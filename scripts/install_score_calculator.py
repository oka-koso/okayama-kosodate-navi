#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
targets = ["index.html", "hoikuen.html", "moushikomi.html"]
needle = '<a href="moushikomi.html">入園申込</a>'
addition = needle + '<a href="score.html">点数計算</a>'

changed = []
for name in targets:
    p = ROOT / name
    if not p.exists():
        print(f"[skip] {name}: not found")
        continue
    s = p.read_text(encoding="utf-8")
    if 'href="score.html"' not in s:
        if needle not in s:
            raise RuntimeError(f"{name}: navigation insertion point not found")
        s = s.replace(needle, addition, 1)
        p.write_text(s, encoding="utf-8")
        changed.append(name)

p = ROOT / "moushikomi.html"
if p.exists():
    s = p.read_text(encoding="utf-8")
    marker = '<h3>点数（利用調整基準）は？</h3>'
    if marker in s and 'score-tool-link' not in s:
        start = s.index(marker)
        para_start = s.find('<p>', start)
        para_end = s.find('</p>', para_start)
        if para_start >= 0 and para_end >= 0:
            replacement = (
              '<p>岡山市の令和8年度基準に沿って、基礎点数・調整点数を試算できます。</p>'
              '<p id="score-tool-link"><a class="btn" href="score.html">🧮 利用調整点数を計算する</a></p>'
            )
            s = s[:para_start] + replacement + s[para_end+4:]
            p.write_text(s, encoding="utf-8")
            if "moushikomi.html" not in changed:
                changed.append("moushikomi.html")

print("patched:", ", ".join(changed) if changed else "already installed")
