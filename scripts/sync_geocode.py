#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
MERGED = ROOT / "data" / "facilities.json"

m = json.loads(MASTER.read_text(encoding="utf-8"))
d = json.loads(MERGED.read_text(encoding="utf-8"))

coords = {
    f["id"]: (f.get("lat"), f.get("lon"))
    for f in d.get("facilities", [])
    if f.get("id")
}

changed = 0
for f in m.get("facilities", []):
    latlon = coords.get(f["id"])
    if not latlon:
        continue
    lat, lon = latlon
    if lat is None or lon is None:
        continue
    if f.get("lat") != lat or f.get("lon") != lon:
        f["lat"], f["lon"] = lat, lon
        changed += 1

if changed:
    MASTER.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("[sync_geocode]", changed)
