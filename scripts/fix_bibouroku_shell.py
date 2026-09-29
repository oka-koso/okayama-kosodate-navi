#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(".")
TARGETS=[ROOT/"bibouroku.html", ROOT/"articles/hoikuen-sagashi-hajimekata.html"]
ADSENSE_ID="ca-pub-2321879700607801"
ADSENSE="""<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2321879700607801"
     crossorigin="anonymous"></script>"""

def add_before(s, closing, tag):
    if tag in s:
        return s
    return re.sub(closing, tag+"\n"+re.search(closing,s,re.I).group(0), s, count=1, flags=re.I)

updated=[]
for p in TARGETS:
    if not p.exists():
        print("WARN missing:",p)
        continue
    s=p.read_text(encoding="utf-8")
    old=s
    pre="../"*(len(p.parts)-1)

    # Existing site base design
    if "css/style.css" not in s:
        s=re.sub(r"</head\s*>",f'<link rel="stylesheet" href="{pre}css/style.css">\n</head>',s,count=1,flags=re.I)
    if "css/site-shell.css" not in s:
        s=re.sub(r"</head\s*>",f'<link rel="stylesheet" href="{pre}css/site-shell.css">\n</head>',s,count=1,flags=re.I)
    if "css/site-shell-polish.css" not in s:
        s=re.sub(r"</head\s*>",f'<link rel="stylesheet" href="{pre}css/site-shell-polish.css">\n</head>',s,count=1,flags=re.I)

    # Existing common behavior + shell behavior
    if "js/common.js" not in s:
        s=re.sub(r"</body\s*>",f'<script defer src="{pre}js/common.js"></script>\n</body>',s,count=1,flags=re.I)
    if "js/site-shell.js" not in s:
        s=re.sub(r"</body\s*>",f'<script defer src="{pre}js/site-shell.js"></script>\n</body>',s,count=1,flags=re.I)
    if "js/site-shell-polish.js" not in s:
        s=re.sub(r"</body\s*>",f'<script defer src="{pre}js/site-shell-polish.js"></script>\n</body>',s,count=1,flags=re.I)

    # AdSense: these pages were created after the original site-wide installer.
    if ADSENSE_ID not in s:
        s=re.sub(r"</head\s*>",ADSENSE+"\n</head>",s,count=1,flags=re.I)

    if s!=old:
        p.write_text(s,encoding="utf-8")
        updated.append(str(p))
        print("FIXED:",p)
    else:
        print("SKIP already fixed:",p)

# Fix the shared navigation reliably.
shell=ROOT/"js/site-shell.js"
if shell.exists():
    s=shell.read_text(encoding="utf-8")
    old=s
    # Header: replace 点数計算 with 子育て備忘録.
    # score.html itself remains available from page CTAs and other internal links.
    # First remove a previously inserted duplicate Bibouroku nav item, if any.
    s=s.replace('["bibouroku.html","子育て備忘録"],','')
    s=s.replace(',["bibouroku.html","子育て備忘録"]','')
    if '["score.html","点数計算"]' in s:
        s=s.replace('["score.html","点数計算"]','["bibouroku.html","子育て備忘録"]',1)
    elif '["bibouroku.html","子育て備忘録"]' not in s:
        print("WARN: score nav insertion point not found")
    if s!=old:
        shell.write_text(s,encoding="utf-8")
        print("FIXED: js/site-shell.js nav")
else:
    raise SystemExit("js/site-shell.js not found")

print("UPDATED HTML:",len(updated))
print("DONE: bibouroku shell fix v1.1")
