#!/usr/bin/env python3
from pathlib import Path
import shutil, re

for src, dst in [
    (Path("patch_files/css/home-bibouroku-feature.css"), Path("css/home-bibouroku-feature.css")),
    (Path("patch_files/js/home-bibouroku-feature.js"), Path("js/home-bibouroku-feature.js")),
]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print("COPIED:", dst)

p = Path("index.html")
if not p.exists():
    raise SystemExit("ERROR: index.html not found")
s = p.read_text(encoding="utf-8")

css_tag = '<link rel="stylesheet" href="css/home-bibouroku-feature.css">'
js_tag = '<script src="js/home-bibouroku-feature.js" defer></script>'

if "css/home-bibouroku-feature.css" not in s:
    if "</head>" not in s:
        raise SystemExit("ERROR: </head> not found")
    s = s.replace("</head>", f"  {css_tag}\\n</head>", 1)

if "js/home-bibouroku-feature.js" not in s:
    if "</body>" not in s:
        raise SystemExit("ERROR: </body> not found")
    s = s.replace("</body>", f"  {js_tag}\\n</body>", 1)

p.write_text(s, encoding="utf-8")
print("UPDATED:", p)
print("DONE")
