#!/usr/bin/env python3
from pathlib import Path

MEASUREMENT_ID = "G-961RLY7WVE"
MARKER = "Google Analytics 4 - Okayama Kosodate Navi"

snippet = '''<!-- Google Analytics 4 - Okayama Kosodate Navi -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-961RLY7WVE"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-961RLY7WVE');
</script>'''

changed = 0
for p in sorted(Path(".").rglob("*.html")):
    if any(part in {".git", "node_modules", "vendor"} for part in p.parts):
        continue
    s = p.read_text(encoding="utf-8")
    if MEASUREMENT_ID in s or MARKER in s:
        print("SKIP:", p)
        continue
    if "</head>" not in s:
        print("NO HEAD:", p)
        continue
    p.write_text(s.replace("</head>", snippet + "\n</head>", 1), encoding="utf-8")
    changed += 1
    print("UPDATED:", p)

print(f"DONE: {changed} HTML file(s) updated with {MEASUREMENT_ID}")
