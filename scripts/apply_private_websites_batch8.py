#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch8.json"
BATCH = [
  {
    "names": [
      "弘西こども園"
    ],
    "ward": "北区",
    "website": "https://www.kids-nakayoshi.jp/kosai/",
    "evidence": "https://www.kids-nakayoshi.jp/kosai/annai/index.html"
  },
  {
    "names": [
      "蓮昌寺こども園"
    ],
    "ward": "北区",
    "website": "https://www.renjyojikodomoen.or.jp/",
    "evidence": "https://www.renjyojikodomoen.or.jp/"
  },
  {
    "names": [
      "若草幼児舎"
    ],
    "ward": "北区",
    "website": "https://wakakusa.kawada.or.jp/",
    "evidence": "https://wakakusa.kawada.or.jp/introduction.html"
  },
  {
    "names": [
      "じゅんせい認定こども園"
    ],
    "ward": "北区",
    "website": "https://www.junsei-hoikuen.jp/",
    "evidence": "https://www.junsei-hoikuen.jp/"
  },
  {
    "names": [
      "京山こども園"
    ],
    "ward": "北区",
    "website": "https://kyo-yama.com/",
    "evidence": "https://kyo-yama.com/"
  },
  {
    "names": [
      "認定こども園 白ゆり",
      "認定こども園白ゆり"
    ],
    "ward": "北区",
    "website": "https://www.shirayurikai.com/shirayurihoiku/",
    "evidence": "https://www.shirayurikai.com/shirayurihoiku/pages/about/index.html"
  },
  {
    "names": [
      "第三吉備こども園"
    ],
    "ward": "北区",
    "website": "https://daisan.kibifukushikai.jp/",
    "evidence": "https://daisan.kibifukushikai.jp/"
  },
  {
    "names": [
      "ポエムこども園ひらつ"
    ],
    "ward": "北区",
    "website": "https://www.okayama-junshinkai.co.jp/facility/nursery/poem2",
    "evidence": "https://www.okayama-junshinkai.co.jp/facility/nursery/poem2"
  },
  {
    "names": [
      "馬屋下まんまるこども園"
    ],
    "ward": "北区",
    "website": "https://mayashimo-manmaru.com/",
    "evidence": "https://mayashimo-manmaru.com/admission/"
  },
  {
    "names": [
      "認定こども園 白ゆりの丘",
      "認定こども園白ゆりの丘"
    ],
    "ward": "北区",
    "website": "https://www.shirayurikai.com/shirayurinooka/",
    "evidence": "https://www.shirayurikai.com/shirayurinooka/"
  },
  {
    "names": [
      "つしま幼稚園"
    ],
    "ward": "北区",
    "website": "https://oomorigakuen.ed.jp/",
    "evidence": "https://oomorigakuen.ed.jp/"
  },
  {
    "names": [
      "聖さくら学院保育園"
    ],
    "ward": "北区",
    "website": "https://www.sento-sakura.com/gakuin/",
    "evidence": "https://www.sento-sakura.com/gakuin/"
  },
  {
    "names": [
      "聖さくら第二保育園"
    ],
    "ward": "北区",
    "website": "https://www.sento-sakura.com/hoikuen-02/",
    "evidence": "https://www.sento-sakura.com/hoikuen-02/"
  },
  {
    "names": [
      "ニチイキッズいま保育園"
    ],
    "ward": "北区",
    "website": "https://www.nichiikids.net/nursery/ima/",
    "evidence": "https://www.nichiikids.net/nursery/ima/introduction/overview/"
  },
  {
    "names": [
      "（仮称）きらめき六区こども園",
      "(仮称)きらめき六区こども園",
      "きらめき六区こども園"
    ],
    "ward": "南区",
    "current_name": "きらめき六区こども園",
    "website": "https://tsukushi-fukushi.com/rokku/",
    "evidence": "https://tsukushi-fukushi.com/rokku/overview.php"
  },
  {
    "names": [
      "小規模保育園あかとんぼ",
      "小規模保育園 あかとんぼ"
    ],
    "ward": "中区",
    "website": "https://akatonbo-hoikuen.com/",
    "evidence": "https://akatonbo-hoikuen.com/more.html"
  },
  {
    "names": [
      "小規模保育園あかとんぼ第二園",
      "小規模保育園 あかとんぼ 第二園"
    ],
    "ward": "中区",
    "website": "https://akatonbo-hoikuen.com/",
    "evidence": "https://akatonbo-hoikuen.com/more.html"
  },
  {
    "names": [
      "ソラ小規模保育園おかやま"
    ],
    "ward": "北区",
    "website": "https://sora-hoikuen.jp/kakuen.html",
    "evidence": "https://sora-hoikuen.jp/kakuen.html"
  },
  {
    "names": [
      "ソラ小規模保育園いま"
    ],
    "ward": "北区",
    "website": "https://sora-hoikuen.jp/kakuen.html",
    "evidence": "https://sora-hoikuen.jp/kakuen.html"
  },
  {
    "names": [
      "ソラ小規模保育園ふくだ"
    ],
    "ward": "南区",
    "website": "https://sora-hoikuen.jp/kakuen.html",
    "evidence": "https://sora-hoikuen.jp/kakuen.html"
  },
  {
    "names": [
      "キッズガーデン白ゆり"
    ],
    "ward": "南区",
    "website": "https://www.shirayurikai.com/kidsgarden/",
    "evidence": "https://www.shirayurikai.com/kidsgarden/"
  },
  {
    "names": [
      "つしまおひさま保育園"
    ],
    "ward": "北区",
    "website": "https://oomorigakuen.ed.jp/hoikuen/",
    "evidence": "https://oomorigakuen.ed.jp/hoikuen/"
  },
  {
    "names": [
      "きらきら小規模保育園西市"
    ],
    "ward": "南区",
    "website": "https://www.kirakira-hoikuen.com/introduction/index_3.html",
    "evidence": "https://www.kirakira-hoikuen.com/introduction/index_3.html"
  },
  {
    "names": [
      "白ゆり小規模保育園"
    ],
    "ward": "北区",
    "website": "https://www.shirayurikai.com/syokibohoiku/",
    "evidence": "https://www.shirayurikai.com/syokibohoiku/"
  },
  {
    "names": [
      "すくすくランド・ポストメイト保育園",
      "すくすくランドポストメイト保育園"
    ],
    "ward": "南区",
    "website": "https://postmate.jp/nursery/307.html",
    "evidence": "https://postmate.jp/nursery/307.html"
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
                      "phone":f.get("phone"),"address":f.get("address")}
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
            "name": f.get("name"),
            "website": f.get("website"),
            "website_status": f.get("website_status"),
        }

        if row.get("current_name"):
            f["name"] = row["current_name"]

        f["website"] = row["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = row["evidence"]

        updated.append({
            "id": f.get("id"),
            "name": f.get("name"),
            "ward": f.get("ward"),
            "before": before,
            "website": row["website"],
            "evidence": row["evidence"],
        })

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch": 8,
        "target_count": len(BATCH),
        "verified_count": len(updated),
        "error_count": len(errors),
        "verified": updated,
        "errors": errors,
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            f"Batch 8 validation failed: {len(updated)}/{len(BATCH)} verified, "
            f"{len(errors)} unresolved. facility_master.json was not written."
        )

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"[batch8] verified={len(updated)}/{len(BATCH)} errors=0")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch8] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
