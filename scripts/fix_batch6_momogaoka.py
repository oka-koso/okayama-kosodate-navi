#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch6_fix1.json"

ALIASES = {"桃丘こども園", "（仮称）桃丘こども園", "(仮称)桃丘こども園"}
OFFICIAL = {
    "name": "桃丘こども園",
    "phone": "086-236-8780",
    "postal": "701-1221",
    "address": "岡山市北区芳賀5112-2",
    "website": "https://cumre.or.jp/service/childcare/momogaoka/",
    "source": "https://cumre.or.jp/service/childcare/momogaoka/",
}

def norm_name(v):
    return re.sub(r"[\s　・]", "", str(v or "")).replace("（","(").replace("）",")")

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])
    aliases = {norm_name(x) for x in ALIASES}

    name_candidates = [f for f in facilities if norm_name(f.get("name")) in aliases]
    candidates = [
        f for f in name_candidates
        if f.get("ward") == "北区"
        and (
            "701-1221" in str(f.get("postal") or "")
            or "芳賀5112" in str(f.get("address") or "")
        )
    ]

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": "桃丘こども園",
        "official": OFFICIAL,
        "name_candidates": [
            {k: f.get(k) for k in ("id","name","phone","postal","address","public_private")}
            for f in name_candidates
        ],
        "location_match_count": len(candidates),
    }

    if len(candidates) != 1:
        audit["result"] = "blocked"
        audit["reason"] = f"location-match-count={len(candidates)}"
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        raise RuntimeError("桃丘こども園を園名＋所在地で一意照合できませんでした。")

    f = candidates[0]
    if f.get("public_private") != "私立":
        audit["result"] = "blocked"
        audit["reason"] = f"public_private={f.get('public_private')}"
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        raise RuntimeError("桃丘こども園が私立として登録されていません。")

    audit["before"] = {k: f.get(k) for k in ("name","phone","postal","address","website")}

    f["name"] = OFFICIAL["name"]
    f["phone"] = OFFICIAL["phone"]
    f["postal"] = OFFICIAL["postal"]
    f["address"] = OFFICIAL["address"]
    f["website"] = OFFICIAL["website"]
    f["website_status"] = "verified"
    f["website_verified_at"] = "2026-09-29"
    f["website_verification_source"] = OFFICIAL["source"]

    audit["result"] = "updated"
    audit["facility_id"] = f.get("id")
    audit["after"] = {k: f.get(k) for k in ("name","phone","postal","address","website")}

    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("[batch6-fix1] 桃丘こども園を現行公式情報へ更新しました。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch6-fix1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
