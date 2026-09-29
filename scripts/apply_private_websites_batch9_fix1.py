#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "private_website_audit_batch9_fix1.json"
BATCH = [
  {
    "names": [
      "桃太郎こども園",
      "桃太郎保育園",
      "（仮称）桃太郎こども園",
      "(仮称)桃太郎こども園"
    ],
    "ward": "東区",
    "current_name": "桃太郎こども園",
    "website": "https://momotarouhoikuen.ed.jp/",
    "evidence": "https://momotarouhoikuen.ed.jp/"
  },
  {
    "names": [
      "竜之口わかばこども園"
    ],
    "ward": "中区",
    "website": "https://tatsunokuchiwakaba.com/",
    "evidence": "https://tatsunokuchiwakaba.com/"
  },
  {
    "names": [
      "内山下幼稚園"
    ],
    "ward": "北区",
    "website": "https://www.uchisange.com/",
    "evidence": "https://www.uchisange.com/"
  },
  {
    "names": [
      "岡北学園",
      "認定こども園岡北学園"
    ],
    "ward": "北区",
    "website": "https://www.kouhoku.com/",
    "evidence": "https://www.kouhoku.com/"
  },
  {
    "names": [
      "さくらこども園"
    ],
    "ward": "北区",
    "website": "https://sakurakids.jp/",
    "evidence": "https://sakurakids.jp/access/"
  },
  {
    "names": [
      "第二さくらこども園"
    ],
    "ward": "北区",
    "website": "https://www.sakurakids2.jp/",
    "evidence": "https://www.sakurakids2.jp/"
  },
  {
    "names": [
      "もみの木こども園"
    ],
    "ward": "北区",
    "website": "https://www.mominokikko.jp/",
    "evidence": "https://www.mominokikko.jp/message/company"
  },
  {
    "names": [
      "ゆりかごこども園"
    ],
    "ward": "中区",
    "website": "https://yurikagokodomoen.com/",
    "evidence": "https://yurikagokodomoen.com/index02"
  },
  {
    "names": [
      "豊こども園"
    ],
    "ward": "東区",
    "website": "https://kyokutouaijikai.ed.jp/toyo/",
    "evidence": "https://kyokutouaijikai.ed.jp/toyo/"
  },
  {
    "names": [
      "つきのさとこども園"
    ],
    "ward": "東区",
    "website": "https://www.chitosek.or.jp/preschools/tsukinosato",
    "evidence": "https://www.chitosek.or.jp/preschools/tsukinosato",
    "phone": "086-238-5107",
    "postal": "704-8193",
    "address_key": "金岡西町578"
  },
  {
    "names": [
      "江西桜こども園"
    ],
    "ward": "東区",
    "website": "https://kousai.sakurakai.okayama.jp/",
    "evidence": "https://kousai.sakurakai.okayama.jp/"
  },
  {
    "names": [
      "福田こども園"
    ],
    "ward": "南区",
    "website": "https://dousinkai.com/fukuda/index.html",
    "evidence": "https://dousinkai.com/fukuda/index.html"
  },
  {
    "names": [
      "第二すこやか保育園",
      "すこやか第二保育園"
    ],
    "ward": "北区",
    "website": "https://sukoyakahoikuen.com/",
    "evidence": "https://sukoyakahoikuen.com/about/",
    "phone": "086-239-0208",
    "postal": "701-1212",
    "address_key": "尾上1318-3"
  },
  {
    "names": [
      "もりの香保育園 津高園",
      "もりの香保育園津高園",
      "もりの香(か)保育園津高(つだか)園"
    ],
    "ward": "北区",
    "website": "https://www.morinoka.jp/",
    "evidence": "https://www.morinoka.jp/about/",
    "phone": "086-259-3755",
    "postal": "701-1152",
    "address_key": "津高408-1"
  },
  {
    "names": [
      "小規模保育園あかとんぼはつみ園",
      "小規模保育園 あかとんぼ はつみ園",
      "小規模保育園あかとんぼ はつみ園",
      "あかとんぼはつみ園"
    ],
    "ward": "中区",
    "website": "https://akatonbo-hoikuen.com/",
    "evidence": "https://akatonbo-hoikuen.com/more.html",
    "phone": "086-238-5520",
    "postal": "",
    "address_key": "乙多見502"
  },
  {
    "names": [
      "きらきら小規模保育園豊成"
    ],
    "ward": "南区",
    "website": "https://www.kirakira-hoikuen.com/introduction/index_2.html",
    "evidence": "https://www.kirakira-hoikuen.com/introduction/index_2.html"
  },
  {
    "names": [
      "アートチャイルドケア岡山庭瀬保育園"
    ],
    "ward": "北区",
    "website": "https://www.the0123child.com/personal/7955/",
    "evidence": "https://www.the0123child.com/personal/7955/"
  },
  {
    "names": [
      "星の子保育園"
    ],
    "ward": "北区",
    "website": "https://hoshinoko.kawada.or.jp/",
    "evidence": "https://hoshinoko.kawada.or.jp/recruit.html"
  },
  {
    "names": [
      "玉井桜保育園"
    ],
    "ward": "東区",
    "website": "https://sakurakai.okayama.jp/",
    "evidence": "https://sakurakai.okayama.jp/"
  },
  {
    "names": [
      "古都こども園"
    ],
    "ward": "東区",
    "website": "https://www.chitosek.or.jp/preschools/kozu",
    "evidence": "https://www.chitosek.or.jp/preschools/kozu"
  },
  {
    "names": [
      "めぐみ幼保連携型認定こども園",
      "幼保連携型認定こども園めぐみ"
    ],
    "ward": "東区",
    "website": "https://megumihoikuenn-kubo.jp/",
    "evidence": "https://megumihoikuenn-kubo.jp/outline/"
  },
  {
    "names": [
      "めぐみ第二幼保連携型認定こども園",
      "幼保連携型認定こども園めぐみ第二"
    ],
    "ward": "東区",
    "website": "https://megumihoikuenn-kubo.jp/",
    "evidence": "https://megumihoikuenn-kubo.jp/outline/"
  },
  {
    "names": [
      "幼保連携型認定こども園あんじゅの里",
      "認定こども園あんじゅの里",
      "あんじゅの里"
    ],
    "ward": "北区",
    "website": "https://www.fukujukai-gp.com/",
    "evidence": "https://www.fukujukai-gp.com/"
  }
]

