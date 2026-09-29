#!/usr/bin/env python3
from pathlib import Path
import re

URL = "https://www.mhlw.go.jp/web/t_doc?dataId=00ta9723&dataType=1&pageNo=1"
targets = [
    Path("articles/hoikuen-erabikata-part1.html"),
    Path("articles/hoikuen-erabikata-part2.html"),
]

replacement = f"""<h2>参考資料</h2>
<p>園選びのポイントを整理するにあたり、厚生労働省が公開している「よい保育施設の選び方 十か条」を参考にしています。この記事では、その内容をもとに、園見学や毎日の通園を考える際に確認しやすい形へ独自に整理しています。</p>
<p><a href="{URL}" rel="noopener noreferrer" target="_blank">厚生労働省「よい保育施設の選び方 十か条」</a></p>"""

for p in targets:
    if not p.exists():
        raise SystemExit(f"ERROR: {p} not found")

    s = p.read_text(encoding="utf-8")
    old = s

    # Replace the whole reference section up to the article content wrapper close.
    pat = r'<h2>参考にした資料</h2>\s*<p>.*?</p>\s*<p><a[^>]+>.*?</a></p>'
    s, n = re.subn(pat, replacement, s, count=1, flags=re.S)

    if n != 1:
        # Also support an already partially edited heading.
        pat2 = r'<h2>参考資料</h2>\s*<p>.*?(?:若草|wakakusa).*?</p>\s*<p><a[^>]+>.*?</a></p>'
        s, n = re.subn(pat2, replacement, s, count=1, flags=re.S)

    if n != 1:
        raise SystemExit(f"ERROR: reference block not found in {p}")

    if "wakakusa-kodomoen.com" in s or "大久保わかくさ" in s:
        raise SystemExit(f"ERROR: old secondary-source reference remains in {p}")
    if URL not in s:
        raise SystemExit(f"ERROR: MHLW URL missing in {p}")

    p.write_text(s, encoding="utf-8")
    print("UPDATED:", p)

print("DONE: reference sources changed to MHLW primary source")
