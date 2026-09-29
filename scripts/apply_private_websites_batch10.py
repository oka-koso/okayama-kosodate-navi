#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch10.json"
BATCH = [
  {
    "names": [
      "旭川こども園"
    ],
    "ward": "中区",
    "website": "https://asahigawa-hoiku.com/",
    "evidence": "https://asahigawa-hoiku.com/"
  },
  {
    "names": [
      "柿の木こども園"
    ],
    "ward": "中区",
    "website": "https://www.kakinokiho.com/",
    "evidence": "https://www.kakinokiho.com/about.html"
  },
  {
    "names": [
      "グリーン長利こども園"
    ],
    "ward": "中区",
    "website": "https://www.chitosek.or.jp/preschools/gr-nagatoshi",
    "evidence": "https://www.chitosek.or.jp/preschools/gr-nagatoshi"
  },
  {
    "names": [
      "なのはなこども園"
    ],
    "ward": "中区",
    "website": "https://nanohana-kodomoen.jp/",
    "evidence": "https://nanohana-kodomoen.jp/nyuen.php"
  },
  {
    "names": [
      "クレイン小規模保育園"
    ],
    "ward": "南区",
    "website": "https://crane-nishiichi.jp/",
    "evidence": "https://crane-nishiichi.jp/about"
  },
  {
    "names": [
      "新保おひさま南保育園"
    ],
    "ward": "南区",
    "website": "https://shinbouohisama-m-hoikuen.jp/",
    "evidence": "https://shinbouohisama-m-hoikuen.jp/"
  },
  {
    "names": [
      "にこにこランドポストメイト保育園・国富",
      "にこにこランドポストメイト保育園国富"
    ],
    "ward": "中区",
    "website": "https://postmate.jp/nursery/306.html",
    "evidence": "https://postmate.jp/nursery/306.html"
  },
  {
    "names": [
      "小規模保育園いろいろ"
    ],
    "ward": "東区",
    "website": "https://www.chitosek.or.jp/preschools/iroiro",
    "evidence": "https://www.chitosek.or.jp/preschools/iroiro"
  },
  {
    "names": [
      "岡山済生会なでしこ保育園",
      "岡山済生会 なでしこ保育園"
    ],
    "ward": "北区",
    "website": "https://www.okayamasaiseikai.or.jp/facilities/institution/nadeshikoen/about_nadeshikoen/",
    "evidence": "https://www.okayamasaiseikai.or.jp/facilities/institution/nadeshikoen/about_nadeshikoen/"
  },
  {
    "names": [
      "みらい保育園"
    ],
    "ward": "北区",
    "website": "https://okayama-kotobuki.sakura.ne.jp/new/02facility/mirai.html",
    "evidence": "https://okayama-kotobuki.sakura.ne.jp/new/02facility/mirai.html"
  },
  {
    "names": [
      "心育保育園"
    ],
    "ward": "北区",
    "website": "https://stepup-sp.co.jp/service/kokoiku/",
    "evidence": "https://stepup-sp.co.jp/service/kokoiku/"
  },
  {
    "names": [
      "カナダこども園"
    ],
    "ward": "東区",
    "website": "https://www.chitosek.or.jp/preschools/canada",
    "evidence": "https://www.chitosek.or.jp/preschools/canada"
  },
  {
    "names": [
      "たんぽぽ・つぼみ保育園",
      "たんぽぽつぼみ保育園"
    ],
    "ward": "東区",
    "website": "https://www.tannpopo-tubomi.com/tsubomi",
    "evidence": "https://www.tannpopo-tubomi.com/admission"
  },
  {
    "names": [
      "（仮称）ひこさきこども園",
      "(仮称)ひこさきこども園",
      "ひこさきこども園"
    ],
    "ward": "南区",
    "current_name": "ひこさきこども園",
    "website": "https://nsfk.okayama.jp/hikosaki-kodomoen/",
    "evidence": "https://nsfk.okayama.jp/hikosaki-kodomoen/about/"
  },
  {
    "names": [
      "岡北保育園"
    ],
    "ward": "北区",
    "website": "https://www.kouhoku.com/",
    "evidence": "https://www.kouhoku.com/"
  },
  {
    "names": [
      "柿の木保育園"
    ],
    "ward": "中区",
    "website": "https://www.kakinokiho.com/",
    "evidence": "https://www.kakinokiho.com/"
  },
  {
    "names": [
      "ぷちあんじゅ",
      "ぶちあんじゅ"
    ],
    "ward": "北区",
    "website": "https://www.fukujukai-gp.com/",
    "evidence": "https://www.fukujukai-gp.com/"
  }
]

def norm_name(v):
    return (str(v or "").replace("　","").replace(" ","")
            .replace("（","(").replace("）",")").replace("・","").strip())

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])
    updated, errors = [], []

    for row in BATCH:
        aliases = {norm_name(x) for x in row["names"]}
        candidates = [
            f for f in facilities
            if norm_name(f.get("name")) in aliases and f.get("ward") == row["ward"]
        ]

        if len(candidates) != 1:
            errors.append({
                **row,
                "reason": f"candidate-count={len(candidates)}",
                "candidates": [
                    {"id":f.get("id"),"name":f.get("name"),"ward":f.get("ward"),
                      "phone":f.get("phone"),"postal":f.get("postal"),"address":f.get("address")}
                    for f in candidates
                ],
            })
            continue

        f = candidates[0]
        if f.get("public_private") != "私立":
            errors.append({
                **row,
                "reason": f"public_private={f.get('public_private')}",
                "matched_name": f.get("name"),
            })
            continue

        before = {
            "name":f.get("name"),
            "website":f.get("website"),
            "website_status":f.get("website_status"),
        }

        if row.get("current_name"):
            f["name"] = row["current_name"]

        f["website"] = row["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = row["evidence"]

        updated.append({
            "id":f.get("id"),"name":f.get("name"),"ward":f.get("ward"),
            "before":before,"website":row["website"],"evidence":row["evidence"]
        })

    audit = {
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "batch":10,
        "target_count":len(BATCH),
        "verified_count":len(updated),
        "error_count":len(errors),
        "verified":updated,
        "errors":errors,
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            f"Batch 10 validation failed: {len(updated)}/{len(BATCH)} verified, "
            f"{len(errors)} unresolved. facility_master.json was not written."
        )

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"[batch10] verified={len(updated)}/{len(BATCH)} errors=0")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch10] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
