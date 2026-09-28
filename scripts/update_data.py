#!/usr/bin/env python3
"""
岡山市公式「認可保育園等の受入見込み」PDFを取得し、掲載施設を漏れなく facilities.json に反映する。

v4:
- 「電話・住所がうまく抽出できない行」を理由に施設自体を捨てない。
- PDF内で施設と判断できる行の件数を監査し、解析漏れがあれば更新を止める。
- 既存の緯度経度、サービス情報、公式サイトURLを保持する。
- data/websites.json に園名→URLを追加すれば公式サイトURLを施設データへ自動反映する。
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
WEBSITES = ROOT / "data" / "websites.json"

SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
FACILITY_LIST_PAGE = "https://www.city.okayama.jp/kurashi/0000012549.html"
UA = "OkayamaKosodateNavi/1.4 (official-data refresh)"
JST = timezone(timedelta(hours=9))

TYPE_MAP = {
    "保": "保育園",
    "こ": "認定こども園",
    "小": "地域型保育",
    "事": "地域型保育",
}

STATUS_MAP = {"〇": "○", "○": "○", "△": "△", "×": "×"}
WARD_BY_7P = ["北区", "北区", "北区", "中区", "東区", "南区", "南区"]

PHONE_RE = re.compile(
    r"(?:℡|☎|TEL|Tel|tel)?\s*"
    r"(?:(086)[-－ー])?([0-9]{3,4})[-－ー]([0-9]{4})"
)
POSTAL_RE = re.compile(r"〒?\s*([0-9]{3})[-－ー]([0-9]{4})")


def normalize(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def normalize_name(s: str | None) -> str:
    s = normalize(s)
    s = s.replace("　", "")
    s = re.sub(r"\s+", "", s)
    s = s.replace("（", "(").replace("）", ")")
    return s


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


def status_value(cell: str | None):
    t = normalize(cell)
    if t in STATUS_MAP:
        return STATUS_MAP[t]
    m = re.search(r"[○〇△×]", t)
    return STATUS_MAP[m.group(0)] if m else None


def row_text(row) -> str:
    return normalize(" ".join(normalize(c) for c in (row or []) if normalize(c)))


def get_type_pub_operator(row):
    row = list(row or [])
    if len(row) < 6:
        row += [None] * (6 - len(row))

    typ = normalize(row[3])
    pub = normalize(row[4])
    operator = normalize(row[5])

    if typ in TYPE_MAP and pub in ("公", "私"):
        return typ, pub, operator

    text = row_text(row)

    # 園名 保 私 福)○○会 のようにセル結合された場合。
    m = re.search(r"(?:^|\s)(保|こ|小|事)\s*(公|私)(?:\s+([^\n]+))?", text)
    if m:
        return m.group(1), m.group(2), normalize(m.group(3) or "")

    return None


def is_probable_facility_row(row) -> bool:
    row = list(row or [])
    if not row:
        return False

    tpo = get_type_pub_operator(row)
    if tpo:
        return True

    statuses = [status_value(c) for c in row[8:14]] if len(row) >= 14 else []
    return sum(s is not None for s in statuses) >= 2


def extract_name(row):
    row = list(row or [])
    info = normalize(row[2]) if len(row) > 2 else ""
    text = info or row_text(row)

    # 電話・郵便番号より前だけを園名候補にする。
    text = re.split(r"(?:℡|☎|TEL|Tel|tel)\s*", text, maxsplit=1)[0]
    text = re.split(r"〒?\s*[0-9]{3}[-－ー][0-9]{4}", text, maxsplit=1)[0]

    # 「園名 保 私 法人名」の後半を切る。
    text = re.sub(r"\s+(?:保|こ|小|事)\s*(?:公|私).*$", "", text).strip()

    # ヘッダ等を除外。
    if not text or "施設名" in text or text in {"保", "こ", "小", "事", "公", "私"}:
        return None

    return normalize(text)


def parse_contact(block: str, ward: str):
    """近傍行を連結した文字列から電話、郵便番号、住所をできる範囲で拾う。"""
    block = normalize(block)

    phone = ""
    m = PHONE_RE.search(block)
    if m:
        area, p2, p3 = m.groups()
        phone = f"{area or '086'}-{p2}-{p3}"

    postal = ""
    address = ""
    pm = POSTAL_RE.search(block)
    if pm:
        postal = f"{pm.group(1)}-{pm.group(2)}"
        tail = block[pm.end():].strip()

        # 年齢欄・記号欄などが後ろに混ざった場合を切る。
        tail = re.split(
            r"\s+(?:0歳|1歳|2歳|3歳|4歳|5歳|[○〇△×](?:\s+[○〇△×]){1,})",
            tail
        )[0].strip()

        # 区名がPDF本文に含まれていなければ付与する。
        if tail:
            if re.match(r"^(北区|中区|東区|南区)", tail):
                address = tail
            else:
                address = f"{ward}{tail}"

    return phone, postal, address


def load_websites():
    if not WEBSITES.exists():
        return {}

    raw = json.loads(WEBSITES.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "facilities" in raw:
        raw = raw["facilities"]

    result = {}
    if isinstance(raw, dict):
        for name, url in raw.items():
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                result[normalize_name(name)] = url.strip()

    return result


def parse_table_rows(rows, ward: str, old_by_name: dict, websites: dict, page_no: int):
    facilities = []
    raw_candidates = 0
    problems = []

    for i, row in enumerate(rows):
        row = list(row or [])
        if len(row) < 15:
            row += [None] * (15 - len(row))

        if not is_probable_facility_row(row):
            continue

        name = extract_name(row)
        tpo = get_type_pub_operator(row)

        if not name or not tpo:
            continue

        raw_candidates += 1
        typ, pub, operator = tpo

        # 同じ園の電話・住所が次行に分離されていることがあるため近傍行をまとめて読む。
        blocks = [row_text(row)]
        for j in range(max(0, i - 1), min(len(rows), i + 4)):
            if j == i:
                continue
            nxt = list(rows[j] or [])

            # 次の施設行なら、それ以降は混ぜない。
            if j > i and is_probable_facility_row(nxt) and extract_name(nxt):
                break

            blocks.append(row_text(nxt))

        phone, postal, address = parse_contact(" ".join(blocks), ward)

        availability = {}
        for age, cell in enumerate(row[8:14]):
            st = status_value(cell)
            if st:
                availability[str(age)] = st

        key = normalize_name(name)
        prev = old_by_name.get(key, {})

        website = websites.get(key) or prev.get("website") or ""

        facility = {
            "name": name,
            "ward": ward,
            "type": TYPE_MAP.get(typ, "保育施設"),
            "public": pub == "公",
            "operator": operator or prev.get("operator") or ("岡山市" if pub == "公" else ""),
            "phone": phone or prev.get("phone", ""),
            "postal": postal or prev.get("postal", ""),
            "address": address or prev.get("address", ""),
            "services": prev.get("services", {"extended": False, "temporary": False}),
            "availability": availability,
            "website": website,
            "lat": prev.get("lat"),
            "lon": prev.get("lon"),
        }

        if not facility["phone"] or not facility["address"]:
            problems.append(
                f"p{page_no}: contact incomplete: {name} / phone={facility['phone']!r} / address={facility['address']!r}"
            )

        facilities.append(facility)

    return facilities, raw_candidates, problems


def extract_tables(page):
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

    return tables


def parse_pdf(content: bytes, old_by_name: dict, websites: dict):
    all_facilities = []
    total_candidates = 0
    all_problems = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pi, page in enumerate(pdf.pages):
            ward = ward_for_page(pi, len(pdf.pages))
            tables = extract_tables(page)

            page_facilities = []
            page_candidates = 0

            for table in tables:
                fs, candidates, problems = parse_table_rows(
                    table, ward, old_by_name, websites, pi + 1
                )
                page_facilities.extend(fs)
                page_candidates += candidates
                all_problems.extend(problems)

            # 同一園の重複抽出を整理。
            uniq = {}
            for f in page_facilities:
                uniq[(normalize_name(f["name"]), f["ward"])] = f
            page_facilities = list(uniq.values())

            total_candidates += page_candidates
            all_facilities.extend(page_facilities)

            print(
                f"[update_data] page {pi+1}/{len(pdf.pages)}: "
                f"tables={len(tables)}, candidates={page_candidates}, "
                f"parsed={len(page_facilities)}, ward={ward}"
            )

    # 全ページの重複も整理。
    uniq = {}
    for f in all_facilities:
        uniq[(normalize_name(f["name"]), f["ward"])] = f
    facilities = list(uniq.values())

    # 施設候補を拾ったのに最終データに大幅な欠落がある場合は安全のため書き換えない。
    # 重複テーブル抽出があり得るので「candidate == parsed」は要求しないが、
    # parsed が candidate の85%未満なら要確認とする。
    if total_candidates and len(facilities) < int(total_candidates * 0.85):
        raise RuntimeError(
            f"施設候補行 {total_candidates}件に対して最終施設 {len(facilities)}件です。"
            " 解析漏れの可能性があるため既存JSONを保持します。"
        )

    for msg in all_problems[:30]:
        print(f"[update_data] warning: {msg}")

    return facilities, total_candidates


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
    old_by = {
        normalize_name(x.get("name")): x
        for x in old.get("facilities", [])
        if x.get("name")
    }
    websites = load_websites()

    title, url, source_page_updated, page_as_of = get_latest_pdf()

    r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    r.raise_for_status()
    digest = hashlib.sha256(r.content).hexdigest()

    # PDFが同一でも websites.json を更新した場合にURLを反映できるよう、
    # v4では早期returnしない。
    facilities, candidate_count = parse_pdf(r.content, old_by, websites)

    print(f"PDF: {title} / candidates={candidate_count} / parsed={len(facilities)}")

    if len(facilities) < 100:
        raise RuntimeError(
            f"解析件数が少なすぎます ({len(facilities)}件)。既存JSONを保持します。"
        )

    with_availability = sum(
        1 for f in facilities
        if any(v in ("○", "△", "×") for v in f.get("availability", {}).values())
    )

    print(
        f"[update_data] facilities with availability: "
        f"{with_availability}/{len(facilities)}"
    )

    if with_availability < max(80, int(len(facilities) * 0.70)):
        raise RuntimeError(
            f"受入見込みの解析件数が少なすぎます "
            f"({with_availability}/{len(facilities)}件)。既存JSONを保持します。"
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
        "facility_candidate_rows": candidate_count,
        "facility_count": len(facilities),
        "sources": [
            SOURCE_PAGE,
            FACILITY_LIST_PAGE,
        ],
        "facilities": sorted(
            facilities,
            key=lambda x: (
                ["北区", "中区", "東区", "南区"].index(x["ward"]),
                x["name"],
            ),
        ),
    }

    DATA.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[update_data] wrote {DATA} ({len(facilities)} facilities)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[update_data] {e}", file=sys.stderr)
        sys.exit(1)
