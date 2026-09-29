#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT/"data"/"facility_master.json"
AUDIT = ROOT/"data"/"private_website_audit_batch11.json"
REMAINING = ROOT/"data"/"private_website_remaining_after_batch11.json"
UPDATES = [
  {
    "id": "oky-8bf4f5cc8f77",
    "expected_name": "操南保育園(分園)",
    "website": "http://sounan.jp/",
    "evidence": "http://sounan.jp/"
  },
  {
    "id": "oky-5d696eff342a",
    "expected_name": "（仮称）岡山聖園マリア幼稚園",
    "current_name": "岡山聖園マリア幼稚園",
    "website": "https://misonogakuen.ed.jp/maria/",
    "evidence": "https://misonogakuen.ed.jp/maria/"
  },
  {
    "id": "oky-f429c8d7fe8c",
    "expected_name": "こじかこども園",
    "website": "https://kojika-okayama.ed.jp/",
    "evidence": "https://kojika-okayama.ed.jp/"
  },
  {
    "id": "oky-1f720255b07c",
    "expected_name": "ふたばこども園",
    "website": "https://futaba-okayama.ed.jp/",
    "evidence": "https://futaba-okayama.ed.jp/"
  },
  {
    "id": "oky-f950767f5dfe",
    "expected_name": "（仮称）たねのくに ちとせこども園",
    "current_name": "撫川ちとせこども園",
    "website": "https://www.chitosek.or.jp/preschools/natsukawa",
    "evidence": "https://www.chitosek.or.jp/preschools/natsukawa"
  },
  {
    "id": "oky-210bccc4e2e5",
    "expected_name": "岡山博愛会認定こども園",
    "website": "https://www.okayama-hakuaikai.or.jp/hakuaikai/nursery/",
    "evidence": "https://www.okayama-hakuaikai.or.jp/hakuaikai/nursery/"
  },
  {
    "id": "oky-af1ea3b22f80",
    "expected_name": "原尾島こども園",
    "website": "https://www.chitosek.or.jp/preschools/haraoshima",
    "evidence": "https://www.chitosek.or.jp/preschools/haraoshima"
  },
  {
    "id": "oky-a9b154c54514",
    "expected_name": "東岡山IPUこども園",
    "website": "https://genkinoizumi.ed.jp/okayama/",
    "evidence": "https://genkinoizumi.ed.jp/okayama/"
  },
  {
    "id": "oky-b5ce04971cbb",
    "expected_name": "ちとせ認定こども園",
    "website": "https://www.chitosek.or.jp/preschools/chitose",
    "evidence": "https://www.chitosek.or.jp/preschools/chitose"
  },
  {
    "id": "oky-92e89fe0f4fb",
    "expected_name": "しいのみこども園",
    "website": "https://nozomi-kinder.ed.jp/",
    "evidence": "https://nozomi-kinder.ed.jp/"
  },
  {
    "id": "oky-6e897ebf054a",
    "expected_name": "浮田とちのみこども園",
    "website": "https://konominoki.ed.jp/tochinomi/",
    "evidence": "https://konominoki.ed.jp/tochinomi/"
  },
  {
    "id": "oky-c81757e30b10",
    "expected_name": "（仮称）芳明こども園",
    "current_name": "芳明こども園",
    "phone": "086-259-1655",
    "website": "https://www.keizankai.or.jp/hoiku/houmei-kodomoen/",
    "evidence": "https://www.keizankai.or.jp/hoiku/houmei-kodomoen/"
  },
  {
    "id": "oky-0e9de12c1314",
    "expected_name": "小規模保育園しらかば",
    "website": "http://www.shirakaba-kai.com/shota.html",
    "evidence": "http://www.shirakaba-kai.com/shota.html"
  },
  {
    "id": "oky-694167f784c4",
    "expected_name": "たかまつすくすく保育園",
    "website": "https://gifukai.jp/facilities/sukusuku.html",
    "evidence": "https://gifukai.jp/facilities/sukusuku.html"
  },
  {
    "id": "oky-de68cfb6b3b6",
    "expected_name": "ほほえみ保育園",
    "website": "https://hoiku.medical-jiyukai.jp/",
    "evidence": "https://hoiku.medical-jiyukai.jp/"
  },
  {
    "id": "oky-00988b6a1b66",
    "expected_name": "さとちやん保育園",
    "current_name": "さとちゃん保育園",
    "address": "岡山市南区築港栄町2-13",
    "website": "https://www.sato-hp.com/meihoukai/hoikuen",
    "evidence": "https://www.sato-hp.com/meihoukai/hoikuen"
  }
]

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    fs = data.get("facilities", [])
    by_id = {f.get("id"):f for f in fs}
    changed, errors = [], []

    for u in UPDATES:
        f = by_id.get(u["id"])
        if not f:
            errors.append({**u,"reason":"id-not-found"})
            continue
        if f.get("public_private") != "私立":
            errors.append({**u,"reason":f"public_private={f.get('public_private')}","actual_name":f.get("name")})
            continue
        # IDs are stable, but also require the old/current expected name unless this
        # record has already been renamed by an earlier successful run.
        allowed_names = {u["expected_name"]}
        if u.get("current_name"):
            allowed_names.add(u["current_name"])
        if f.get("name") not in allowed_names:
            errors.append({**u,"reason":"name-mismatch","actual_name":f.get("name")})
            continue

        before = {
            "name":f.get("name"),"phone":f.get("phone"),"address":f.get("address"),
            "website":f.get("website"),"website_status":f.get("website_status")
        }
        if u.get("current_name"): f["name"] = u["current_name"]
        if u.get("phone"): f["phone"] = u["phone"]
        if u.get("address"): f["address"] = u["address"]
        f["website"] = u["website"]
        f["website_status"] = "verified"
        f["website_verified_at"] = "2026-09-29"
        f["website_verification_source"] = u["evidence"]
        changed.append({"id":f["id"],"name":f["name"],"before":before,
                        "website":f["website"],"evidence":u["evidence"]})

    audit = {
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "batch":11,
        "target_count":len(UPDATES),
        "verified_count":len(changed),
        "error_count":len(errors),
        "verified":changed,
        "errors":errors
    }
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    if errors or len(changed) != len(UPDATES):
        raise RuntimeError(
            f"Batch 11 stopped safely: {len(changed)}/{len(UPDATES)} matched; "
            f"errors={len(errors)}. Master not written."
        )

    remaining = [
        {
            "id":f.get("id"),"name":f.get("name"),"category":f.get("category"),
            "ward":f.get("ward"),"postal":f.get("postal"),"address":f.get("address"),
            "phone":f.get("phone"),"website":f.get("website"),
            "website_status":f.get("website_status")
        }
        for f in fs
        if f.get("public_private") == "私立" and f.get("website_status") != "verified"
    ]
    remaining.sort(key=lambda x: (["北区","中区","東区","南区"].index(x["ward"]), x["name"]))
    rem = {
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "private_total":sum(1 for f in fs if f.get("public_private")=="私立"),
        "private_verified":sum(1 for f in fs if f.get("public_private")=="私立" and f.get("website_status")=="verified"),
        "remaining_count":len(remaining),
        "remaining":remaining
    }
    REMAINING.write_text(json.dumps(rem,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    MASTER.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rem,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[batch11] ERROR: {e}",file=sys.stderr)
        sys.exit(1)
