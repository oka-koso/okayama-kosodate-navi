#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
changed = []

# 1) Existing page navigation: add the midyear guide without changing the established header design.
targets = ['index.html','hoikuen.html','moushikomi.html','score.html','support.html','contact.html','about.html']
for name in targets:
    p = ROOT / name
    if not p.exists():
        continue
    s = p.read_text(encoding='utf-8')
    before = s
    if 'href="tochuu.html"' not in s:
        needle = '<a href="moushikomi.html">入園申込</a>'
        if needle in s:
            s = s.replace(needle, needle + '<a href="tochuu.html">途中入園</a>', 1)
    if s != before:
        p.write_text(s, encoding='utf-8')
        changed.append(name)

# 2) Homepage: put a direct link in "いま確認したい情報".
p = ROOT / 'index.html'
if p.exists():
    s = p.read_text(encoding='utf-8')
    before = s
    marker = 'data-midyear-home-link="1"'
    if marker not in s:
        row = ('<a class="status-row" data-midyear-home-link="1" href="tochuu.html" '
               'style="color:inherit;text-decoration:none">'
               '<span class="dot"></span><div><strong>途中入園（4月以外）</strong>'
               '<div class="small">申込締切・最新の受入見込みを確認 →</div></div></a>')
        # Prefer inserting before the existing availability row so admission info stays grouped.
        availability_row = re.search(r'<div class="status-row"><span class="dot"></span><div><strong>最新の受入見込み</strong>', s)
        if availability_row:
            s = s[:availability_row.start()] + row + s[availability_row.start():]
        else:
            # Fallback: first row inside the hero-card.
            hero = re.search(r'(<div class="hero-card"><h2>[^<]*いま確認したい情報[^<]*</h2>)', s)
            if hero:
                s = s[:hero.end()] + row + s[hero.end():]
            else:
                print('[warn] index.html: "いま確認したい情報" insertion point not found')
    if s != before:
        p.write_text(s, encoding='utf-8')
        if 'index.html' not in changed:
            changed.append('index.html')

print('patched:', ', '.join(changed) if changed else 'already installed / no matching pages')
