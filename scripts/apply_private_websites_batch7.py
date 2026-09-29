#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch7.json"
BATCH = [
  {
    "names": [
      "高島第一保育園"
    ],
    "phone": "086-275-1755",
    "ward": "中区",
    "postal": "703-8205",
    "address_key": "中井4",
    "website": "https://dorodan5.jimdofree.com/",
    "evidence": "https://dorodan5.jimdofree.com/本園の保育について/"
  },
  {
    "names": [
      "瀬戸桜保育園"
    ],
    "phone": "086-952-0448",
    "ward": "東区",
    "postal": "709-0856",
    "address_key": "瀬戸町下133",
    "website": "https://seto.sakurakai.okayama.jp/",
    "evidence": "https://seto.sakurakai.okayama.jp/"
  },
  {
    "names": [
      "こども園 城東チャイルドセンター",
      "こども園城東チャイルドセンター",
      "城東チャイルドセンター"
    ],
    "phone": "086-278-8500",
    "ward": "中区",
    "postal": "703-8223",
    "address_key": "長利194",
    "website": "https://www.chitosek.or.jp/preschools/joto",
    "evidence": "https://www.chitosek.or.jp/preschools/joto"
  },
  {
    "names": [
      "ちどり保育園"
    ],
    "phone": "086-264-5915",
    "ward": "南区",
    "postal": "702-8037",
    "address_key": "千鳥町7",
    "website": "https://www.okayama-chidori.or.jp/hoiku/chidori",
    "evidence": "https://www.okayama-chidori.or.jp/hoiku/chidori"
  },
  {
    "names": [
      "紅陽台ちどり保育園"
    ],
    "phone": "086-362-2241",
    "ward": "南区",
    "postal": "709-1203",
    "address_key": "西紅陽台3",
    "website": "https://www.okayama-chidori.or.jp/hoiku/kouyoudai",
    "evidence": "https://www.okayama-chidori.or.jp/hoiku/kouyoudai"
  },
  {
    "names": [
      "妹尾保育園"
    ],
    "phone": "086-282-1106",
    "ward": "南区",
    "postal": "701-0205",
    "address_key": "妹尾1368",
    "website": "https://www.dousinkai.com/seno/index.html",
    "evidence": "https://www.dousinkai.com/seno/index.html"
  },
  {
    "names": [
      "第二福田保育園"
    ],
    "phone": "086-230-6652",
    "ward": "南区",
    "postal": "701-0205",
    "address_key": "妹尾3763",
    "website": "https://www.dousinkai.com/daini/index.html",
    "evidence": "https://www.dousinkai.com/daini/index.html"
  },
  {
    "names": [
      "箕島保育園"
    ],
    "phone": "086-282-0823",
    "ward": "南区",
    "postal": "701-0206",
    "address_key": "箕島2413",
    "website": "https://mishimahoikuen.com/",
    "evidence": "https://mishimahoikuen.com/"
  },
  {
    "names": [
      "白鳩保育園"
    ],
    "phone": "086-262-3432",
    "ward": "南区",
    "postal": "702-8032",
    "address_key": "福富中2",
    "website": "https://shirobato.ed.jp/",
    "evidence": "https://shirobato.ed.jp/about_us.html"
  },
  {
    "names": [
      "うらやす白鳩保育園"
    ],
    "phone": "086-261-5566",
    "ward": "南区",
    "postal": "702-8026",
    "address_key": "浦安本町171",
    "website": "https://shirobato.ed.jp/",
    "evidence": "https://shirobato.ed.jp/contact.html"
  },
  {
    "names": [
      "アイグラン保育園平福"
    ],
    "phone": "086-250-7527",
    "ward": "南区",
    "postal": "702-8043",
    "address_key": "平福1",
    "website": "https://aigran.co.jp/nursery/ninka/nursery-620/",
    "evidence": "https://aigran.co.jp/nursery/ninka/nursery-620/"
  },
  {
    "names": [
      "イートンちどり保育園"
    ],
    "phone": "086-265-5561",
    "ward": "南区",
    "postal": "702-8024",
    "address_key": "浦安南町425",
    "website": "https://www.eatone.co.jp/chidori/",
    "evidence": "https://www.eatone.co.jp/chidori/outline/"
  },
  {
    "names": [
      "アートチャイルドケア岡山豊成保育園"
    ],
    "phone": "086-230-1667",
    "ward": "南区",
    "postal": "700-0942",
    "address_key": "豊成1",
    "website": "https://www.the0123child.com/personal/24373/",
    "evidence": "https://www.the0123child.com/personal/24373/"
  },
  {
    "names": [
      "アートチャイルドケア岡山新保保育園"
    ],
    "phone": "086-226-2500",
    "ward": "南区",
    "postal": "700-0945",
    "address_key": "新保1113",
    "website": "https://www.the0123child.com/personal/16459/",
    "evidence": "https://www.the0123child.com/personal/16459/"
  },
  {
    "names": [
      "さつき保育園"
    ],
    "phone": "086-241-6524",
    "ward": "南区",
    "postal": "700-0944",
    "address_key": "泉田402",
    "website": "https://satsukihoikuen.jp/",
    "evidence": "https://satsukihoikuen.jp/invitation/"
  },
  {
    "names": [
      "当新田ちとせ保育園"
    ],
    "phone": "086-244-0188",
    "ward": "南区",
    "postal": "700-0956",
    "address_key": "当新田482",
    "website": "https://www.chitosek.or.jp/preschools/toushinden",
    "evidence": "https://www.chitosek.or.jp/preschools/toushinden"
  },
  {
    "names": [
      "ニチイキッズ西市保育園"
    ],
    "phone": "086-241-3132",
    "ward": "南区",
    "postal": "700-0953",
    "address_key": "西市115",
    "website": "https://www.nichiikids.net/nursery/nishiichi/",
    "evidence": "https://www.nichiikids.net/nursery/nishiichi/introduction/overview/"
  },
  {
    "names": [
      "御南認定こども園"
    ],
    "phone": "086-244-6100",
    "ward": "北区",
    "postal": "701-0145",
    "address_key": "今保247",
    "website": "https://minan-nintei.com/",
    "evidence": "https://minan-nintei.com/about/outline/"
  },
  {
    "names": [
      "御南まんまるこども園"
    ],
    "phone": "086-244-6111",
    "ward": "北区",
    "postal": "700-0951",
    "address_key": "田中165",
    "website": "https://minan-manmaru.com/",
    "evidence": "https://minan-manmaru.com/about/outline/"
  },
  {
    "names": [
      "第一吉備こども園"
    ],
    "phone": "086-293-7575",
    "ward": "北区",
    "postal": "701-0151",
    "address_key": "平野1071",
    "website": "https://daiichi.kibifukushikai.jp/",
    "evidence": "https://daiichi.kibifukushikai.jp/contact/"
  },
  {
    "names": [
      "第二吉備こども園"
    ],
    "phone": "086-293-7777",
    "ward": "北区",
    "postal": "701-0153",
    "address_key": "庭瀬1032",
    "website": "https://daini.kibifukushikai.jp/",
    "evidence": "https://daini.kibifukushikai.jp/contact/"
  }
]

