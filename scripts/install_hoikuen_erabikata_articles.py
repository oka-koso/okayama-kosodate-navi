#!/usr/bin/env python3
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT=Path(".")
data_path=ROOT/"data/bibouroku.json"
if not data_path.exists():
    raise SystemExit("ERROR: data/bibouroku.json not found")

data=json.loads(data_path.read_text(encoding="utf-8"))
if not isinstance(data,list):
    raise SystemExit("ERROR: bibouroku.json must be an array")

new_items=[
  {
    "title":"保育園を選ぶポイント Part1",
    "description":"園見学でまず見たい5つのポイント。子どもの様子、先生の関わり方、保育室の環境など、パンフレットだけでは分からない部分をまとめました。",
    "url":"articles/hoikuen-erabikata-part1.html",
    "category":"保育園",
    "published":"2026-09-29",
    "updated":"2026-09-29"
  },
  {
    "title":"保育園を選ぶポイント Part2",
    "description":"保育方針、給食、安全面、園とのコミュニケーション、通いやすさ。入園後の毎日まで考えて確認したいポイントをまとめました。",
    "url":"articles/hoikuen-erabikata-part2.html",
    "category":"保育園",
    "published":"2026-09-29",
    "updated":"2026-09-29"
  }
]
by_url={x.get("url"):x for x in data if isinstance(x,dict)}
for item in new_items:
    by_url[item["url"]]=item
# Preserve existing order, append/update these two at the end.
seen=set()
out=[]
for x in data:
    if not isinstance(x,dict) or not x.get("url"): continue
    u=x["url"]
    if u in seen: continue
    out.append(by_url[u]); seen.add(u)
for item in new_items:
    if item["url"] not in seen:
        out.append(item); seen.add(item["url"])
data_path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("OK: bibouroku.json",len(out),"articles")

# Update sitemap without overwriting existing URLs.
sm=ROOT/"sitemap.xml"
if sm.exists():
    txt=sm.read_text(encoding="utf-8")
    base="https://oka-koso.github.io/okayama-kosodate-navi/"
    additions=[]
    for item in new_items:
        loc=base+item["url"]
        if loc not in txt:
            additions.append(f"""  <url>
    <loc>{loc}</loc>
    <lastmod>2026-09-29</lastmod>
  </url>
""")
    if additions:
        if "</urlset>" not in txt:
            raise SystemExit("ERROR: sitemap.xml has no </urlset>")
        txt=txt.replace("</urlset>","".join(additions)+"</urlset>",1)
        sm.write_text(txt,encoding="utf-8")
        print("OK: sitemap.xml added",len(additions),"URLs")
    else:
        print("SKIP: sitemap URLs already exist")
else:
    print("WARN: sitemap.xml not found")

for f in ["articles/hoikuen-erabikata-part1.html","articles/hoikuen-erabikata-part2.html"]:
    if not (ROOT/f).exists():
        raise SystemExit("ERROR: missing "+f)
print("DONE")
