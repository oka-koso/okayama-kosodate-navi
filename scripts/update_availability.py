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
UA = "OkayamaKosodateNavi/5.1"
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


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def norm_name(s):
    s = clean(s).replace("　", "")
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"\s+", "", s)
    return s.replace("・", "")


def stable_id(name, postal=""):
    raw = f"{norm_name(name)}|{postal}".encode("utf-8")
    return "oky-" + hashlib.sha1(raw).hexdigest()[:12]


def full_address(address, ward=""):
    a = clean(address)
    if not a:
        return ""
    if a.startswith("岡山市"):
        return a
    if re.match(r"^(北区|中区|東区|南区)", a):
        return "岡山市" + a
    return f"岡山市{ward}{a}" if ward else "岡山市" + a


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
        raise RuntimeError("最新の認可保育施設受入見込みPDFを発見できません。")

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


def status(cell):
    t = clean(cell)
    if t in STATUS_MAP:
        return STATUS_MAP[t]

    m = re.fullmatch(r".*?([○〇△×]).*?", t)
    return STATUS_MAP[m.group(1)] if m else None


def row_text(row):
    return clean(" ".join(clean(c) for c in (row or []) if clean(c)))


def type_public(row):
    cells = [clean(c) for c in (row or [])]

    # 独立セル
    for i, c in enumerate(cells):
        if c in TYPE_MAP:
            for j in range(i + 1, min(i + 4, len(cells))):
                if cells[j] in ("公", "私"):
                    return i, c, cells[j]

    # セル結合
    text = row_text(row)
    m = re.search(r"(?:^|\s)(保|こ|小|事)\s*(公|私)(?:\s|$)", text)
    if m:
        return None, m.group(1), m.group(2)

    return None


def plausible_name(s):
    s = clean(s)
    if not s:
        return False

    reject = (
        "施設名", "電話番号", "利用定員", "対象年齢", "受入見込み",
        "注意事項", "備考", "中学校区", "年齢別", "凡例",
        "認可保育園等の受入見込み", "確認時点", "施設利用",
        "保育利用", "教育利用", "設置者", "確認日時",
    )
    if any(x in s for x in reject):
        return False

    if s in TYPE_MAP or s in ("公", "私"):
        return False

    if PHONE_RE.search(s) or POSTAL_RE.search(s):
        return False

    # 園名には通常かな・漢字が含まれる。
    return bool(re.search(r"[ぁ-んァ-ヶ一-龯]", s))


def name_score(s):
    """園名らしさ。前行探索で法人名より園名を優先する。"""
    s = clean(s)
    if not plausible_name(s):
        return -999

    score = 1

    strong = (
        "保育園", "こども園", "保育所", "幼稚園",
        "保育室", "キッズ", "ナーサリー", "スクール",
        "ルーム", "園", "保育",
    )
    if any(x in s for x in strong):
        score += 8

    # 法人名・設置者名らしさは減点
    operator_words = (
        "社会福祉法人", "学校法人", "株式会社", "有限会社",
        "合同会社", "一般社団法人", "医療法人", "岡山市",
    )
    if any(x in s for x in operator_words):
        score -= 6

    if len(s) > 40:
        score -= 3

    return score


def clean_name_candidate(name):
    name = clean(name)
    name = re.split(r"(?:℡|☎|TEL|Tel|tel)\s*", name, maxsplit=1)[0]
    name = re.split(r"〒?\s*[0-9]{3}[-－ー][0-9]{4}", name, maxsplit=1)[0]
    name = re.sub(r"\s+(?:保|こ|小|事)\s*(?:公|私).*$", "", name).strip()
    return clean(name)


def extract_name(row, type_index=None):
    cells = [clean(c) for c in (row or [])]
    candidates = []

    if type_index is not None:
        for c in reversed(cells[:type_index]):
            if plausible_name(c):
                candidates.append(c)
                break

    if len(cells) > 2 and plausible_name(cells[2]):
        candidates.append(cells[2])

    for c in cells:
        m = re.match(r"(.+?)\s+(保|こ|小|事)\s*(公|私)(?:\s|$)", c)
        if m and plausible_name(m.group(1)):
            candidates.append(m.group(1))

    if not candidates:
        return None

    candidates = [clean_name_candidate(c) for c in candidates]
    candidates = [c for c in candidates if plausible_name(c)]
    if not candidates:
        return None

    return max(candidates, key=name_score)