def norm_phone(v):
    return re.sub(r"\D", "", str(v or ""))

def norm_name(v):
    s = str(v or "").replace("　","").replace(" ","").replace("（","(").replace("）",")")
    return s.replace("・","").strip()

def norm_addr(v):
    return (str(v or "").replace("　","").replace(" ","").replace("番地","-").replace("番","-")
            .replace("丁目","-").replace("−","-").replace("ー","-"))

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])
    by_phone = {}
    for f in facilities:
        p = norm_phone(f.get("phone"))
        if p:
            by_phone.setdefault(p, []).append(f)

    updated, errors = [], []

    for row in BATCH:
        phone_candidates = by_phone.get(norm_phone(row["phone"]), [])
        candidates = phone_candidates[:]

        # If the old master phone is stale/missing, fall back to:
        # alias + ward + postal/address. This avoids repeats of Batch 5/6 failures.
        if len(candidates) != 1:
            aliases = {norm_name(x) for x in row["names"]}
            named = [f for f in facilities if norm_name(f.get("name")) in aliases]
            candidates = [
                f for f in named
                if f.get("ward") == row["ward"]
                and (
                    row["postal"] in str(f.get("postal") or "")
                    or norm_addr(row["address_key"]) in norm_addr(f.get("address"))
                )
            ]

        if len(candidates) != 1:
            errors.append({
                **row,
                "reason": f"candidate-count={len(candidates)}",
                "phone_candidates": [
                    {"id":f.get("id"),"name":f.get("name"),"phone":f.get("phone"),
                      "postal":f.get("postal"),"address":f.get("address")}
                    for f in phone_candidates
                ]
            })
            continue

        f = candidates[0]
        if f.get("public_private") != "私立":
            errors.append({**row, "reason":f"public_private={f.get('public_private')}",
                           "matched_name":f.get("name")})
            continue

        before = f.get("website","")
        f["website"] = row["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = row["evidence"]
        updated.append({
            "id":f.get("id"),"name":f.get("name"),"phone":f.get("phone"),
            "website_before":before,"website":row["website"],"evidence":row["evidence"]
        })

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch": 7,
        "target_count": len(BATCH),
        "verified_count": len(updated),
        "error_count": len(errors),
        "verified": updated,
        "errors": errors
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    # Preserve strict safety: all 21 must resolve before master is written.
    if errors or len(updated) != len(BATCH):
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        raise RuntimeError(
            f"Batch 7 validation failed: {len(updated)}/{len(BATCH)} verified, "
            f"{len(errors)} unresolved. facility_master.json was not written."
        )

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"[batch7] verified={len(updated)}/{len(BATCH)} errors=0")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch7] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
