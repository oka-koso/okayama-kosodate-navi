#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/"data"/"facility_master.json"
AUDIT=ROOT/"data"/"private_website_audit_batch12.json"
REMAINING=ROOT/"data"/"private_website_remaining_after_batch12.json"
UPDATES=[
  {
    "id": "oky-c9203aa946fd",
    "expected_name": "加茂こども園",
    "website": "https://ryouwakai.jp/",
    "evidence": "https://ryouwakai.jp/"
  },
  {
    "id": "oky-b4ce2044c16e",
    "expected_name": "とみやまこども園",
    "website": "https://tomiyama.ed.jp/",
    "evidence": "https://tomiyama.ed.jp/"
  },
  {
    "id": "oky-c8aebac17abf",
    "expected_name": "竜之口こども園",
    "website": "https://tatsunokuchi.ed.jp/",
    "evidence": "https://tatsunokuchi.ed.jp/"
  },
  {
    "id": "oky-97fb1f945ade",
    "expected_name": "益野保育園",
    "website": "https://masunohoikuen.jp/",
    "evidence": "https://masunohoikuen.jp/"
  },
  {
    "id": "oky-8372800aaa77",
    "expected_name": "かわい保育園",
    "website": "https://www.sumatoku.jp/kawai/",
    "evidence": "https://www.sumatoku.jp/kawai/"
  },
  {
    "id": "oky-deb6fc9b9832",
    "expected_name": "ほかほか保育園",
    "current_name": "ぽかぽか保育園",
    "website": "https://dainimakotokai.com/publics/index/38/",
    "evidence": "https://dainimakotokai.com/publics/index/38/"
  }
]

def main():
    data=json.loads(MASTER.read_text(encoding="utf-8"))
    fs=data.get("facilities",[])
    by_id={f.get("id"):f for f in fs}
    changed=[]; errors=[]

    for u in UPDATES:
        f=by_id.get(u["id"])
        if not f:
            errors.append({**u,"reason":"id-not-found"}); continue
        if f.get("public_private")!="私立":
            errors.append({**u,"reason":f"public_private={f.get('public_private')}"}); continue
        allowed={u["expected_name"]}
        if u.get("current_name"): allowed.add(u["current_name"])
        if f.get("name") not in allowed:
            errors.append({**u,"reason":"name-mismatch","actual_name":f.get("name")}); continue

        before={"name":f.get("name"),"website":f.get("website"),
                "website_status":f.get("website_status")}
        if u.get("current_name"): f["name"]=u["current_name"]
        f["website"]=u["website"]
        f["website_status"]="verified"
        f["website_verified_at"]="2026-09-29"
        f["website_verification_source"]=u["evidence"]
        changed.append({"id":f["id"],"name":f["name"],"before":before,
                        "website":f["website"],"evidence":u["evidence"]})

    audit={
      "generated_at":datetime.now().isoformat(timespec="seconds"),
      "batch":12,"target_count":len(UPDATES),
      "verified_count":len(changed),"error_count":len(errors),
      "verified":changed,"errors":errors
    }
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    if errors or len(changed)!=len(UPDATES):
        raise RuntimeError(
          f"Batch 12 stopped safely: {len(changed)}/{len(UPDATES)}; "
          f"errors={len(errors)}. Master not written."
        )

    remaining=[
      {"id":f.get("id"),"name":f.get("name"),"category":f.get("category"),
        "ward":f.get("ward"),"postal":f.get("postal"),"address":f.get("address"),
        "phone":f.get("phone"),"website":f.get("website"),
        "website_status":f.get("website_status")}
      for f in fs
      if f.get("public_private")=="私立" and f.get("website_status")!="verified"
    ]
    remaining.sort(key=lambda x:(["北区","中区","東区","南区"].index(x["ward"]),x["name"]))
    report={
      "generated_at":datetime.now().isoformat(timespec="seconds"),
      "private_total":sum(1 for f in fs if f.get("public_private")=="私立"),
      "private_verified":sum(1 for f in fs if f.get("public_private")=="私立" and f.get("website_status")=="verified"),
      "remaining_count":len(remaining),"remaining":remaining
    }
    REMAINING.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    MASTER.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"[batch12] ERROR: {e}",file=sys.stderr); sys.exit(1)
