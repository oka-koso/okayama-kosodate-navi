#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "public_links_audit.json"

PUBLIC_NURSERY_URL = "https://www.city.okayama.jp/kurashi/0000030497.html"
PUBLIC_KODOMO_URL = "https://www.city.okayama.jp/kurashi/0000030473.html"

UA = "OkayamaKosodateNavi/public-links-v1"
JST = timezone(timedelta(hours=9))
WARDS = ("北区", "中区", "東区", "南区")

PHONE_RE = re.compile(r"(086)[-－ー](\d{3})[-－ー](\d{4})")

def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()

def norm_name(v):
    return (
        clean(v)
        .replace("　", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("・", "")
        .replace(" ", "")
    )

def norm_phone(v):
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 10 and d.startswith("086"):
        return d
    if len(d) == 7:
        return "086" + d
    return d

def norm_address(v):
    s = clean(v)
    s = s.replace("岡山市", "", 1)
    s = s.replace("一丁目", "1丁目")
    s = s.replace("二丁目", "2丁目")
    s = s.replace("三丁目", "3丁目")
    s = s.replace("四丁目", "4丁目")
    s = s.replace("五丁目", "5丁目")
    s = s.replace("六丁目", "6丁目")
    s = s.replace("七丁目", "7丁目")
    s = s.replace("八丁目", "8丁目")
    s = s.replace("九丁目", "9丁目")
    s = s.replace("－", "-").replace("ー", "-")
    return re.sub(r"\s+", "", s)

def scrape_public_page(url, category):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    current_ward = ""

    for node in soup.find_all(["h2", "h3", "h4", "table"]):
        if node.name != "table":
            text = clean(node.get_text(" ", strip=True))
            for ward in WARDS:
                if ward in text:
                    current_ward = ward
            continue

        for tr in node.find_all("tr"):
            cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
            if len(cells) < 4:
                continue

            name = cells[0]
            if not name or name in ("園名", "施設名"):
                continue

            phone = ""
            address = ""

            for cell in cells[1:]:
                m = PHONE_RE.search(cell)
                if m and not phone:
                    phone = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                if any(ward in cell for ward in WARDS) and not address:
                    address = cell
                    if not address.startswith("岡山市"):
                        address = "岡山市" + address

            if not phone or not address:
                continue

            full_name = name
            if category == "認可保育園" and not full_name.endswith("保育園"):
                full_name += "保育園"
            elif category == "認定こども園" and not full_name.endswith("こども園"):
                full_name += "認定こども園"

            out.append({
                "name_on_city_page": name,
                "full_name_guess": full_name,
                "category": category,
                "ward": current_ward,
                "phone": phone,
                "address": address,
                "source_url": url,
            })

    return out

def build_indexes(facilities):
    by_phone = {}
    by_address = {}
    by_name = {}

    for f in facilities:
        p = norm_phone(f.get("phone"))
        a = norm_address(f.get("address"))
        n = norm_name(f.get("name"))

        if p:
            by_phone.setdefault(p, []).append(f)
        if a:
            by_address.setdefault(a, []).append(f)
        if n:
            by_name.setdefault(n, []).append(f)

    return by_phone, by_address, by_name

def match_row(row, indexes):
    by_phone, by_address, by_name = indexes

    p = norm_phone(row["phone"])
    a = norm_address(row["address"])

    # 1. 電話番号一意
    phone_candidates = by_phone.get(p, [])
    if len(phone_candidates) == 1:
        return phone_candidates[0], "phone"

    # 2. 住所一意
    addr_candidates = by_address.get(a, [])
    if len(addr_candidates) == 1:
        return addr_candidates[0], "address"

    # 3. 名称候補
    variants = {
        norm_name(row["full_name_guess"]),
        norm_name(row["name_on_city_page"]),
    }

    if row["category"] == "認可保育園":
        variants.add(norm_name(row["name_on_city_page"] + "保育園"))
    else:
        variants.add(norm_name(row["name_on_city_page"] + "認定こども園"))
        variants.add(norm_name(row["name_on_city_page"] + "こども園"))

    name_candidates = []
    for v in variants:
        name_candidates.extend(by_name.get(v, []))

    unique = {f["id"]: f for f in name_candidates}
    if len(unique) == 1:
        return next(iter(unique.values())), "name"

    return None, "none"

def main():
    if not MASTER.exists():
        raise RuntimeError("data/facility_master.json がありません。")

    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])

    if len(facilities) != 206:
        raise RuntimeError(f"固定マスタが206施設ではありません: {len(facilities)}")

    official_rows = (
        scrape_public_page(PUBLIC_NURSERY_URL, "認可保育園")
        + scrape_public_page(PUBLIC_KODOMO_URL, "認定こども園")
    )

    indexes = build_indexes(facilities)

    matches = []
    unmatched = []
    matched_ids = set()

    for row in official_rows:
        facility, method = match_row(row, indexes)
        if not facility:
            unmatched.append(row)
            continue

        if facility["id"] in matched_ids:
            unmatched.append({
                **row,
                "reason": "duplicate-master-match",
                "matched_id": facility["id"],
            })
            continue

        matches.append({
            "id": facility["id"],
            "master_name": facility["name"],
            "city_name": row["name_on_city_page"],
            "category": row["category"],
            "method": method,
            "source_url": row["source_url"],
        })
        matched_ids.add(facility["id"])

    audit = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "official_public_rows": len(official_rows),
        "matched_public_facilities": len(matches),
        "unmatched_count": len(unmatched),
        "matches": matches,
        "unmatched": unmatched,
    }

    AUDIT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"[public-links-v1] official={len(official_rows)} "
        f"matched={len(matches)} unmatched={len(unmatched)}"
    )

    # 岡山市の現行ページは公立保育園25園 + 公立認定こども園25園。
    # 50園すべてを固定マスタへ一意照合できた場合だけ反映する。
    if len(official_rows) != 50 or len(matches) != 50 or unmatched:
        raise RuntimeError(
            "公立50園の完全照合に失敗しました。"
            "facility_master.json は更新せず audit を確認してください。"
        )

    match_by_id = {m["id"]: m for m in matches}

    for f in facilities:
        if f["id"] in match_by_id:
            m = match_by_id[f["id"]]

            f["public_private"] = "公立"
            f["website"] = ""
            f["website_status"] = "none"
            f["official_info_url"] = m["source_url"]
            f["public_source"] = m["source_url"]

        else:
            # 公立50園が完全照合できた後なので、残りは私立として確定可能。
            f["public_private"] = "私立"
            if f.get("website"):
                f["website_status"] = "verified"
            else:
                # 私立の公式HP調査は次工程。未確認を「なし」にしない。
                if f.get("website_status") not in ("none", "verified"):
                    f["website_status"] = "unchecked"
            f.setdefault("official_info_url", "")

    data["public_private_generated_at"] = audit["generated_at"]
    data["public_facility_count"] = 50

    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("[public-links-v1] facility_master.json updated safely.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[public-links-v1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
