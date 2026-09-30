#!/usr/bin/env python3
from pathlib import Path
import json, shutil

ROOT = Path(".")
master = ROOT/"data/facility_master.json"
canonical = ROOT/"data/facility_master_206_canonical.json"
dual = ROOT/"scripts/update_availability_dual.py"

if not master.exists() or not dual.exists():
    raise SystemExit("ERROR: required files not found")

data=json.loads(master.read_text(encoding="utf-8"))
n=len(data.get("facilities",[]))
if n != 206:
    raise SystemExit(f"ERROR: current facility_master.json is {n}, expected 206")

shutil.copy2(master, canonical)
print("CREATED:", canonical)

s=dual.read_text(encoding="utf-8")
marker="# facility-master-206-guard-v1"
if marker not in s:
    anchor='UA = "OkayamaKosodateNavi/availability-dual-v1"\n'
    if anchor not in s:
        raise SystemExit("ERROR: UA anchor not found")

    guard='''\n# facility-master-206-guard-v1
FACILITY_MASTER = ROOT / "data" / "facility_master.json"
FACILITY_MASTER_CANONICAL = ROOT / "data" / "facility_master_206_canonical.json"

def ensure_facility_master_206():
    def count(path):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            return len(obj.get("facilities", []))
        except Exception:
            return -1

    current_count = count(FACILITY_MASTER)
    if current_count == 206:
        return

    canonical_count = count(FACILITY_MASTER_CANONICAL)
    if canonical_count != 206:
        raise RuntimeError(
            f"facility master invalid: current={current_count}, canonical={canonical_count}"
        )

    shutil.copyfile(FACILITY_MASTER_CANONICAL, FACILITY_MASTER)
    print(
        f"[availability-dual] WARN: facility_master.json was {current_count}; "
        "restored verified 206-facility canonical snapshot."
    )
\n'''
    s=s.replace(anchor, anchor+guard, 1)

    old="def main():\n    if not LEGACY_PATH.exists():"
    new="def main():\n    ensure_facility_master_206()\n    if not LEGACY_PATH.exists():"
    if old not in s:
        raise SystemExit("ERROR: main anchor not found")
    s=s.replace(old,new,1)
    dual.write_text(s,encoding="utf-8")
    print("UPDATED:",dual)
else:
    print("ALREADY PATCHED:",dual)

print("DONE")
