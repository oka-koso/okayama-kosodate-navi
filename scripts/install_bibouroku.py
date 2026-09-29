from pathlib import Path
import re
R=Path(".")
idx=R/"index.html"
if idx.exists():
 s=idx.read_text(encoding="utf-8")
 if "css/bibouroku.css" not in s:s=s.replace("</head>",'<link rel="stylesheet" href="css/bibouroku.css">\n</head>',1)
 if "js/bibouroku.js" not in s:s=s.replace("</body>",'<script src="js/bibouroku.js" defer></script>\n</body>',1)
 if 'id="home-bibouroku"' not in s:
  b='<section class="home-bibouroku" id="home-bibouroku"><div class="home-bibouroku__head"><div><h2>子育て備忘録</h2><p>知っておくとちょっと助かる、子育てのあれこれ。</p></div><a class="home-bibouroku__all" href="bibouroku.html">記事をもっと見る →</a></div><div class="bibouroku-list" data-bibouroku-list data-limit="3"></div></section>\n'
  s=s.replace("</main>",b+"</main>",1) if "</main>" in s else s.replace("</body>",b+"</body>",1)
 idx.write_text(s,encoding="utf-8");print("OK index")
shell=R/"js/site-shell.js"
if shell.exists():
 s=shell.read_text(encoding="utf-8")
 if "bibouroku.html" not in s:
  m=re.search(r'(<a\\b[^>]*href=["\\\'][^"\\\']*about\\.html["\\\'][^>]*>\\s*このサイトについて\\s*</a>)',s)
  if m:
   ins='<a href="bibouroku.html">子育て備忘録</a>'
   s=s[:m.start()]+ins+m.group(1)+s[m.end():];shell.write_text(s,encoding="utf-8");print("OK nav")
  else:print("WARN nav pattern not found")
sm=R/"sitemap.xml"
if sm.exists():
 s=sm.read_text(encoding="utf-8")
 for u,p in [("https://oka-koso.github.io/okayama-kosodate-navi/bibouroku.html","0.8"),("https://oka-koso.github.io/okayama-kosodate-navi/articles/hoikuen-sagashi-hajimekata.html","0.7")]:
  if u not in s:s=s.replace("</urlset>",f'  <url>\n    <loc>{u}</loc>\n    <priority>{p}</priority>\n  </url>\n</urlset>')
 sm.write_text(s,encoding="utf-8");print("OK sitemap")
print("DONE")
