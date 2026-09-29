#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch4.json"

BATCH = [
  {
    "names": [
      "みのりの木保育園"
    ],
    "phone": "086-230-6200",
    "website": "https://minorinokihoikuen.jimdofree.com/",
    "evidence": "https://minorinokihoikuen.jimdofree.com/当園について/"
  },
  {
    "names": [
      "学南保育園"
    ],
    "phone": "086-254-9571",
    "website": "https://ghoikuen.sakura.ne.jp/",
    "evidence": "https://ghoikuen.sakura.ne.jp/entrance.html"
  },
  {
    "names": [
      "あゆみ保育園"
    ],
    "phone": "086-254-2714",
    "website": "https://ayumihoikuen-okayama.or.jp/",
    "evidence": "https://ayumihoikuen-okayama.or.jp/"
  },
  {
    "names": [
      "第四ひかり保育園"
    ],
    "phone": "086-259-5565",
    "website": "https://www.s-hikari.or.jp/",
    "evidence": "https://www.s-hikari.or.jp/otoiawase/jyuyoujikou_r6.pdf"
  },
  {
    "names": [
      "橘今保育園"
    ],
    "phone": "086-241-2722",
    "website": "https://tatibanaima-hoikuen.com/",
    "evidence": "https://tatibanaima-hoikuen.com/qanda/"
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
        "batch": 4,
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
        f"[private-websites-batch4] "
        f"verified={len(updated)}/{len(BATCH)} "
        f"errors={len(errors)}"
    )

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            "Batch 4 の固定マスタ照合に失敗しました。"
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
        print(f"[private-websites-batch4] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
