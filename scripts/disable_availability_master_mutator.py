#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MARKER = 'auto_added_from_availability_pdf_v5_2'

def main():
    offenders=[]
    for p in (ROOT/'scripts').glob('*.py'):
        if p.name in {Path(__file__).name, 'repair_facility_master.py'}: continue
        try: s=p.read_text(encoding='utf-8')
        except Exception: continue
        if MARKER in s:
            offenders.append(p)
    print('[master-guard] mutator scripts:', ', '.join(str(x.relative_to(ROOT)) for x in offenders) or 'none found')
    changed=[]
    for wf in (ROOT/'.github'/'workflows').glob('*.y*ml'):
        try: s=wf.read_text(encoding='utf-8')
        except Exception: continue
        if not any(str(p.relative_to(ROOT)) in s for p in offenders):
            continue
        # Do not delete the workflow. Remove only schedule blocks so it remains
        # manually runnable for future reviewed migrations.
        lines=s.splitlines()
        out=[]; i=0; removed=False
        while i < len(lines):
            line=lines[i]
            if re.match(r'^\s{2}schedule:\s*$', line):
                indent=len(line)-len(line.lstrip())
                i+=1; removed=True
                while i < len(lines):
                    nxt=lines[i]; nindent=len(nxt)-len(nxt.lstrip()) if nxt.strip() else 999
                    if nxt.strip() and nindent <= indent: break
                    i+=1
                continue
            out.append(line); i+=1
        if removed:
            wf.write_text('\n'.join(out)+'\n', encoding='utf-8')
            changed.append(str(wf.relative_to(ROOT)))
    print('[master-guard] disabled schedules:', ', '.join(changed) or 'none')

if __name__=='__main__': main()
