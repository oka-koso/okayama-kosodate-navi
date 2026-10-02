#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AVAIL = ROOT / "data" / "availability.json"

SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
UA = "OkayamaKosodateNavi/5.2"
JST = timezone(timedelta(hours=9))

TYPE_MAP = {
    "保": "保育園",
    "こ": "認定こども園",
    "小": "地域型保育",
    "事": "地域型保育",
}
STATUS_MAP = {"〇": "○", "○": "○", "△": "△", "×": "×"}
WARD_BY_7P = ["北区", "北区", "北区", "中区", "東区", "南区", "南区"]

PHONE_RE = re.compile(r"(?:(086)[-－ー])?([0-9]{3,4})[-－ー]([0-9]{4})")
POSTAL_RE = re.compile(r"〒?\s*([0-9]{3})[-－ー]([0-9]{4})")
CAPACITY_RE = re.compile(r"^\d{1,3}$")


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def norm_name(s):
    s = clean(s).replace("　", "")
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"\s+", "", s)
    return s.replace("・", "")


def full_address(address, ward=""):
    a = clean(address)
    if not a:
        return ""
    if a.startswith("岡山市"):
        return a
    if re.match(r"^(北区|中区|東区|南区)", a):
        return "岡山市" + a
    return f"岡山市{ward}{a}" if ward else "岡山市" + a


def stable_id(name, postal=""):
    raw = f"{norm_name(name)}|{postal}".encode("utf-8")
    return "oky-" + hashlib.sha1(raw).hexdigest()[:12]


def latest_pdf():
    r = requests.get(SOURCE_PAGE, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    page_updated = None
    m = re.search(r"\[(\d{4})年(\d{1,2})月(\d{1,2})日\]", soup.get_text("\n", strip=True))
    if m:
        page_updated = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    candidates = []
    for a in soup.find_all("a", href=True):
        text = clean(" ".join(a.stripped_strings))
        href = requests.compat.urljoin(SOURCE_PAGE, a["href"])
        path = href.split("?", 1)[0].lower()

        if not path.endswith(".pdf"):
            continue
        if "認可外" in text or "教育利用" in text:
            continue

        filename = path.rsplit("/", 1)[-1]
        score = 0
        if "受入見込み" in text:
            score += 4
        if "認可保育園" in text:
            score += 4
        if "ninka" in filename and "ninkagai" not in filename:
            score += 4

        if score >= 4:
            candidates.append((score, text or filename, href))

    if not candidates:
        # 岡山市の受入見込みPDFは申込締切日前の約1週間だけ公開され、
        # 締切後は一時的に非掲載になるため、Noneを返して正常スキップする。
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, title, url = candidates[0]
    return title, url, page_updated, page_text


def ward_for_page(index, page_count):
    if page_count == 7:
        return WARD_BY_7P[index]
    ratio = index / max(page_count - 1, 1)
    if ratio < .43:
        return "北区"
    if ratio < .58:
        return "中区"
    if ratio < .73:
        return "東区"
    return "南区"


def group_words_by_row(words, tolerance=2.6):
    """
    pdfplumber.extract_words() の top 座標で実際の紙面の「横一列」を再構成する。
    extract_tables() のように結合セルで園名を落とさないためのv5.2の核。
    """
    words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))
    rows = []

    for w in words:
        top = float(w["top"])
        if not rows or abs(top - rows[-1]["top"]) > tolerance:
            rows.append({"top": top, "words": [w]})
        else:
            rows[-1]["words"].append(w)
            # 少し平均して、微小なズレに強くする
            n = len(rows[-1]["words"])
            rows[-1]["top"] = ((rows[-1]["top"] * (n - 1)) + top) / n

    for r in rows:
        r["words"] = sorted(r["words"], key=lambda w: float(w["x0"]))

    return rows


def row_text(row):
    return clean(" ".join(str(w["text"]) for w in row["words"]))


def find_header_geometry(rows):
    """
    ページの見出しから「施設名列」と「0～5歳列」の概略x位置を取得。
    ページごとの微妙なレイアウト差に追随する。
    """
    facility_left = None
    age_centers = {}

    for row in rows:
        for w in row["words"]:
            t = clean(str(w["text"]))
            if "施設名" in t and facility_left is None:
                facility_left = float(w["x0"])

            m = re.fullmatch(r"([０１２３４５0-5])歳", t)
            if m:
                z = m.group(1)
                trans = str.maketrans("０１２３４５", "012345")
                age = int(z.translate(trans))
                age_centers[age] = (float(w["x0"]) + float(w["x1"])) / 2

    return facility_left, age_centers


