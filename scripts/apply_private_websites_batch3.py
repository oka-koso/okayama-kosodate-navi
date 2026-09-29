#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch3.json"

BATCH = [
  {
    "names": [
      "ポストメイト保育園・岡山陵南"
    ],
    "phone": "086-250-7245",
    "website": "https://postmate.jp/nursery/305.html",
    "evidence": "https://postmate.jp/nursery/305.html"
  },
  {
    "names": [
      "第四吉備保育園"
    ],
    "phone": "086-293-1717",
    "website": "https://daiyon.kibifukushikai.jp/",
    "evidence": "https://daiyon.kibifukushikai.jp/"
  },
  {
    "names": [
      "ポエム保育園おかやま"
    ],
    "phone": "086-284-1118",
    "website": "https://www.okayama-junshinkai.co.jp/facility/nursery/poem",
    "evidence": "https://www.okayama-junshinkai.co.jp/facility/nursery/poem"
  },
  {
    "names": [
      "かしのみ保育園"
    ],
    "phone": "086-279-5750",
    "website": "https://konominoki.ed.jp/kashinomi/",
    "evidence": "https://konominoki.ed.jp/kashinomi/"
  },
  {
    "names": [
      "たんぽぽ保育園"
    ],
    "phone": "086-948-9377",
    "website": "https://www.tannpopo-tubomi.com/tanpopo",
    "evidence": "https://www.tannpopo-tubomi.com/tanpopo"
  },
  {
    "names": [
      "操南保育園"
    ],
    "phone": "086-277-3431",
    "website": "http://sounan.jp/",
    "evidence": "https://www.hik-okayama.jp/pr/detail.php?id=331"
  }
]

def norm_phone(v):
    return re.sub(r"\D", "", str(v or ""))

def norm_name(v):
    return (
        str(v or "")
        .replace("　", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("・", "")
        .strip()
    )

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])

    by_phone = {}
    for f in facilities:
        by_phone.setdefault(norm_phone(f.get("phone")), []).append(f)

    updated = []
    errors = []

    for row in BATCH:
        phone_candidates = by_phone.get(norm_phone(row["phone"]), [])
        candidates = []

        if len(phone_candidates) == 1:
            candidates = phone_candidates
        elif len(phone_candidates) > 1:
            aliases = {norm_name(x) for x in row["names"]}
            candidates = [
                f for f in phone_candidates
                if norm_name(f.get("name")) in aliases
            ]

        if len(candidates) != 1:
            errors.append({
                **row,
                "reason": f"candidate-count={len(candidates)}",
                "phone_candidates": [
                    {
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "phone": f.get("phone"),
                    }
                    for f in phone_candidates
                ],
            })
            continue

        f = candidates[0]

        if f.get("public_private") != "私立":
            errors.append({
                **row,
                "reason": f'public_private={f.get("public_private")}',
                "matched_name": f.get("name"),
            })
            continue

        f["website"] = row["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = row["evidence"]

        updated.append({
            "id": f["id"],
            "name": f["name"],
            "phone": f.get("phone", ""),
            "website": row["website"],
            "evidence": row["evidence"],
        })

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch": 3,
        "target_count": len(BATCH),
        "verified_count": len(updated),
        "error_count": len(errors),
        "verified": updated,
        "errors": errors,
    }

    AUDIT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"[private-websites-batch3] "
        f"verified={len(updated)}/{len(BATCH)} "
        f"errors={len(errors)}"
    )

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            "Batch 3 の固定マスタ照合に失敗しました。"
            "facility_master.json は更新しません。"
        )

    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[private-websites-batch3] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
