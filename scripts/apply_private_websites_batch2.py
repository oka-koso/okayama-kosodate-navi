#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch2.json"

BATCH = [
  {
    "names": [
      "朝日塾こども園"
    ],
    "phone": "086-243-4111",
    "website": "https://www.asahijuku.ac.jp/kindergarten/",
    "evidence": "https://www.asahijuku.ac.jp/kindergarten/"
  },
  {
    "names": [
      "就実こども園",
      "認定こども園 就実",
      "認定こども園就実"
    ],
    "phone": "086-206-2112",
    "website": "https://kids.shujitsu.ac.jp/",
    "evidence": "https://kids.shujitsu.ac.jp/"
  },
  {
    "names": [
      "第一ひかりこども園"
    ],
    "phone": "086-262-2602",
    "website": "https://hikari-gakuen.ac.jp/",
    "evidence": "https://hikari-gakuen.ac.jp/outline-2/"
  },
  {
    "names": [
      "第二ひかりこども園"
    ],
    "phone": "086-263-7492",
    "website": "https://hikari-gakuen.ac.jp/",
    "evidence": "https://hikari-gakuen.ac.jp/"
  },
  {
    "names": [
      "高島おひさまこども園"
    ],
    "phone": "086-275-1998",
    "website": "https://oomorigakuen.ed.jp/takashima/",
    "evidence": "https://oomorigakuen.ed.jp/takashima/"
  },
  {
    "names": [
      "つしまこども園"
    ],
    "phone": "086-252-0171",
    "website": "https://oomorigakuen.ed.jp/",
    "evidence": "https://oomorigakuen.ed.jp/"
  },
  {
    "names": [
      "おおふくこども園"
    ],
    "phone": "086-282-3700",
    "website": "https://okayama-tokokai.jp/kakuen-shoukai/",
    "evidence": "https://okayama-tokokai.jp/kakuen-shoukai/"
  },
  {
    "names": [
      "大元こども園"
    ],
    "phone": "086-259-3700",
    "website": "https://okayama-tokokai.jp/kakuen-shoukai/",
    "evidence": "https://okayama-tokokai.jp/kakuen-shoukai/"
  },
  {
    "names": [
      "ならの木こども園"
    ],
    "phone": "086-242-3400",
    "website": "https://okayama-tokokai.jp/kakuen-shoukai/",
    "evidence": "https://okayama-tokokai.jp/kakuen-shoukai/"
  },
  {
    "names": [
      "どんぐり保育園"
    ],
    "phone": "086-244-6600",
    "website": "https://okayama-tokokai.jp/kakuen-shoukai/",
    "evidence": "https://okayama-tokokai.jp/kakuen-shoukai/"
  },
  {
    "names": [
      "ノイエ保育園"
    ],
    "phone": "086-244-6600",
    "website": "https://okayama-tokokai.jp/kakuen-shoukai/",
    "evidence": "https://okayama-tokokai.jp/kakuen-shoukai/"
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
        "batch": 2,
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
        f"[private-websites-batch2] "
        f"verified={len(updated)}/{len(BATCH)} "
        f"errors={len(errors)}"
    )

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            "Batch 2 の固定マスタ照合に失敗しました。"
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
        print(f"[private-websites-batch2] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