def is_type_token(t):
    return clean(t) in TYPE_MAP


def is_public_token(t):
    return clean(t) in ("公", "私")


def plausible_name(s):
    s = clean(s)
    if not s:
        return False

    reject = (
        "施設名", "電話番号", "利用定員", "対象年齢", "受入見込み",
        "注意事項", "備考", "中学校区", "年齢別", "凡例",
        "確認時点", "施設利用", "保育利用", "教育利用", "設置者",
        "令和", "ページ", "クラス", "生年月日",
    )
    if any(x in s for x in reject):
        return False

    if s in TYPE_MAP or s in ("公", "私"):
        return False
    if PHONE_RE.search(s) or POSTAL_RE.search(s):
        return False
    if re.fullmatch(r"\d+", s):
        return False

    return bool(re.search(r"[ぁ-んァ-ヶ一-龯]", s))


def join_name_words(words):
    # 日本語名は基本スペースなし。英数字部分の自然さより園名一致を優先。
    text = "".join(clean(str(w["text"])) for w in words)
    return clean(text)


def detect_facility_row(row, facility_left):
    """
    同じy座標上の「施設名 / 種別 / 公私」を座標で結び直す。
    これにより、従来ログで "保 私" だけになっていた施設も取得可能。
    """
    ws = row["words"]

    type_positions = [i for i, w in enumerate(ws) if is_type_token(str(w["text"]))]
    if not type_positions:
        return None

    # 施設表中では原則、最初に出る保/こ/小/事を採用
    ti = type_positions[0]

    pi = None
    for j in range(ti + 1, min(ti + 4, len(ws))):
        if is_public_token(str(ws[j]["text"])):
            pi = j
            break

    if pi is None:
        return None

    type_token = clean(str(ws[ti]["text"]))
    pub_token = clean(str(ws[pi]["text"]))
    type_x = float(ws[ti]["x0"])

    name_words = []
    for w in ws[:ti]:
        x0 = float(w["x0"])
        x1 = float(w["x1"])
        t = clean(str(w["text"]))

        # 施設名ヘッダ位置が取れた場合、それより左（学校区など）を除く
        if facility_left is not None and x1 < facility_left - 2:
            continue

        # 種別列より左だけ
        if x0 >= type_x:
            continue

        # 区・学校区や数値だけのセルを除く
        if not t or re.fullmatch(r"\d+", t):
            continue

        name_words.append(w)

    name = join_name_words(name_words)

    # 名前が取れない場合、種別の直前1～2語を救済
    if not plausible_name(name):
        rescue = []
        for w in reversed(ws[:ti]):
            t = clean(str(w["text"]))
            if plausible_name(t):
                rescue.insert(0, w)
                # かなり長い園名は複数wordに割れるため2～3語まで連結
                if len(rescue) >= 3:
                    break
            elif rescue:
                break
        name = join_name_words(rescue)

    if not plausible_name(name):
        return None

    # 設置者は公私セルの右から、定員（数値セル）の手前まで
    operator_words = []
    for w in ws[pi + 1:]:
        t = clean(str(w["text"]))
        if CAPACITY_RE.fullmatch(t):
            break
        if t in STATUS_MAP:
            break
        operator_words.append(w)

    operator = clean(" ".join(str(w["text"]) for w in operator_words))

    return {
        "name": name,
        "type_code": type_token,
        "public_code": pub_token,
        "operator": operator,
        "row_top": row["top"],
        "words": ws,
    }


def parse_contact_row(row, ward):
    txt = row_text(row)
    if not PHONE_RE.search(txt) and not POSTAL_RE.search(txt):
        return "", "", ""

    phone = ""
    postal = ""
    address = ""

    pm = PHONE_RE.search(txt)
    if pm:
        area, p2, p3 = pm.groups()
        phone = f"{area or '086'}-{p2}-{p3}"

    zm = POSTAL_RE.search(txt)
    if zm:
        postal = f"{zm.group(1)}-{zm.group(2)}"
        tail = txt[zm.end():].strip()

        # 後方に別セルの情報が混ざったときの切断
        tail = re.split(
            r"\s+(?:\d{1,3}\s*(?:人|か月|ヶ月|歳)|[○〇△×](?:\s+[○〇△×])|障害児)",
            tail,
            maxsplit=1,
        )[0].strip()

        address = full_address(tail, ward)

    return phone, postal, address


