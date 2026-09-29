from pathlib import Path
import re

CODE = """<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2321879700607801"
     crossorigin="anonymous"></script>"""
CLIENT = "ca-pub-2321879700607801"
changed=[]; already=[]; errors=[]

for p in sorted(Path(".").rglob("*.html")):
    if any(x in {".git","node_modules"} for x in p.parts) or p.name=="404.html":
        continue
    s=p.read_text(encoding="utf-8")
    # If exact publisher code already exists, do not duplicate it.
    if CLIENT in s:
        already.append(str(p)); continue
    if not re.search(r"</head\s*>",s,re.I):
        errors.append(str(p)); continue
    s=re.sub(r"</head\s*>",CODE+"\n</head>",s,count=1,flags=re.I)
    p.write_text(s,encoding="utf-8")
    changed.append(str(p))

print("UPDATED:",len(changed))
for x in changed: print(" +",x)
print("ALREADY:",len(already))
for x in already: print(" =",x)
if errors:
    print("ERROR: </head> がないHTML:", *errors, sep="\n ! ")
    raise SystemExit("安全のため停止しました。")
if not changed and not already:
    raise SystemExit("対象HTMLがありません。")
