#!/usr/bin/env python3
from __future__ import annotations

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
NAME_MASTER = ROOT / "data" / "facility_name_master.json"
OUT = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "facility_master_audit.json"

# 岡山市 令和8年度保育利用ガイド
# 「11 認可保育施設一覧（令和7年8月現在）」
SOURCE_PDF = (
    "https://www.city.okayama.jp/kurashi/cmsfiles/"
    "contents/0000012/13000/R8_32-ura_hoiku.pdf"
)

PUBLIC_NURSERY_URL = "https://www.city.okayama.jp/kurashi/0000030497.html"
PUBLIC_KODOMO_URL = "https://www.city.okayama.jp/kurashi/0000030473.html"

UA = "OkayamaKosodateNavi/fixed-master-enricher-2.0"
JST = timezone(timedelta(hours=9))

PHONE_LABEL_3PART_RE = re.compile(
    r"(?:℡|☎|TEL|Tel|tel)\s*"
    r"([0-9]{2,4})[-－ー]([0-9]{2,4})[-－ー]([0-9]{4})"
)
PHONE_LABEL_2PART_RE = re.compile(
    r"(?:℡|☎|TEL|Tel|tel)\s*"
    r"([0-9]{3,4})[-－ー]([0-9]{4})"
)
POSTAL_RE = re.compile(r"〒\s*([0-9]{3})[-－ー]([0-9]{4})")

def extract_phone(text):
    """Tel/℡/☎ の直後だけを電話番号として採用する。"""
    text = text or ""

    m3 = PHONE_LABEL_3PART_RE.search(text)
    if m3:
        return f"{m3.group(1)}-{m3.group(2)}-{m3.group(3)}"

    m2 = PHONE_LABEL_2PART_RE.search(text)
    if m2:
        return f"086-{m2.group(1)}-{m2.group(2)}"

    return ""

