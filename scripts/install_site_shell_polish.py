from pathlib import Path
import re
changed=[]
for p in sorted(Path(".").rglob("*.html")):
    if any(x in {".git","node_modules"} for x in p.parts) or p.name=="404.html": continue
    s=p.read_text(encoding="utf-8"); old=s
    pre="../"*(len(p.parts)-1)
    if "css/site-shell.css" not in s or "js/site-shell.js" not in s:
        print("SKIP (共通shell未導入):",p); continue
    if "css/site-shell-polish.css" not in s:
        s=re.sub(r"</head\s*>",f'<link rel="stylesheet" href="{pre}css/site-shell-polish.css">\n</head>',s,count=1,flags=re.I)
    if "js/site-shell-polish.js" not in s:
        s=re.sub(r"</body\s*>",f'<script defer src="{pre}js/site-shell-polish.js"></script>\n</body>',s,count=1,flags=re.I)
    if s!=old:
        p.write_text(s,encoding="utf-8");changed.append(str(p))
if not changed:
    raise SystemExit("変更対象がありません（既に導入済みの場合を除く）")
print("UPDATED:",len(changed))
for x in changed: print(" +",x)
