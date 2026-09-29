#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit.json"

BATCH = [
  {
    "name": "弓之町保育園",
    "phone": "086-222-7583",
    "website": "https://yuminocho-hoikuen.jp/",
    "evidence": "https://yuminocho-hoikuen.jp/"
  },
  {
    "name": "なかよし保育園",
    "phone": "086-255-4134",
    "website": "https://www.kids-nakayoshi.jp/nakayoshi/",
    "evidence": "https://www.kids-nakayoshi.jp/nakayoshi/"
  },
  {
    "name": "宝島保育園",
    "phone": "086-254-6888",
    "website": "https://tkjm.or.jp/takarajima/",
    "evidence": "https://tkjm.or.jp/takarajima/"
  },
  {
    "name": "第二宝島保育園",
    "phone": "086-239-9100",
    "website": "https://tkjm.or.jp/dainitakarajima/",
    "evidence": "https://tkjm.or.jp/dainitakarajima/"
  },
  {
    "name": "みかど貴ッズ保育園",
    "phone": "086-252-9936",
    "website": "https://mikadokids.jimdofree.com/",
    "evidence": "https://mikadokids.jimdofree.com/"
  },
  {
    "name": "たちばな上中野保育園",
    "phone": "086-241-0378",
    "website": "https://tachibana-k.or.jp/",
    "evidence": "https://tachibana-k.or.jp/"
  },
  {
    "name": "大元ちどり保育園",
    "phone": "086-206-2211",
    "website": "https://www.okayama-chidori.or.jp/hoiku/omoto",
    "evidence": "https://www.okayama-chidori.or.jp/hoiku/omoto"
  },
  {
    "name": "北長瀬ちどり保育園",
    "phone": "086-230-7115",
    "website": "https://www.okayama-chidori.or.jp/hoiku/kitanagase",
    "evidence": "https://www.okayama-chidori.or.jp/hoiku/kitanagase"
  },
  {
    "name": "からたち保育園",
    "phone": "086-224-7369",
    "website": "https://karatachihoikuen.com/",
    "evidence": "https://karatachihoikuen.com/"
  },
  {
    "name": "土の子保育園",
    "phone": "086-232-0825",
    "website": "https://www.tsuchinoko-net.com/",
    "evidence": "https://www.tsuchinoko-net.com/"
  },
  {
    "name": "ひらたえがお保育園",
    "phone": "086-805-3818",
    "website": "https://hirata-asahigawasou.jp/institutions/detail.php?id=5",
    "evidence": "https://hirata-asahigawasou.jp/institutions/detail.php?id=5"
  },
  {
    "name": "第二すみれ保育園",
    "phone": "086-295-2000",
    "website": "https://www.sojahukushikai.com/about/sumire-02/",
    "evidence": "https://www.sojahukushikai.com/about/sumire-02/"
  },
  {
    "name": "岡山協立保育園",
    "phone": "086-272-4111",
    "website": "https://waiwai-kyoritsu.sakura.ne.jp/",
    "evidence": "https://waiwai-kyoritsu.sakura.ne.jp/"
  },
  {
    "name": "三友保育園",
    "phone": "086-272-1786",
    "website": "https://sanyu-hoikuen.ed.jp/",
    "evidence": "https://sanyu-hoikuen.ed.jp/facility/about/"
  },
  {
    "name": "白菊保育園",
    "phone": "086-277-7609",
    "website": "https://shiragiku.ed.jp/",
    "evidence": "https://shiragiku.ed.jp/"
  },
  {
    "name": "第二白ゆり保育園",
    "phone": "086-284-5224",
    "website": "https://dai2-shirayuri.com/",
    "evidence": "https://dai2-shirayuri.com/report/"
  },
  {
    "name": "くまの子保育園",
    "phone": "086-942-5958",
    "website": "https://kumanokohoikuen.jp/",
    "evidence": "https://kumanokohoikuen.jp/"
  }
]

def norm_phone(v):
    return re.sub(r"\D", "", str(v or ""))

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])

    by_name = {}
    for f in facilities:
        by_name.setdefault(f.get("name", ""), []).append(f)

    updated = []
    errors = []

    for row in BATCH:
        candidates = by_name.get(row["name"], [])

        if len(candidates) != 1:
            errors.append({
                **row,
                "reason": f"name-match={len(candidates)}",
            })
            continue

        f = candidates[0]

        if f.get("public_private") != "私立":
            errors.append({
                **row,
                "reason": f'public_private={f.get("public_private")}',
            })
            continue

        if norm_phone(f.get("phone")) != norm_phone(row["phone"]):
            errors.append({
                **row,
                "reason": f'phone-mismatch master={f.get("phone")}',
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
        "batch": 1,
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
        f"[private-websites-batch1] "
        f"verified={len(updated)}/{len(BATCH)} errors={len(errors)}"
    )

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            "精査済みURLの固定マスタ照合に失敗しました。"
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
        print(f"[private-websites-batch1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