WARDS = ("北区", "中区", "東区", "南区")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm_name(value):
    return (
        clean(value)
        .replace("　", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("・", "")
        .replace(" ", "")
    )


def full_address(locality, ward):
    """
    郵便番号は絶対に address に混ぜない。
    locality は PDF の「町名以下」だけを受け取る。
    """
    locality = clean(locality)
    locality = re.sub(r"^〒?\s*\d{3}[-－ー]\d{4}\s*", "", locality)

    if not locality:
        return ""

    if locality.startswith("岡山市"):
        return locality

    if locality.startswith(WARDS):
        return "岡山市" + locality

    return f"岡山市{ward}{locality}"


def pdf_lines_by_page(content):
    result = {}
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        # 施設一覧は先頭9ページ
        for page_no, page in enumerate(pdf.pages[:9], start=1):
            text = page.extract_text(x_tolerance=1.5, y_tolerance=2.0) or ""
            result[page_no] = [
                clean(line)
                for line in text.splitlines()
                if clean(line)
            ]
    return result


def parse_contact_line(line):
    """
    電話番号は必ず Tel/℡/☎ の直後から取得し、
    郵便番号は必ず 〒 の直後から取得する。
    """
    phone = extract_phone(line)
    if not phone:
        return None

    postal = ""
    locality = ""

    postal_match = POSTAL_RE.search(line)
    if postal_match:
        postal = f"{postal_match.group(1)}-{postal_match.group(2)}"
        locality = line[postal_match.end():].strip()

        locality = re.sub(r"^[※＊*]\s*", "", locality)
        locality = re.sub(r"^〒\s*\d{3}[-－ー]\d{4}\s*", "", locality)

        locality = re.split(
            r"\s+(?:短|標準)\s+\d{1,2}:\d{2}",
            locality,
            maxsplit=1,
        )[0].strip()

        locality = re.split(
            r"\s+(?:\d{1,3}\s*(?:人|か月|ヶ月|歳)|[○〇△×])",
            locality,
            maxsplit=1,
        )[0].strip()

    return {
        "phone": phone,
        "postal": postal,
        "locality": locality,
        "raw": line,
    }


def contacts_for_page(lines):
    # 園ごとに必ず電話行があるので、名前抽出に頼らず電話行を順番に使う。
    contacts = []
    for line in lines:
        if not any(label in line for label in ("℡", "☎", "TEL", "Tel", "tel")):
            continue
        parsed = parse_contact_line(line)
        if parsed:
            contacts.append(parsed)
    return contacts


def scrape_public_html(url, category):
    """
    公立園は最新HTML一覧で所在地・電話を補正する。
    """
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    current_ward = ""
    out = {}

    # テーブル前見出しの区名を保持
    for node in soup.find_all(["h2", "h3", "h4", "table"]):
        if node.name != "table":
            text = clean(node.get_text(" ", strip=True))
            for ward in WARDS:
                if ward in text:
                    current_ward = ward
            continue

        for tr in node.find_all("tr"):
            cells = [
                clean(x.get_text(" ", strip=True))
                for x in tr.find_all(["th", "td"])
            ]
            if len(cells) < 3:
                continue

            # 多くの表は [園名, 所在地/住所, 電話] or [園名, ..., 電話, 所在地]
            name = cells[0]
            if not name or name in ("園名", "施設名"):
                continue

            candidates = []
            for idx, cell in enumerate(cells[1:], start=1):
                if extract_phone(cell):
                    candidates.append(("phone", idx, cell))
                if re.search(r"(?:北区|中区|東区|南区)", cell):
                    candidates.append(("address", idx, cell))

            phone = ""
            address = ""

            for kind, _, cell in candidates:
                if kind == "phone" and not phone:
                    phone = extract_phone(cell)
                elif kind == "address" and not address:
                    address = cell
                    if not address.startswith("岡山市"):
                        address = "岡山市" + address

            # 岡山市の公立一覧では園名に施設種別が省略される場合がある
            possible_names = {norm_name(name)}
            if category == "認可保育園":
                possible_names.add(norm_name(name + "保育園"))
            elif category == "認定こども園":
                possible_names.add(norm_name(name + "認定こども園"))

            for key in possible_names:
                out[key] = {
                    "phone": phone,
                    "address": address,
                    "ward": current_ward,
                }

    return out


def main():
    fixed = json.loads(NAME_MASTER.read_text(encoding="utf-8"))
    facilities = fixed["facilities"]

    # 固定マスタ自体の基本監査
    names = [norm_name(x["name"]) for x in facilities]
    if len(names) != len(set(names)):
        raise RuntimeError("固定施設名マスタに重複があります。")
    if len(facilities) < 180:
        raise RuntimeError(
            f"固定施設名マスタが少なすぎます: {len(facilities)}件"
        )

    r = requests.get(SOURCE_PDF, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()

    pages = pdf_lines_by_page(r.content)

    # 固定施設をPDFページごとに並べる。
    # name master の並び順は公式PDFの紙面順に固定済み。
    by_page = {}
    for f in facilities:
        page = int(f["source_pdf_page"])
        by_page.setdefault(page, []).append(f)

    contact_by_page = {
        page: contacts_for_page(lines)
        for page, lines in pages.items()
    }

    page_audit = []
    assigned = []

    for page in sorted(by_page):
        expected = by_page[page]
        contacts = contact_by_page.get(page, [])

        page_audit.append({
            "page": page,
            "expected_facilities": len(expected),
            "contact_rows": len(contacts),
            "status": "ok" if len(expected) == len(contacts) else "mismatch",
        })

        # ここが重要:
        # 件数が合わないページは「それっぽく」ずらして割り当てない。
        # データ事故を避けるため、この段階で失敗させる。
        if len(expected) != len(contacts):
            continue

        for facility, contact in zip(expected, contacts):
            item = dict(facility)

            item["phone"] = contact["phone"]
            item["postal"] = contact["postal"]
            item["address"] = full_address(
                contact["locality"],
                item["ward"],
            )
            item["contact_source"] = "R8 official facility-list PDF"

            assigned.append(item)

    mismatches = [x for x in page_audit if x["status"] != "ok"]

    # 一旦、ページ件数不一致がある場合でも audit を書き出す。
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    audit_payload = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source_pdf": SOURCE_PDF,
        "fixed_master_count": len(facilities),
        "assigned_count_before_public_correction": len(assigned),
        "page_audit": page_audit,
        "mismatch_pages": mismatches,
    }

    if mismatches:
        AUDIT.write_text(
            json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        detail = ", ".join(
            f"P{x['page']} expected={x['expected_facilities']} contacts={x['contact_rows']}"
            for x in mismatches
        )
        raise RuntimeError(
            "PDF紙面順との件数照合に失敗しました。"
            f" 推測割当をせず停止します: {detail}"
        )

    # 公立園については最新HTMLで補正。
    public_nursery = scrape_public_html(
        PUBLIC_NURSERY_URL,
        "認可保育園",
    )
    public_kodomo = scrape_public_html(
        PUBLIC_KODOMO_URL,
        "認定こども園",
    )
    public = {**public_nursery, **public_kodomo}

    corrected = 0
    issues = []

    for item in assigned:
        key = norm_name(item["name"])

        if item.get("public_private") == "公立" or key in public:
            info = public.get(key)
            if info:
                if info.get("phone"):
                    item["phone"] = info["phone"]
                if info.get("address"):
                    item["address"] = info["address"]
                if info.get("ward"):
                    item["ward"] = info["ward"]
                item["contact_source"] = "Okayama City public-facility HTML"
                corrected += 1

        # 厳格な形式監査
        if "〒" in item.get("address", ""):
            issues.append({
                "name": item["name"],
                "issue": "postal_leaked_into_address",
                "value": item["address"],
            })

        postal = item.get("postal", "")
        if postal and not re.fullmatch(r"\d{3}-\d{4}", postal):
            issues.append({
                "name": item["name"],
                "issue": "invalid_postal",
                "value": postal,
            })

        phone = item.get("phone", "")
        if phone and not re.fullmatch(r"\d{2,4}-\d{2,4}-\d{4}", phone):
            issues.append({
                "name": item["name"],
                "issue": "invalid_phone_format",
                "value": phone,
            })

        if "※" in item.get("address", "") or "〒" in item.get("address", ""):
            issues.append({
                "name": item["name"],
                "issue": "annotation_or_postal_leaked_into_address",
                "value": item.get("address", ""),
            })

        address = item.get("address", "")
        if address and not address.startswith("岡山市"):
            issues.append({
                "name": item["name"],
                "issue": "address_not_prefixed_okayama_city",
                "value": address,
            })

        if not item.get("phone"):
            issues.append({
                "name": item["name"],
                "issue": "missing_phone",
            })

        if not item.get("address"):
            issues.append({
                "name": item["name"],
                "issue": "missing_address",
            })

    payload = {
        "schema_version": 2,
        "source_name_master": "facility_name_master.json",
        "source_contact_pdf": SOURCE_PDF,
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "facility_count": len(assigned),
        "public_html_corrected": corrected,
        "facilities": assigned,
    }

    audit_payload["assigned_count"] = len(assigned)
    audit_payload["public_html_corrected"] = corrected
    audit_payload["issue_count"] = len(issues)
    audit_payload["issues"] = issues

    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    AUDIT.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if issues:
        print(
            f"[master] generated {len(assigned)} facilities "
            f"with {len(issues)} audit issue(s)."
        )
        for issue in issues[:20]:
            print("[master] warning:", issue)
        raise RuntimeError(
            f"施設マスタ監査で{len(issues)}件の問題を検出しました。"
            " facility_master.json は生成しましたが、監査合格前のため本番利用しないでください。"
        )

    print(
        f"[master] SUCCESS facilities={len(assigned)} "
        f"public_html_corrected={corrected} issues=0"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[master] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