def previous_name(rows, idx):
    """
    園名と種別が別行になったPDFを救済。
    type/public行の直前1～4行から最も園名らしいセルを選ぶ。
    """
    candidates = []

    for back in range(1, 5):
        j = idx - back
        if j < 0:
            break

        r = rows[j]

        # 前の施設のtype/public行まで遡らない
        if type_public(r):
            break

        for c in (r or []):
            c = clean_name_candidate(c)
            sc = name_score(c)
            if sc > 0:
                # 近い行を少し優先
                candidates.append((sc + (5 - back) * 0.35, c))

        txt = clean_name_candidate(row_text(r))
        sc = name_score(txt)
        if sc > 0:
            candidates.append((sc + (5 - back) * 0.35, txt))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]


def contact_from_text(text, ward):
    phone = postal = address = ""

    pm = PHONE_RE.search(text)
    if pm:
        area, p2, p3 = pm.groups()
        phone = f"{area or '086'}-{p2}-{p3}"

    zm = POSTAL_RE.search(text)
    if zm:
        postal = f"{zm.group(1)}-{zm.group(2)}"
        tail = text[zm.end():].strip()

        # 後方の定員・年齢・受入記号等を切る
        tail = re.split(
            r"\s+(?:"
            r"\d{1,3}\s*(?:人|か月|ヶ月|歳)|"
            r"[○〇△×](?:\s+[○〇△×])|"
            r"障害児|幼稚園型|"
            r"(?:保|こ|小|事)\s*(?:公|私)"
            r")",
            tail,
            maxsplit=1,
        )[0].strip()

        address = full_address(tail, ward)

    return phone, postal, address


def statuses_from_row(row):
    cells = [clean(c) for c in (row or [])]

    if len(cells) >= 14:
        vals = [status(c) for c in cells[8:14]]
        if sum(v is not None for v in vals) >= 1:
            return {str(i): v for i, v in enumerate(vals) if v is not None}

    vals = []
    for c in cells:
        v = status(c)
        if v is not None and clean(c) in STATUS_MAP:
            vals.append(v)

    vals = vals[-6:]
    return {str(i): v for i, v in enumerate(vals)}


def best_statuses_near(rows, idx):
    """
    年齢別記号がtype/public行とは別行へ分かれた場合にも対応。
    現行行と前後2行のうち、最も多く○△×を取れる行を採用する。
    """
    best = {}

    for j in range(max(0, idx - 2), min(len(rows), idx + 3)):
        vals = statuses_from_row(rows[j])
        if len(vals) > len(best):
            best = vals

    return best


def contact_block(rows, idx):
    """
    同一施設の名前行・type/public行・電話/住所行をまとめる。
    次の施設のtype/public行へ到達したら停止。
    """
    parts = []

    for j in range(max(0, idx - 2), min(len(rows), idx + 6)):
        if j > idx and type_public(rows[j]):
            break
        parts.append(row_text(rows[j]))

    return clean(" ".join(x for x in parts if x))


def dedupe_rows(rows):
    """
    pdfplumberが同じ表を重複抽出することがあるため、
    連続・非連続を問わず同じ行テキストをページ内で1回にする。
    空行は除外。
    """
    result = []
    seen = set()

    for row in rows:
        key = row_text(row)
        if not key:
            continue

        # 完全一致の重複だけ除く。異なる園の同型行は保持。
        # 園名がないtype/publicだけの行は重複しやすいので、
        # 位置情報を失うと困るため除外対象にしない。
        if plausible_name(key):
            if key in seen:
                continue
            seen.add(key)

        result.append(row)

    return result


