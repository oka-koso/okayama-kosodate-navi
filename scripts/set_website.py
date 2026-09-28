#!/usr/bin/env python3
"""
facility_master.json の website を手作業で登録するときの簡易ツール。

例:
python scripts/set_website.py "弓之町保育園" "https://example.jp/"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "facility_master.json"

if len(sys.argv) != 3:
    raise SystemExit('usage: python scripts/set_website.py "園名" "https://..."')

name, url = sys.argv[1], sys.argv[2]
d = json.loads(P.read_text(encoding="utf-8"))

for f in d.get("facilities", []):
    if f.get("name") == name:
        f["website"] = url
        f["review_status"] = "website_verified"
        P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("updated", name)
        break
else:
    raise SystemExit("facility not found: " + name)
