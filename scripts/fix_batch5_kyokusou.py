#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch5_fix1.json"

TARGET_ALIASES = {
    "旭操こども園",
    "旭操認定こども園",
    "（仮称）旭操認定こども園",
    "(仮称)旭操認定こども園",
}
OFFICIAL_PHONE = "086-237-1161"
OFFICIAL_POSTAL = "703-8264"
OFFICIAL_ADDRESS_KEY = "倉富171"
OFFICIAL_WEBSITE = "https://shiragiku.ed.jp/kyokusou/"
EVIDENCE = "https://shiragiku.ed.jp/kyokusou/"

def norm_name(v):
    return re.sub(r"[\s　・]", "", str(v or "")).replace("（","(").replace("）",")")

def norm_phone(v):
    return re.sub(r"\D", "", str(v or ""))

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])
    aliases = {norm_name(x) for x in TARGET_ALIASES}

    # Batch5 failed because the new園 phone is not yet in the old fixed master.
    # For this one migration case, identify by the old/current name AND location,
    # never by phone alone.
    name_candidates = [f for f in facilities if norm_name(f.get("name")) in aliases]
    candidates = [
        f for f in name_candidates
        if f.get("ward") == "中区"
        and (
            OFFICIAL_POSTAL in str(f.get("postal") or "")
            or OFFICIAL_ADDRESS_KEY in str(f.get("address") or "").replace("番地","-").replace("番","-")
            or "倉富" in str(f.get("address") or "")
        )
    ]

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": "旭操こども園",
        "official": {
            "phone": OFFICIAL_PHONE,
            "postal": OFFICIAL_POSTAL,
            "address": "岡山市中区倉富171-2",
            "website": OFFICIAL_WEBSITE,
            "evidence": EVIDENCE,
        },
        "name_candidates": [
            {
                "id": f.get("id"), "name": f.get("name"),
                "phone": f.get("phone"), "postal": f.get("postal"),
                "address": f.get("address"), "public_private": f.get("public_private")
            } for f in name_candidates
        ],
        "location_match_count": len(candidates),
    }

    if len(candidates) != 1:
        audit["result"] = "blocked"
        audit["reason"] = f"location-match-count={len(candidates)}"
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        raise RuntimeError("旭操こども園を園名＋所在地で一意照合できませんでした。")

    f = candidates[0]
    if f.get("public_private") != "私立":
        audit["result"] = "blocked"
        audit["reason"] = f"public_private={f.get('public_private')}"
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        raise RuntimeError("旭操こども園が私立として登録されていません。")

    before = {
        "name": f.get("name"), "phone": f.get("phone"),
        "postal": f.get("postal"), "address": f.get("address"),
        "website": f.get("website")
    }

    # Official current data (2026-09-29)
    f["name"] = "旭操こども園"
    f["phone"] = OFFICIAL_PHONE
    f["postal"] = OFFICIAL_POSTAL
    f["address"] = "岡山市中区倉富171-2"
    f["website"] = OFFICIAL_WEBSITE
    f["website_status"] = "verified"
    f["website_verified_at"] = "2026-09-29"
    f["website_verification_source"] = EVIDENCE

    audit["result"] = "updated"
    audit["facility_id"] = f.get("id")
    audit["before"] = before
    audit["after"] = {
        "name": f.get("name"), "phone": f.get("phone"),
        "postal": f.get("postal"), "address": f.get("address"),
        "website": f.get("website")
    }

    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("[batch5-fix1] 旭操こども園を現行公式情報へ更新しました。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch5-fix1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
