#!/usr/bin/env python3
import json,time,requests
from pathlib import Path
root=Path(__file__).resolve().parents[1]
main=root/"data/facility_master.json"
canonical=root/"data/facility_master_206_canonical.json"
obj=json.loads(main.read_text(encoding="utf-8"))
targets={"oky-r9-minomaki","oky-r9-sanyogakuen"}
for f in obj["facilities"]:
    if f["id"] not in targets or f.get("lat") is not None: continue
    address=f["address"]
    resp=requests.get("https://msearch.gsi.go.jp/address-search/AddressSearch",params={"q":address},headers={"User-Agent":"OkayamaKosodateNavi/2026"},timeout=25)
    resp.raise_for_status()
    candidates=resp.json()
    if not candidates: raise RuntimeError(f"Geocoding unavailable: {address}")
    lon,lat=candidates[0]["geometry"]["coordinates"]
    if not (34.45 < lat < 34.95 and 133.65 < lon < 134.25): raise RuntimeError("Coordinate outside Okayama")
    f["lat"],f["lon"]=lat,lon
    f["geocode_source"]="GSI"
    f["geocode_title"]=candidates[0].get("properties",{}).get("title","")
    print(f["name"],lat,lon)
    time.sleep(0.3)
if any(f.get("lat") is None for f in obj["facilities"] if f["id"] in targets):raise RuntimeError("Missing coordinates")
data=json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
main.write_text(data,encoding="utf-8")
canonical.write_text(data,encoding="utf-8")
