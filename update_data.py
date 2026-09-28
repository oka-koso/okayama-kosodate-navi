#!/usr/bin/env python3
"""岡山市公式の保育・幼児教育施設「受入見込み」を取得して facilities.json を更新する。

v2: PDFの行構造が「園名行」と「電話・住所行」に分かれるケースに対応。
PDF内の表を座標ベースで解析し、園名・種別・設置者・電話・住所・0〜5歳の受入見込みを取得する。
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "facilities.json"
SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
UA = "OkayamaKosodateNavi/1.2 (official-data refresh)"
JST = timezone(timedelta(hours=9))

TYPE_MAP = {
    "保": "保育園",
    "こ": "認定こども園",
    "小": "地域型保育",
    "事": "地域型保育",
}
STATUS_MAP = {"〇": "○", "○": "○", "△": "△", "×": "×"}
WARD_BY_7P = ["北区", "北区", "北区", "中区", "東区", "南区", "南区"]

PHONE_POST_RE = re.compile(
    r"(?:℡|☎|TEL|Tel|tel)?\s*"
    r"(?:(086)[-－ー])?([0-9]{3,4})[-－ー]([0-9]{4})"
    r".*?〒?\s*([0-9]{3})[-－ー]([0-9]{4})\s+(.+)$"
)

# 園名 + 種別 + 公私。設置者は右側セルに分かれる場合があるので任意。
FAC_LINE_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<typ>保|こ|小|事)\s+(?P<pub>公|私)(?:\s+(?P<operator>.+?))?(?:\s+\d+)?(?:\s+[0-9０-９]+(?:か月|歳).*)?$"
)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def clean_name(s: str) -> str:
    s = normalize(s)
    # 左端の区・中学校区文字が混ざった場合の軽い除去
    s = re.sub(r"^(?:北|中|東|南)?\s*区\s+", "", s)
    return s.strip(" ■●◆")


def get_latest_pdf():
    r = requests.get(SOURCE_PAGE, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    page_text = normalize(soup.get_text(" ", strip=True))
    raw_text = soup.get_text("\n", strip=True)

    page_updated = None
    m = re.search(r"\[(\d{4})年(\d{1,2})月(\d{1,2})日\]", raw_text)
    if m:
        page_updated = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    candidates = []
    for a in soup.find_all("a", href=True):
        text = normalize(" ".join(a.stripped_strings))
        href = requests.compat.urljoin(SOURCE_PAGE, a["href"])
        path = href.split("?", 1)[0].lower()
        if not path.endswith(".pdf"):
            continue
        if "認可外" in text or "教育利用" in text:
            continue

        filename = path.rsplit("/", 1)[-1]
        score = 0
        if "受入見込み" in text:
            score += 3
        if "認可保育園" in text:
            score += 4
        elif "認可" in text:
            score += 2
        if "ninka" in filename and "ninkagai" not in filename:
            score += 4
        if score >= 4:
            candidates.append((score, text or filename, href))

    if not candidates:
        raise RuntimeError("認可保育園等の受入見込みPDFを発見できませんでした。")

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, title, url = candidates[0]

    as_of_text = None
    m = re.search(r"こちらの表をご覧ください。?（([^）]*?(?:現在|時点))）", page_text)
    if m:
        as_of_text = m.group(1)

    return title, url, page_updated, as_of_text


def ward_for_page(i: int, n: int, page_text: str = "") -> str:
    # まずページ内の区表記を利用。見つからない場合は従来のページ配分を利用。
    compact = re.sub(r"\s+", "", page_text or "")
    for ward in ("北区", "中区", "東区", "南区"):
        if ward in compact:
            return ward
    if n == 7:
        return WARD_BY_7P[i]
    r = i / max(n - 1, 1)
    return "北区" if r < .43 else "中区" if r < .58 else "東区" if r < .73 else "南区"


def group_words_to_lines(words, tolerance=3.0):
    """pdfplumber words を top 座標で行にまとめる。"""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w.get("top", 0), w.get("x0", 0)))
    lines = []
    current = []
    current_top = None
    for w in words:
        top = float(w.get("top", 0))
        if current_top is None or abs(top - current_top) <= tolerance:
            current.append(w)
            if current_top is None:
                current_top = top
            else:
                current_top = (current_top * (len(current) - 1) + top) / len(current)
        else:
            lines.append(_line_obj(current))
            current = [w]
            current_top = top
    if current:
        lines.append(_line_obj(current))
    return lines


def _line_obj(words):
    words = sorted(words, key=lambda w: w.get("x0", 0))
    return {
        "top": min(float(w.get("top", 0)) for w in words),
        "bottom": max(float(w.get("bottom", w.get("top", 0))) for w in words),
        "x0": min(float(w.get("x0", 0)) for w in words),
        "x1": max(float(w.get("x1", 0)) for w in words),
        "text": normalize(" ".join(w.get("text", "") for w in words)),
        "words": words,
    }


def find_age_columns(page, words):
    """0〜5歳の列中心X。ヘッダ文字が取れない場合は記号列のXクラスタから推定。"""
    cols = {}
    trans = str.maketrans("0123456789", "０１２３４５６７８９")

    for age in range(6):
        labels = (f"{age}歳", f"{str(age).translate(trans)}歳")
        for label in labels:
            try:
                hits = page.search(label) or []
            except Exception:
                hits = []
            hits = [h for h in hits if h.get("x0", 0) > page.width * .45]
            if hits:
                h = sorted(hits, key=lambda x: x.get("top", 9999))[0]
                cols[age] = (h["x0"] + h["x1"]) / 2
                break

    if len(cols) >= 5:
        return cols

    # フォールバック: ○△× のX座標を丸めて頻度の高い6クラスタを使う。
    xs = []
    for w in words:
        if normalize(w.get("text", "")) in STATUS_MAP and w.get("x0", 0) > page.width * .45:
            xs.append((w["x0"] + w["x1"]) / 2)
    if not xs:
        return cols

    buckets = defaultdict(list)
    for x in xs:
        key = round(x / 5) * 5
        buckets[key].append(x)
    common = sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)[:8]
    centers = sorted(sum(v) / len(v) for _, v in common)
    if len(centers) >= 6:
        # 右側に備考の記号が紛れた場合を避け、最も等間隔な6連続を選ぶ。
        best = None
        for i in range(len(centers) - 5):
            c = centers[i:i+6]
            gaps = [c[j+1] - c[j] for j in range(5)]
            score = max(gaps) - min(gaps)
            if best is None or score < best[0]:
                best = (score, c)
        if best:
            for age, x in enumerate(best[1]):
                cols[age] = x
    return cols


def statuses_at_y(words, age_cols, y, y_tol=8.5):
    if len(age_cols) < 4:
        return {}
    symbols = []
    for w in words:
        t = normalize(w.get("text", ""))
        if t in STATUS_MAP and abs(float(w.get("top", 9999)) - y) <= y_tol:
            symbols.append(((w["x0"] + w["x1"]) / 2, STATUS_MAP[t]))
    if not symbols:
        return {}

    xs = sorted(age_cols.values())
    gaps = [b-a for a, b in zip(xs, xs[1:]) if b-a > 0]
    typical_gap = sum(gaps) / len(gaps) if gaps else 40
    out = {}
    for x, st in symbols:
        age, cx = min(age_cols.items(), key=lambda kv: abs(kv[1] - x))
        if abs(cx - x) <= max(typical_gap * .48, 16):
            out[str(age)] = st
    return out


def parse_facility_header(text: str):
    """園名行から (name, typ, pub, operator) を返す。"""
    text = normalize(text)
    # 表の右側（定員・対象年齢・受入記号）をなるべく切る
    text = re.sub(r"\s+[0-9０-９]{1,3}\s+(?:[0-9０-９]+(?:か月|歳)|満).*?$", "", text)
    # 行末の受入記号群を除く
    text = re.sub(r"(?:\s+[○〇△×]){2,6}.*$", "", text)

    m = FAC_LINE_RE.match(text)
    if m:
        return (
            clean_name(m.group("name")),
            m.group("typ"),
            m.group("pub"),
            normalize(m.group("operator") or ""),
        )

    # 列境界の都合で「こ 公 岡山市」等が離れても、最初の 種別+公私 を探す。
    m = re.search(r"\s(保|こ|小|事)\s+(公|私)(?:\s+([^0-9０-９○〇△×]+?))?(?=\s+[0-9０-９]{1,3}\b|\s+[○〇△×]|$)", text)
    if m:
        name = clean_name(text[:m.start()])
        return name, m.group(1), m.group(2), normalize(m.group(3) or "")
    return None


def find_header_for_phone(lines, phone_line_idx):
    """電話・住所行の直前から対応する園名行を探す。"""
    phone_line = lines[phone_line_idx]

    # 同じ行に園名まで入るPDFもある。
    same = parse_facility_header(phone_line["text"])
    if same:
        return same, phone_line["top"]

    # 直前最大4行、かつ縦距離55pt以内。
    for j in range(phone_line_idx - 1, max(-1, phone_line_idx - 5), -1):
        ln = lines[j]
        if phone_line["top"] - ln["top"] > 55:
            break
        parsed = parse_facility_header(ln["text"])
        if parsed:
            return parsed, ln["top"]
    return None, None


def parse_pdf(content: bytes, old_by_name: dict):
    out = []
    debug = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pi, page in enumerate(pdf.pages):
            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=False,
            ) or []
            lines = group_words_to_lines(words, tolerance=3.0)
            page_text = normalize(page.extract_text(x_tolerance=2, y_tolerance=3) or "")
            ward = ward_for_page(pi, len(pdf.pages), page_text)
            age_cols = find_age_columns(page, words)

            page_count = 0
            for i, line in enumerate(lines):
                pm = PHONE_POST_RE.search(line["text"])
                if not pm:
                    continue

                header, header_y = find_header_for_phone(lines, i)
                if not header:
                    # ログには先頭だけ残す。将来レイアウトが変わった時の診断用。
                    if len(debug) < 12:
                        debug.append(f"p{pi+1} header-not-found: {line['text'][:120]}")
                    continue

                name, typ, pub, operator = header
                if not name or len(name) < 2:
                    continue

                area, p2, p3, z1, z2, addr = pm.groups()
                phone = f"{area or '086'}-{p2}-{p3}"
                addr = normalize(addr)
                # 住所行の右側に表データが混ざる場合は切る
                addr = re.split(r"\s{1,}(?:[0-9０-９]{1,3}\s+(?:[0-9０-９]+(?:か月|歳)|満)|[○〇△×](?:\s+[○〇△×]){2,})", addr)[0].strip()

                prev = old_by_name.get(name, {})
                availability = statuses_at_y(words, age_cols, header_y)

                f = {
                    "name": name,
                    "ward": ward,
                    "type": TYPE_MAP.get(typ, "保育施設"),
                    "public": pub == "公",
                    "operator": operator or ("岡山市" if pub == "公" else ""),
                    "phone": phone,
                    "postal": f"{z1}-{z2}",
                    "address": f"{ward}{addr}",
                    "services": prev.get("services", {"extended": False, "temporary": False}),
                    "availability": availability or prev.get("availability", {}),
                    "lat": prev.get("lat"),
                    "lon": prev.get("lon"),
                }
                out.append(f)
                page_count += 1

            print(f"[update_data] page {pi+1}/{len(pdf.pages)}: parsed={page_count}, age_cols={len(age_cols)}, ward={ward}")

    if debug:
        for msg in debug:
            print(f"[update_data] debug: {msg}")

    uniq = {}
    for f in out:
        uniq[(f["name"], f["postal"], f["phone"])] = f
    return list(uniq.values())


def extract_pdf_meta(content: bytes, title: str):
    meta = {"availability_as_of": None, "availability_for": None}
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            first = pdf.pages[0].extract_text() or ""
        m = re.search(r"確認時点\s*([^\n]+?時点)", first)
        if m:
            meta["availability_as_of"] = normalize(m.group(1))
        m = re.search(r"施設利用\s*開始月\s*([^\n]+)", first)
        if m:
            meta["availability_for"] = normalize(m.group(1))
    except Exception:
        pass

    if not meta["availability_for"]:
        m = re.search(r"令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月", title)
        if m:
            meta["availability_for"] = f"令和{m.group(1)}年{m.group(2)}月"
    return meta


def main():
    old = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"facilities": []}
    old_by = {x["name"]: x for x in old.get("facilities", [])}

    title, url, source_page_updated, page_as_of = get_latest_pdf()
    r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    r.raise_for_status()
    digest = hashlib.sha256(r.content).hexdigest()

    # PDFが同一で、既に十分な件数が取れている場合は更新不要。
    if old.get("source_pdf_sha256") == digest and len(old.get("facilities", [])) >= 100:
        print("Official PDF unchanged; no data update needed.")
        return

    facilities = parse_pdf(r.content, old_by)
    print(f"PDF: {title} / parsed={len(facilities)}")

    # 公式資料のレイアウト変更等で誤解析した場合に既存データを壊さない。
    if len(facilities) < 100:
        raise RuntimeError(
            f"解析件数が少なすぎます ({len(facilities)}件)。既存JSONを保持します。"
            " Actionログの page ... parsed= を確認してください。"
        )

    # 年齢別受入状況が取れた園が極端に少ない場合も安全停止。
    with_availability = sum(1 for f in facilities if len(f.get("availability", {})) >= 4)
    print(f"[update_data] facilities with availability: {with_availability}/{len(facilities)}")
    if with_availability < max(50, int(len(facilities) * 0.35)):
        raise RuntimeError(
            f"受入見込みの解析件数が少なすぎます ({with_availability}/{len(facilities)}件)。既存JSONを保持します。"
        )

    meta = extract_pdf_meta(r.content, title)
    payload = {
        "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source_page_updated": source_page_updated,
        "data_scope": "岡山市公表の最新『認可保育園等の受入見込み』掲載施設",
        "availability_as_of": meta["availability_as_of"] or page_as_of,
        "availability_for": meta["availability_for"],
        "source_pdf_title": title,
        "source_pdf_url": url,
        "source_pdf_sha256": digest,
        "sources": [
            SOURCE_PAGE,
            "https://www.city.okayama.jp/kurashi/0000013000.html",
        ],
        "facilities": sorted(
            facilities,
            key=lambda x: (
                ["北区", "中区", "東区", "南区"].index(x["ward"]),
                x["name"],
            ),
        ),
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[update_data] wrote {DATA} ({len(facilities)} facilities)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[update_data] {e}", file=sys.stderr)
        sys.exit(1)
