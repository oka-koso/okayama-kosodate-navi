from pathlib import Path
import re
changed=[]
for p in sorted(Path(".").rglob("*.html")):
 if any(x in {".git","node_modules"} for x in p.parts) or p.name=="404.html": continue
 s=p.read_text(encoding="utf-8"); old=s
 hs=list(re.finditer(r"<header\\b[^>]*>.*?</header>",s,re.S|re.I)); fs=list(re.finditer(r"<footer\\b[^>]*>.*?</footer>",s,re.S|re.I))
 if len(hs)!=1 or len(fs)!=1:
  print("SKIP",p,"header",len(hs),"footer",len(fs)); continue
 h=hs[0]; s=s[:h.start()]+"<div data-site-header></div>"+s[h.end():]
 fs=list(re.finditer(r"<footer\\b[^>]*>.*?</footer>",s,re.S|re.I)); f=fs[0]; s=s[:f.start()]+"<div data-site-footer></div>"+s[f.end():]
 pre="../"*(len(p.parts)-1)
 if "css/site-shell.css" not in s:s=s.replace("</head>",f'<link rel="stylesheet" href="{pre}css/site-shell.css">\\n</head>',1)
 if "js/site-shell.js" not in s:s=s.replace("</body>",f'<script defer src="{pre}js/site-shell.js"></script>\\n</body>',1)
 if s!=old:p.write_text(s,encoding="utf-8");changed.append(str(p))
if not changed: raise SystemExit("変更対象HTMLがありません")
print("UPDATED",*changed,sep="\\n - ")