def nearest_contact(rows, index, ward):
    """
    施設名行の直後数行から電話・〒住所を探す。
    """
    base_top = rows[index]["top"]

    for j in range(index + 1, min(len(rows), index + 5)):
        # 離れすぎたら別行ブロック
        if rows[j]["top"] - base_top > 26:
            break

        phone, postal, address = parse_contact_row(rows[j], ward)
        if phone or postal or address:
            return phone, postal, address

    return "", "", ""


def status_from_token(t):
    t = clean(t)
    if t in STATUS_MAP:
        return STATUS_MAP[t]
    return None


def availability_from_same_row(row, age_centers):
    """
    0～5歳のヘッダx位置へ○△×を最近傍割当。
    merged cell / text extraction orderに依存しない。
    """
    if len(age_centers) < 4:
        return {}

    result = {}

    for w in row["words"]:
        st = status_from_token(str(w["text"]))
        if not st:
            continue

        cx = (float(w["x0"]) + float(w["x1"])) / 2
        age = min(age_centers, key=lambda a: abs(age_centers[a] - cx))

        # 近すぎない記号は備考欄などの可能性があるため弾く
        if abs(age_centers[age] - cx) <= 28:
            result[str(age)] = st

    return result


def availability_near_row(rows, index, age_centers):
    """
    園名行と○△×のbaselineが数pxズレるPDFに対応。
    同一行＋上下近傍から最も多く取れたものを採用。
    """
    best = {}
    base_top = rows[index]["top"]

    for j in range(max(0, index - 2), min(len(rows), index + 3)):
        if abs(rows[j]["top"] - base_top) > 12:
            continue

        av = availability_from_same_row(rows[j], age_centers)
        if len(av) > len(best):
            best = av

    return best


def parse_pdf(pdf_bytes):
    facilities = []
    seen = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            ward = ward_for_page(pi, len(pdf.pages))

            words = page.extract_words(
                use_text_flow=False,
                keep_blank_chars=False,
                x_tolerance=1.5,
                y_tolerance=2.0,
            ) or []

            rows = group_words_by_row(words)
            facility_left, age_centers = find_header_geometry(rows)

            page_count = 0
            missing_contact = 0
            missing_status = 0

            for i, row in enumerate(rows):
                rec = detect_facility_row(row, facility_left)
                if not rec:
                    continue

                key = norm_name(rec["name"])
                if not key or key in seen:
                    continue

                phone, postal, address = nearest_contact(rows, i, ward)
                availability = availability_near_row(rows, i, age_centers)

                if not phone or not address:
                    missing_contact += 1
                if not availability:
                    missing_status += 1

                facilities.append({
                    "name": rec["name"],
                    "normalized_name": key,
                    "ward": ward,
                    "type": TYPE_MAP.get(rec["type_code"], "保育施設"),
                    "public": rec["public_code"] == "公",
                    "operator": rec["operator"],
                    "phone": phone,
                    "postal": postal,
                    "address": address,
                    "availability": availability,
                })
                seen.add(key)
                page_count += 1

            print(
                f"[update] page {pi+1}/{len(pdf.pages)} "
                f"parsed={page_count} "
                f"missing_contact={missing_contact} "
                f"missing_status={missing_status} "
                f"ward={ward}"
            )

    return facilities


def load_master():
    return json.loads(MASTER.read_text(encoding="utf-8"))


def master_indexes(master):
    exact = {}
    for f in master["facilities"]:
        exact[norm_name(f.get("name", ""))] = f
        for alias in f.get("aliases", []):
            exact[norm_name(alias)] = f
    return exact


def fuzzy_match(name, facilities):
    target = norm_name(name)
    best = None
    best_score = 0.0

    for f in facilities:
        names = [f.get("name", "")] + list(f.get("aliases", []))
        for candidate in names:
            score = SequenceMatcher(None, target, norm_name(candidate)).ratio()
            if score > best_score:
                best = f
                best_score = score

    return (best, best_score) if best_score >= 0.94 else (None, best_score)


def meta_from_pdf(pdf_bytes, title, page_text):
    result = {"availability_for": None, "availability_as_of": None}

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(
                (pdf.pages[i].extract_text() or "")
                for i in range(min(2, len(pdf.pages)))
            )

        m = re.search(r"確認時点\s*([^\n]*?時点)", text)
        if m:
            result["availability_as_of"] = clean(m.group(1))

        m = re.search(r"施設利用\s*開始月\s*([^\n]+)", text)
        if m:
            result["availability_for"] = clean(m.group(1))
    except Exception:
        pass

    if not result["availability_for"]:
        m = re.search(r"令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月", title)
        if m:
            result["availability_for"] = f"令和{m.group(1)}年{m.group(2)}月"

    if not result["availability_as_of"]:
        m = re.search(
            r"令和\s*[0-9０-９]+年\s*[0-9０-９]+月\s*[0-9０-９]+日\s*時点",
            page_text
        )
        if m:
            result["availability_as_of"] = clean(m.group(0))

    return result


