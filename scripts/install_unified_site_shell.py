from pathlib import Path
import re

changed=[]; already=[]; errors=[]
for p in sorted(Path(".").rglob("*.html")):
    if any(x in {".git","node_modules"} for x in p.parts) or p.name=="404.html": continue
    s=p.read_text(encoding="utf-8"); old=s
    pre="../"*(len(p.parts)-1)

    if 'data-site-header' not in s:
        hs=list(re.finditer(r"<header\b[^>]*>.*?</header>",s,re.S|re.I))
        if len(hs)!=1:
            errors.append((str(p),f"header={len(hs)}")); continue
        h=hs[0]; s=s[:h.start()]+"<div data-site-header></div>"+s[h.end():]

    if 'data-site-footer' not in s:
        fs=list(re.finditer(r"<footer\b[^>]*>.*?</footer>",s,re.S|re.I))
        if len(fs)==1:
            f=fs[0]; s=s[:f.start()]+"<div data-site-footer></div>"+s[f.end():]
        elif len(fs)==0:
            # Legal/about pages currently have no footer: safely add the host before </body>.
            if re.search(r"</body\s*>",s,re.I):
                s=re.sub(r"</body\s*>","<div data-site-footer></div>\n</body>",s,count=1,flags=re.I)
            else:
                errors.append((str(p),"footer=0 and </body> missing")); continue
        else:
            errors.append((str(p),f"footer={len(fs)}")); continue

    if "css/site-shell.css" not in s:
        if "</head>" not in s.lower():
            errors.append((str(p),"</head> missing")); continue
        s=re.sub(r"</head\s*>",f'<link rel="stylesheet" href="{pre}css/site-shell.css">\n</head>',s,count=1,flags=re.I)
    if "js/site-shell.js" not in s:
        if not re.search(r"</body\s*>",s,re.I):
            errors.append((str(p),"</body> missing")); continue
        s=re.sub(r"</body\s*>",f'<script defer src="{pre}js/site-shell.js"></script>\n</body>',s,count=1,flags=re.I)

    if s!=old:
        p.write_text(s,encoding="utf-8"); changed.append(str(p))
    else: already.append(str(p))

print("UPDATED:",len(changed))
for x in changed: print(" +",x)
print("ALREADY:",len(already))
for x in already: print(" =",x)
if errors:
    print("ERRORS:",len(errors))
    for x,e in errors: print(" !",x,e)
    raise SystemExit("想定外のHTML構造があります。commit前に停止します。")
if not changed and not already: raise SystemExit("対象HTMLがありません。")
