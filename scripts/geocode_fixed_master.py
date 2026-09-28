#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
UA = "OkayamaKosodateNavi/geocoder-fixed-master-1.0"

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    changed = 0

    for f in data.get("facilities", []):
        if f.get("lat") is not None and f.get("lon") is not None:
            continue
        if not f.get("address"):
            continue

        params = {
            "q": f["address"],
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "jp",
        }

        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": UA},
            timeout=20,
        )
        r.raise_for_status()
        arr = r.json()

        if arr:
            f["lat"] = float(arr[0]["lat"])
            f["lon"] = float(arr[0]["lon"])
            changed += 1
            print(f"[geocode] {f['name']} -> {f['lat']}, {f['lon']}")
        else:
            print(f"[geocode] NOT FOUND: {f['name']} / {f['address']}")

        # Nominatim usage policy: low rate
        time.sleep(1.05)

    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[geocode] changed={changed}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[geocode] ERROR:", e, file=sys.stderr)
        sys.exit(1)