def main():
    if not MASTER.exists():
        raise RuntimeError(
            "facility_master.json がありません。v5の初期マスタ作成を先に実行してください。"
        )

    discovered = latest_pdf()
    if discovered is None:
        print(
            "[update] SKIP: monthly availability PDF is not currently "
            "published; existing data preserved."
        )
        return

    title, pdf_url, page_updated, page_text = discovered

    r = requests.get(pdf_url, headers={"User-Agent": UA}, timeout=45)
    r.raise_for_status()

    pdf_hash = hashlib.sha256(r.content).hexdigest()
    pdf_facilities = parse_pdf(r.content)

    # 閾値を下げて「成功」にしない。現行PDF全件取得前提。
    if len(pdf_facilities) < 180:
        raise RuntimeError(
            f"PDFから取得できた施設が{len(pdf_facilities)}件しかありません。"
            "座標ベース解析でも不足しているため、既存データを保護して停止します。"
        )

    master = load_master()
    exact = master_indexes(master)

    matched_ids = set()
    by_id = {}
    fuzzy_log = []
    auto_added = []

    for pf in pdf_facilities:
        f = exact.get(pf["normalized_name"])

        if not f:
            f, score = fuzzy_match(pf["name"], master["facilities"])
            if f:
                fuzzy_log.append({
                    "pdf_name": pf["name"],
                    "master_name": f["name"],
                    "score": round(score, 4),
                })

        if not f:
            fid = stable_id(pf["name"], pf.get("postal", ""))
            f = {
                "id": fid,
                "name": pf["name"],
                "aliases": [],
                "ward": pf["ward"],
                "type": pf["type"],
                "public": pf["public"],
                "operator": pf.get("operator", ""),
                "postal": pf.get("postal", ""),
                "address": pf.get("address", ""),
                "phone": pf.get("phone", ""),
                "lat": None,
                "lon": None,
                "website": "",
                "official_info_url": "",
                "services": {
                    "extended": False,
                    "temporary": False
                },
                "active": True,
                "review_status": "auto_added_from_availability_pdf_v5_2",
            }
            master["facilities"].append(f)
            exact[norm_name(f["name"])] = f
            auto_added.append(f["name"])

        # PDFの連絡先は「現在PDFに載っている住所・電話」として、
        # 値が正常に取れている場合だけマスタへ反映。
        if pf.get("phone"):
            f["phone"] = pf["phone"]
        if pf.get("postal"):
            f["postal"] = pf["postal"]
        if pf.get("address"):
            f["address"] = full_address(pf["address"], pf["ward"])

        if not f.get("ward"):
            f["ward"] = pf["ward"]
        if not f.get("type"):
            f["type"] = pf["type"]

        matched_ids.add(f["id"])
        by_id[f["id"]] = pf.get("availability", {})

    with_status = sum(1 for v in by_id.values() if v)

    # 受入記号の取得率も監査。
    if with_status < 150:
        raise RuntimeError(
            f"受入見込みを読み取れた施設が{with_status}件しかありません。"
            "既存データを保護して停止します。"
        )

    missing_from_pdf = [
        {"id": f["id"], "name": f["name"]}
        for f in master["facilities"]
        if f.get("active", True) and f["id"] not in matched_ids
    ]

    meta = meta_from_pdf(r.content, title, page_text)

    master["updated_at"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    master["last_pdf_seen"] = pdf_url
    master["last_auto_added"] = auto_added

    MASTER.write_text(
        json.dumps(master, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    AVAIL.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "parser_version": "5.2-coordinate",
                "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
                "availability_for": meta["availability_for"],
                "availability_as_of": meta["availability_as_of"],
                "source_page_updated": page_updated,
                "source_pdf_title": title,
                "source_pdf_url": pdf_url,
                "source_pdf_sha256": pdf_hash,
                "pdf_facility_count": len(pdf_facilities),
                "matched_facility_count": len(matched_ids),
                "with_status_count": with_status,
                "auto_added_facilities": auto_added,
                "fuzzy_matches": fuzzy_log,
                "master_not_in_pdf": missing_from_pdf,
                "by_facility_id": by_id,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"[update] SUCCESS pdf={len(pdf_facilities)} "
        f"matched={len(matched_ids)} "
        f"with_status={with_status} "
        f"auto_added={len(auto_added)} "
        f"master_not_in_pdf={len(missing_from_pdf)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[update] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