def norm_name(v):
    return (str(v or "").replace("　","").replace(" ","")
            .replace("（","(").replace("）",")").replace("・","").strip())

def norm_phone(v):
    return re.sub(r"\D", "", str(v or ""))

def norm_addr(v):
    return (str(v or "").replace("岡山県","").replace("岡山市","")
            .replace("　","").replace(" ","").replace("番地","-").replace("番","-")
            .replace("丁目","-").replace("−","-").replace("ー","-"))

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
        method = "name+ward"

        # For the four known naming mismatches, use verified current
        # phone/postal/address as a second independent locator.
        if len(candidates) != 1 and row.get("phone"):
            p = norm_phone(row["phone"])
            by_phone = [f for f in facilities if norm_phone(f.get("phone")) == p]
            if len(by_phone) == 1:
                candidates = by_phone
                method = "official-phone"
            else:
                addr_key = norm_addr(row.get("address_key"))
                postal = re.sub(r"\D", "", row.get("postal",""))
                by_location = [
                    f for f in facilities
                    if f.get("ward") == row["ward"]
                    and (
                        (postal and postal in re.sub(r"\D","",str(f.get("postal") or "")))
                        or (addr_key and addr_key in norm_addr(f.get("address")))
                    )
                ]
                if len(by_location) == 1:
                    candidates = by_location
                    method = "official-location"

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
            errors.append({**row,"reason":f"public_private={f.get('public_private')}",
                           "matched_name":f.get("name")})
            continue

        before = {"name":f.get("name"),"website":f.get("website"),
                  "website_status":f.get("website_status")}
        if row.get("current_name"):
            f["name"] = row["current_name"]

        f["website"] = row["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = row["evidence"]

        updated.append({
            "id":f.get("id"),"name":f.get("name"),"ward":f.get("ward"),
            "match_method":method,"before":before,
            "website":row["website"],"evidence":row["evidence"]
        })

    audit = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch":"9-fix1",
        "target_count":len(BATCH),
        "verified_count":len(updated),
        "error_count":len(errors),
        "excluded_from_master":[{
            "name":"認定こども園あけぼの幼稚園",
            "reason":"岡山市の私立幼稚園（教育利用）として扱われ、この保育利用固定マスタの対象外"
        }],
        "verified":updated,
        "errors":errors
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    if errors or len(updated) != len(BATCH):
        raise RuntimeError(
            f"Batch 9 fix validation failed: {len(updated)}/{len(BATCH)} verified, "
            f"{len(errors)} unresolved. facility_master.json was not written."
        )

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"[batch9-fix1] verified={len(updated)}/{len(BATCH)} errors=0")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch9-fix1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