def parse_pdf(pdf_bytes):
    parsed = []
    seen = set()

    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "join_tolerance": 4,
        "intersection_tolerance": 5,
        "text_tolerance": 3,
    }

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            ward = ward_for_page(pi, len(pdf.pages))

            tables = page.extract_tables(settings) or []
            if not tables:
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                    "text_tolerance": 3,
                }) or []

            rows = [row for table in tables for row in (table or [])]
            rows = dedupe_rows(rows)

            page_count = 0
            recovered_name_count = 0

            for idx, row in enumerate(rows):
                tp = type_public(row)
                if not tp:
                    continue

                type_index, typ, pub = tp

                # まず同じ行。無ければ直前行から園名を回収。
                name = extract_name(row, type_index)
                if not name:
                    name = previous_name(rows, idx)
                    if name:
                        recovered_name_count += 1

                if not name:
                    print(
                        f"[update] WARNING page {pi+1}: "
                        f"type/public detected but name missing: {row_text(row)[:120]}"
                    )
                    continue

                name = clean_name_candidate(name)
                key = norm_name(name)

                if not key or key in seen:
                    continue

                block = contact_block(rows, idx)
                phone, postal, address = contact_from_text(block, ward)
                availability = best_statuses_near(rows, idx)

                parsed.append({
                    "name": name,
                    "normalized_name": key,
                    "ward": ward,
                    "type": TYPE_MAP.get(typ, "保育施設"),
                    "public": pub == "公",
                    "phone": phone,
                    "postal": postal,
                    "address": address,
                    "availability": availability,
                })

                seen.add(key)
                page_count += 1

            print(
                f"[update] page {pi+1}/{len(pdf.pages)} "
                f"parsed={page_count} recovered_names={recovered_name_count} ward={ward}"
            )

    return parsed


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
    result = {
        "availability_for": None,
        "availability_as_of": None,
    }

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
            "facility_master.json がありません。migrate_v5.py を先に実行してください。"
        )

    title, pdf_url, page_updated, page_text = latest_pdf()

    r = requests.get(pdf_url, headers={"User-Agent": UA}, timeout=45)
    r.raise_for_status()

    pdf_hash = hashlib.sha256(r.content).hexdigest()
    pdf_facilities = parse_pdf(r.content)

    # v5.1: 閾値を下げてごまかさない。
    # 180件未満なら従来どおり失敗扱いにしてデータを保護する。
    if len(pdf_facilities) < 180:
        raise RuntimeError(
            f"PDFから取得できた施設が{len(pdf_facilities)}件しかありません。"
            "既存データを壊さないため更新を停止します。"
        )

    master = load_master()
    exact = master_indexes(master)

    matched_ids = set()
    by_id = {}
    unmatched = []
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
                "operator": "",
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
                "review_status": "auto_added_from_availability_pdf",
            }

            master["facilities"].append(f)
            exact[norm_name(f["name"])] = f
            auto_added.append(f["name"])

        # 基本情報は空欄のみ補完。
        if not f.get("ward"):
            f["ward"] = pf["ward"]

        if not f.get("type"):
            f["type"] = pf["type"]

        if not f.get("phone") and pf.get("phone"):
            f["phone"] = pf["phone"]

        if not f.get("postal") and pf.get("postal"):
            f["postal"] = pf["postal"]

        if not f.get("address") and pf.get("address"):
            f["address"] = pf["address"]

        # 住所表記を必ず「岡山市○区...」に統一。
        f["address"] = full_address(
            f.get("address", ""),
            f.get("ward", "")
        )

        matched_ids.add(f["id"])
        by_id[f["id"]] = pf.get("availability", {})

    missing_from_pdf = [
        {"id": f["id"], "name": f["name"]}
        for f in master["facilities"]
        if f.get("active", True) and f["id"] not in matched_ids
    ]

    with_status = sum(1 for v in by_id.values() if v)

    # こちらも従来の安全装置を維持。
    if with_status < 150:
        raise RuntimeError(
            f"受入見込みを読み取れた施設が{with_status}件しかありません。"
            "更新を停止します。"
        )

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
                "parser_version": "5.1",
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
                "unmatched_pdf_facilities": unmatched,
                "master_not_in_pdf": missing_from_pdf,
                "by_facility_id": by_id,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"[update] pdf={len(pdf_facilities)} "
        f"matched={len(matched_ids)} "
        f"with_status={with_status} "
        f"auto_added={len(auto_added)} "
        f"master_not_in_pdf={len(missing_from_pdf)}"
    )

    if auto_added:
        print("[update] NEW:", " / ".join(auto_added))

    if missing_from_pdf:
        print(
            "[update] not in latest PDF:",
            " / ".join(x["name"] for x in missing_from_pdf[:30])
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[update] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
