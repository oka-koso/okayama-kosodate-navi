#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_final.json"
SUMMARY = ROOT / "data" / "private_website_audit_summary.json"

RECORDS = [
  {
    "id": "oky-a180daa6c959",
    "name": "共生保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.hellowork.mhlw.go.jp/",
    "note": "現行の所在地・電話は公的情報で確認。公式園/法人サイトは2026-09-29時点で特定できず。"
  },
  {
    "id": "oky-862ccd1c91a1",
    "name": "富田保育園",
    "result": "verified",
    "website": "http://tomitahoikuen.jp/",
    "evidence": "http://tomitahoikuen.jp/",
    "note": "施設公開情報にも当園ホームページとして同URLが記載。"
  },
  {
    "id": "oky-c0388f0bb7a0",
    "name": "深柢保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.city.okayama.jp/kosodate/0000045410.html",
    "note": "岡山市の岡山中央子育て支援センター掲載で施設同一性を確認。法人の公的開示でもホームページ欄なし。"
  },
  {
    "id": "oky-6af4f50817f8",
    "name": "牧石保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.pref.okayama.jp/",
    "note": "岡山県の現行施設情報で施設同一性を確認。公式園/法人サイトは2026-09-29時点で特定できず。"
  },
  {
    "id": "oky-26ce7b7ab03c",
    "name": "朝日保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.city.okayama.jp/",
    "note": "岡山市・施設公開情報で所在地/電話/運営法人を確認。公式園/法人サイトは2026-09-29時点で特定できず。"
  },
  {
    "id": "oky-73a2b33b3b99",
    "name": "しろばら保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.city.okayama.jp/kyoudou/0000068470.html",
    "note": "岡山市の施設個別ページで所在地・電話を確認。公式園/法人サイトは2026-09-29時点で特定できず。"
  },
  {
    "id": "oky-283b642b9f61",
    "name": "ひばり保育園",
    "result": "checked_no_official_url_found",
    "evidence": "https://www.wam.go.jp/",
    "note": "社会福祉法人淳厚会の公的開示で施設を確認し、法人ホームページ欄は空欄。公式園サイトも特定できず。"
  },
  {
    "id": "oky-bd718a3906e7",
    "name": "みどり町保育園",
    "result": "verified",
    "website": "http://midorikai-net.or.jp/nursery/",
    "evidence": "http://midorikai-net.or.jp/nursery/",
    "note": "施設公開情報にWebサイトとして同URLが記載。"
  }
]
TERMINAL = {"verified", "checked_no_official_url_found"}

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    fs = data.get("facilities", [])
    by_id = {f.get("id"): f for f in fs}
    changed, errors = [], []

    # This is intentionally one all-or-nothing final batch.
    for r in RECORDS:
        f = by_id.get(r["id"])
        if not f:
            errors.append({**r, "reason":"id-not-found"})
            continue
        if f.get("name") != r["name"]:
            errors.append({**r, "reason":"name-mismatch", "actual_name":f.get("name")})
            continue
        if f.get("public_private") != "私立":
            errors.append({**r, "reason":"not-private", "actual":f.get("public_private")})
            continue

        before = {
            "website": f.get("website"),
            "website_status": f.get("website_status"),
            "website_verified_at": f.get("website_verified_at"),
            "website_verification_source": f.get("website_verification_source")
        }

        if r["result"] == "verified":
            f["website"] = r["website"]
        else:
            # Do not invent a URL and do not claim that a website can never exist.
            f["website"] = ""

        f["website_status"] = r["result"]
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = r["evidence"]
        f["website_verification_note"] = r["note"]

        changed.append({
            "id":f["id"], "name":f["name"], "result":r["result"],
            "website":f.get("website",""), "before":before,
            "evidence":r["evidence"], "note":r["note"]
        })

    audit = {
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "batch":"final-8",
        "target_count":len(RECORDS),
        "processed_count":len(changed),
        "error_count":len(errors),
        "records":changed,
        "errors":errors
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    if errors or len(changed) != len(RECORDS):
        raise RuntimeError(
            f"Final batch stopped safely: {len(changed)}/{len(RECORDS)}; "
            f"errors={len(errors)}. facility_master.json was not written."
        )

    private = [f for f in fs if f.get("public_private") == "私立"]
    unchecked = [f for f in private if f.get("website_status") not in TERMINAL]
    verified = [f for f in private if f.get("website_status") == "verified"]
    no_url = [f for f in private if f.get("website_status") == "checked_no_official_url_found"]

    summary = {
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "private_total":len(private),
        "website_verified":len(verified),
        "checked_no_official_url_found":len(no_url),
        "audit_complete":len(private) - len(unchecked),
        "unchecked_count":len(unchecked),
        "unchecked":[
            {"id":f.get("id"),"name":f.get("name"),"ward":f.get("ward"),
              "website_status":f.get("website_status")}
            for f in unchecked
        ]
    }

    if unchecked:
        raise RuntimeError(
            f"Final audit did not reach zero unchecked facilities: {len(unchecked)} remain. "
            "Master not written."
        )

    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[private-websites-final] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
