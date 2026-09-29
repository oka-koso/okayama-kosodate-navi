#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
targets=['index.html','hoikuen.html','moushikomi.html','score.html','support.html','contact.html']
changed=[]
for name in targets:
    p=ROOT/name
    if not p.exists():
        continue
    s=p.read_text(encoding='utf-8')
    if 'href="tochuu.html"' in s:
        continue
    candidates=[
        '<a href="moushikomi.html">入園申込</a>',
        '<a href="score.html">点数計算</a>',
    ]
    done=False
    for needle in candidates:
        if needle in s:
            addition=needle+'<a href="tochuu.html">途中入園</a>'
            s=s.replace(needle,addition,1)
            p.write_text(s,encoding='utf-8')
            changed.append(name); done=True; break
    if not done:
        print(f'[skip-nav] {name}: insertion point not found')
print('patched:', ', '.join(changed) if changed else 'already installed / no matching pages')
