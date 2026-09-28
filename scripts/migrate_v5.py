#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "data" / "facilities.json"
MASTER = ROOT / "data" / "facility_master.json"
AVAIL = ROOT / "data" / "availability.json"


def norm_name(s: str) -> str:
    s = (s or "").strip().replace("　", "")
    s = s.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", s)


def facility_id(name: str, postal: str = "") -> str:
    key = f"{norm_name(name)}|{postal or ''}".encode("utf-8")
    return "oky-" + hashlib.sha1(key).hexdigest()[:12]


def full_address(address: str, ward: str = "") -> str:
    a = (address or "").strip()
    if not a:
        return ""
    if a.startswith("岡山市"):
        return a
    if re.match(r"^(北区|中区|東区|南区)", a):
        return "岡山市" + a
    if ward:
        return f"岡山市{ward}{a}"
    return "岡山市" + a


def main():
    # すでにv5マスタがある場合は何もしない。
    if MASTER.exists():
        print("[migrate_v5] facility_master.json already exists")
        return

    if not OLD.exists():
        raise SystemExit("data/facilities.json が見つかりません。")

    old = json.loads(OLD.read_text(encoding="utf-8"))
    facilities = []
    availability = {}

    for src in old.get("facilities", []):
        name = (src.get("name") or "").strip()
        if not name:
            continue

        fid = src.get("id") or facility_id(name, src.get("postal", ""))
        master = {
            "id": fid,
            "name": name,
            "aliases": [],
            "ward": src.get("ward", ""),
            "type": src.get("type", ""),
            "public": bool(src.get("public", False)),
            "operator": src.get("operator", ""),
            "postal": src.get("postal", ""),
            "address": full_address(src.get("address", ""), src.get("ward", "")),
            "phone": src.get("phone", ""),
            "lat": src.get("lat"),
            "lon": src.get("lon"),
            "website": src.get("website", ""),
            "official_info_url": src.get("official_info_url", ""),
            "services": src.get("services", {"extended": False, "temporary": False}),
            "active": True,
            "review_status": "migrated",
        }
        facilities.append(master)

        if src.get("availability"):
            availability[fid] = src["availability"]

    MASTER.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "source": "migrated from data/facilities.json",
                "facilities": facilities,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    AVAIL.write_text(
        json.dumps(
            {
                "schema_version": 5,
                "availability_for": old.get("availability_for"),
                "availability_as_of": old.get("availability_as_of"),
                "source_page_updated": old.get("source_page_updated"),
                "source_pdf_url": old.get("source_pdf_url"),
                "by_facility_id": availability,
                "unmatched_pdf_facilities": [],
                "master_not_in_pdf": [],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"[migrate_v5] master={len(facilities)}, availability={len(availability)}")


if __name__ == "__main__":
    main()
