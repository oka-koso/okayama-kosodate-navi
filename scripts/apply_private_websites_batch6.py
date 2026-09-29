#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch6.json"

BATCH = [
  {
    "names": [
      "桃丘こども園",
      "（仮称）桃丘こども園"
    ],
    "phone": "086-236-8780",
    "website": "https://cumre.or.jp/service/childcare/momogaoka/",
    "evidence": "https://cumre.or.jp/service/childcare/momogaoka/"
  },
  {
    "names": [
      "しいのみこども園"
    ],
    "phone": "086-279-9850",
    "website": "https://nozomi-kinder.ed.jp/",
    "evidence": "https://nozomi-kinder.ed.jp/"
  },
  {
    "names": [
      "浮田とちのみこども園"
    ],
    "phone": "086-206-1511",
    "website": "https://konominoki.ed.jp/tochinomi/",
    "evidence": "https://konominoki.ed.jp/tochinomi/"
  },
  {
    "names": [
      "東岡山IPUこども園",
      "東岡山ＩＰＵこども園"
    ],
    "phone": "086-206-4150",
    "website": "https://genkinoizumi.ed.jp/okayama/",
    "evidence": "https://genkinoizumi.ed.jp/okayama/"
  },
  {
    "names": [
      "ちとせ認定こども園"
    ],
    "phone": "086-942-6145",
    "website": "https://www.chitosek.or.jp/preschools/chitose",
    "evidence": "https://www.chitosek.or.jp/preschools/chitose"
  },
  {
    "names": [
      "原尾島こども園"
    ],
    "phone": "086-273-2730",
    "website": "https://www.chitosek.or.jp/preschools/haraoshima",
    "evidence": "https://www.chitosek.or.jp/preschools/haraoshima"
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
        .replace("ＩＰＵ", "IPU")
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
        "batch": 6,
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
        f"[private-websites-batch6] "
        f"verified={len(updated)}/{len(BATCH)} "
        f"errors={len(errors)}"
    )

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            "Batch 6 の固定マスタ照合に失敗しました。"
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
        print(f"[private-websites-batch6] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
