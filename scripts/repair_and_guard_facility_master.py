#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, shutil

ROOT=Path(".")
MASTER=ROOT/"data/facility_master.json"
CANON=ROOT/"data/facility_master_206_canonical.json"
DUAL=ROOT/"scripts/update_availability_dual.py"

def count_text(raw):
    try:
        return len(json.loads(raw).get("facilities",[]))
    except Exception:
        return -1

def count_file(p):
    try:
        return count_text(p.read_text(encoding="utf-8"))
    except Exception:
        return -1

current=count_file(MASTER)
print("current facility count:",current)

if current==206:
    verified=MASTER.read_text(encoding="utf-8")
else:
    commits=subprocess.check_output(
        ["git","log","--format=%H","--","data/facility_master.json"],text=True
    ).splitlines()
    verified=None
    source_commit=None
    for sha in commits:
        try:
            raw=subprocess.check_output(
                ["git","show",sha+":data/facility_master.json"],
                text=True,stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            continue
        if count_text(raw)==206:
            verified=raw
            source_commit=sha
            break
    if verified is None:
        raise SystemExit("ERROR: Git history contains no verified 206-facility master.")
    MASTER.write_text(verified,encoding="utf-8")
    print("RESTORED from:",source_commit)

if count_file(MASTER)!=206:
    raise SystemExit("ERROR: repair did not produce 206 facilities.")
shutil.copy2(MASTER,CANON)
print("CANONICAL:",CANON)

s=DUAL.read_text(encoding="utf-8")
marker="# facility-master-206-runtime-guard-v2"
if marker not in s:
    anchor='UA = "OkayamaKosodateNavi/availability-dual-v1"\n'
    guard = """
# facility-master-206-runtime-guard-v2
FACILITY_MASTER = ROOT / "data" / "facility_master.json"
FACILITY_MASTER_CANONICAL = ROOT / "data" / "facility_master_206_canonical.json"

def ensure_verified_facility_master():
    def count(path):
        try:
            obj=json.loads(path.read_text(encoding="utf-8"))
            return len(obj.get("facilities",[]))
        except Exception:
            return -1
    n=count(FACILITY_MASTER)
    if n==206:
        return
    cn=count(FACILITY_MASTER_CANONICAL)
    if cn!=206:
        raise RuntimeError(
            f"固定施設マスタ異常: current={n}, canonical={cn}; 安全のため停止"
        )
    shutil.copyfile(FACILITY_MASTER_CANONICAL,FACILITY_MASTER)
    print(
        f"[availability-dual] WARN: facility master {n} -> restored verified 206 snapshot"
    )

"""
    if anchor not in s:
        raise SystemExit("ERROR: expected UA line not found.")
    s=s.replace(anchor,anchor+guard,1)
    old="def main():\n    if not LEGACY_PATH.exists():"
    new="def main():\n    ensure_verified_facility_master()\n    if not LEGACY_PATH.exists():"
    if old not in s:
        raise SystemExit("ERROR: main insertion point not found.")
    s=s.replace(old,new,1)
    DUAL.write_text(s,encoding="utf-8")
    print("PATCHED:",DUAL)

print("SUCCESS:",count_file(MASTER))
