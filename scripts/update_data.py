#!/usr/bin/env python3
"""岡山市公式の「認可保育園等の受入見込み」PDFを取得し facilities.json を更新する。

v3: PDFの罫線テーブルを pdfplumber.extract_tables() で直接読む方式。
施設名行と電話・住所行が分かれる園、1セルにまとまる園の両方に対応。
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "facilities.json"
SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
UA = "OkayamaKosodateNavi/1.3 (official-data refresh)"
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
    r".*?〒?\s*([0-9]{3})[-－ー]([0-9]{4})\s*(.+)$"
)


def normalize(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def get_latest_pdf():
    r = requests.get(SOURCE_PAGE, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    raw_text = soup.get_text("\n", strip=True)
    page_text = normalize(soup.get_text(" ", strip=True))

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


def ward_for_page(page_index: int, page_count: int) -> str:
    # 現行PDFは7ページ構成。各ページの区を固定対応させる方が、
    # ヘッダ等に含まれる文字を誤認するより安定する。
    if page_count == 7:
        return WARD_BY_7P[page_index]
    ratio = page_index / max(page_count - 1, 1)
    if ratio < .43:
        return "北区"
    if ratio < .58:
        return "中区"
    if ratio < .73:
        return "東区"
    return "南区"


def split_lines(cell: str | None) -> list[str]:
    if not cell:
        return []
    return [normalize(x) for x in str(cell).splitlines() if normalize(x)]


def status_value(cell: str | None):
    t = normalize(cell)
    if t in STATUS_MAP:
        return STATUS_MAP[t]
    # セル内に注記が付いた場合でも先頭の記号を拾う
    m = re.search(r"[○〇△×]", t)
    return STATUS_MAP[m.group(0)] if m else None


def parse_phone_address(text: str):
    text = normalize(text)
    m = PHONE_POST_RE.search(text)
    if not m:
        return None
    area, p2, p3, z1, z2, addr = m.groups()
    phone = f"{area or '086'}-{p2}-{p3}"
    addr = normalize(addr)
    # 右側セル由来の残骸が混じった場合を軽く除去
    addr = re.split(r"\s+(?:[0-9０-９]{1,3}\s+(?:[0-9０-９]+(?:か月|歳)|満)|[○〇△×](?:\s+[○〇△×]){2,})", addr)[0].strip()
    return phone, f"{z1}-{z2}", addr


def parse_facility_identity(info: str, typ_cell: str, pub_cell: str, operator_cell: str):
    """施設名・種別・公私・設置者を返す。"""
    info = normalize(info)
    # 電話番号以降は身元情報ではない
    head = re.split(r"(?:℡|☎|TEL|Tel|tel)\s*", info, maxsplit=1)[0].strip()

    typ = normalize(typ_cell)
    pub = normalize(pub_cell)
    operator = normalize(operator_cell)

    if typ in TYPE_MAP and pub in ("公", "私"):
        name = head
        # PDF抽出で同じセルに typ/pub/operator まで重複して入った場合は除去
        name = re.sub(r"\s+(?:保|こ|小|事)\s*(?:公|私).*$", "", name).strip()
        return name, typ, pub, operator

    # 私立園などで「園名 保 私福)○○会」のように1セルへ連結されるケース
    m = re.match(r"^(.*?)\s+(保|こ|小|事)\s*(公|私)\s*(.*)$", head)
    if m:
        name, typ, pub, op = m.groups()
        return normalize(name), typ, pub, normalize(op)

    return None


def is_probable_facility_row(row: list[str | None]) -> bool:
    if len(row) < 9:
        return False
    statuses = [status_value(c) for c in row[8:14]] if len(row) >= 14 else []
    if sum(s is not None for s in statuses) >= 2:
        return True
    typ = normalize(row[3]) if len(row) > 3 else ""
    pub = normalize(row[4]) if len(row) > 4 else ""
    return typ in TYPE_MAP and pub in ("公", "私")


def parse_table_rows(rows, ward: str, old_by_name: dict, page_no: int):
    facilities = []
    skipped = []

    for i, row in enumerate(rows):
        row = list(row or [])
        if len(row) < 15:
            row += [None] * (15 - len(row))
        if not is_probable_facility_row(row):
            continue

        info = normalize(row[2])
        identity = parse_facility_identity(info, row[3], row[4], row[5])
        if not identity:
            if len(skipped) < 8:
                skipped.append(f"p{page_no} identity: {info[:100]}")
            continue

        name, typ, pub, operator = identity
        if not name or "施設名" in name or len(name) < 2:
            continue

        # 電話・住所は同じセル内、または直後1〜2行の施設情報セルにある。
        phone_source = info
        phone_data = parse_phone_address(phone_source)
        if not phone_data:
            for j in range(i + 1, min(i + 3, len(rows))):
                nxt = list(rows[j] or [])
                if len(nxt) < 3:
                    continue
                # 次の施設本体行に入ったら打ち切る
                if is_probable_facility_row(nxt):
                    break
                candidate = normalize(nxt[2])
                phone_data = parse_phone_address(candidate)
                if phone_data:
                    break

        if not phone_data:
            # 逆に直前行へ電話が分離する特殊ケースも見る
            if i > 0 and len(rows[i - 1] or []) >= 3:
                phone_data = parse_phone_address(normalize(rows[i - 1][2]))

        if not phone_data:
            if len(skipped) < 8:
                skipped.append(f"p{page_no} phone: {name} / {info[:90]}")
            continue

        phone, postal, addr = phone_data
        availability = {}
        for age, cell in enumerate(row[8:14]):
            st = status_value(cell)
            if st:
                availability[str(age)] = st

        prev = old_by_name.get(name, {})
        facilities.append({
            "name": name,
            "ward": ward,
            "type": TYPE_MAP.get(typ, "保育施設"),
            "public": pub == "公",
            "operator": operator or ("岡山市" if pub == "公" else ""),
            "phone": phone,
            "postal": postal,
            "address": f"{ward}{addr}",
            "services": prev.get("services", {"extended": False, "temporary": False}),
            "availability": availability or prev.get("availability", {}),
            "lat": prev.get("lat"),
            "lon": prev.get("lon"),
        })

    return facilities, skipped


def parse_pdf(content: bytes, old_by_name: dict):
    all_facilities = []
    all_skipped = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pi, page in enumerate(pdf.pages):
            ward = ward_for_page(pi, len(pdf.pages))

            # 罫線ベースを第一候補。うまく取れないPDF用に text 戦略もフォールバック。
            tables = page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 4,
                "join_tolerance": 4,
                "intersection_tolerance": 5,
                "text_tolerance": 3,
            }) or []

            if not tables:
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                    "text_tolerance": 3,
                }) or []

            page_facilities = []
            for table in tables:
                fs, skipped = parse_table_rows(table, ward, old_by_name, pi + 1)
                page_facilities.extend(fs)
                all_skipped.extend(skipped)

            # 同じ施設が同一ページで複数テーブルに重複した場合を整理
            uniq = {}
            for f in page_facilities:
                uniq[(f["name"], f["phone"])] = f
            page_facilities = list(uniq.values())
            all_facilities.extend(page_facilities)
            print(f"[update_data] page {pi+1}/{len(pdf.pages)}: tables={len(tables)}, parsed={len(page_facilities)}, ward={ward}")

    if all_skipped:
        for msg in all_skipped[:20]:
            print(f"[update_data] debug: {msg}")

    uniq = {}
    for f in all_facilities:
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

    if old.get("source_pdf_sha256") == digest and len(old.get("facilities", [])) >= 100:
        print("Official PDF unchanged; no data update needed.")
        return

    facilities = parse_pdf(r.content, old_by)
    print(f"PDF: {title} / parsed={len(facilities)}")

    if len(facilities) < 100:
        raise RuntimeError(
            f"解析件数が少なすぎます ({len(facilities)}件)。既存JSONを保持します。"
            " Actionログの page ... tables=... parsed=... を確認してください。"
        )

    with_availability = sum(
        1 for f in facilities
        if sum(v in ("○", "△", "×") for v in f.get("availability", {}).values()) >= 2
    )
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
            key=lambda x: (["北区", "中区", "東区", "南区"].index(x["ward"]), x["name"]),
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
