#!/usr/bin/env python3
from pathlib import Path
import shutil, re

ASSET_SRC = Path("patch_assets/bibouroku")
ASSET_DST = Path("assets/bibouroku")
ASSET_DST.mkdir(parents=True, exist_ok=True)
for p in ASSET_SRC.glob("*.png"):
    shutil.copy2(p, ASSET_DST / p.name)
    print("ASSET:", ASSET_DST / p.name)

css = Path("css/bibouroku.css")
if not css.exists():
    raise SystemExit("ERROR: css/bibouroku.css not found")
s = css.read_text(encoding="utf-8")
marker = "/* bibouroku illustrations v1 */"
block = """
/* bibouroku illustrations v1 */
.bibouroku-hero{position:relative;overflow:hidden}
.bibouroku-hero__illust{position:absolute;right:28px;bottom:0;width:min(230px,26vw);height:auto;pointer-events:none}
.bibouroku-card{position:relative;overflow:hidden}
.bibouroku-card__thumb{display:block;width:100%;height:150px;object-fit:contain;object-position:center bottom;margin:-8px 0 10px}
.article-spot-illust{display:block;width:min(300px,72vw);height:auto;margin:22px auto 8px}
@media(max-width:760px){
  .bibouroku-hero{padding-right:118px}
  .bibouroku-hero__illust{right:8px;width:112px}
  .bibouroku-card__thumb{height:135px}
  .article-spot-illust{width:min(245px,78vw);margin-top:18px}
}
@media(max-width:430px){
  .bibouroku-hero{padding-right:92px}
  .bibouroku-hero__illust{width:90px}
}
"""
if marker not in s:
    css.write_text(s.rstrip()+"\n"+block+"\n", encoding="utf-8")
    print("UPDATED:", css)

js = Path("js/bibouroku.js")
if not js.exists():
    raise SystemExit("ERROR: js/bibouroku.js not found")
j = js.read_text(encoding="utf-8")
if "bibouroku-card__thumb" not in j:
    old = """function card(a){return `<a class="bibouroku-card" href="${base}${esc(a.url)}"><div class="bibouroku-card__meta">"""
    new = """function imageFor(a){const u=String(a.url||'');if(u.includes('hoikuen-sagashi-hajimekata'))return 'assets/bibouroku/hoikuen-start-map.png';if(u.includes('hoikuen-erabikata-part1'))return 'assets/bibouroku/hoikuen-erabikata-part1.png';if(u.includes('hoikuen-erabikata-part2'))return 'assets/bibouroku/hoikuen-erabikata-part2.png';return 'assets/bibouroku/bibouroku-reading.png';}function card(a){const img=imageFor(a);return `<a class="bibouroku-card" href="${base}${esc(a.url)}"><img class="bibouroku-card__thumb" src="${base}${img}" alt="" loading="lazy" decoding="async"><div class="bibouroku-card__meta">"""
    if old not in j:
        raise SystemExit("ERROR: card renderer not found in js/bibouroku.js")
    j = j.replace(old, new, 1)
    js.write_text(j, encoding="utf-8")
    print("UPDATED:", js)

def decorate(path, image, hero=False):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"ERROR: {p} not found")
    x = p.read_text(encoding="utf-8")
    if hero:
        if "bibouroku-hero__illust" not in x:
            needle = '</section><section class="bibouroku-wrap">'
            repl = f'<img class="bibouroku-hero__illust" src="assets/bibouroku/{image}" alt="" aria-hidden="true"></section><section class="bibouroku-wrap">'
            if needle not in x:
                raise SystemExit(f"ERROR: hero insertion point not found in {p}")
            x = x.replace(needle, repl, 1)
    else:
        if "article-spot-illust" not in x:
            pat = r'(<p class="article-lead">.*?</p>)'
            if not re.search(pat, x, flags=re.S):
                raise SystemExit(f"ERROR: article lead not found in {p}")
            repl = r'\1' + f'<img class="article-spot-illust" src="../assets/bibouroku/{image}" alt="" aria-hidden="true" loading="eager" decoding="async">'
            x = re.sub(pat, repl, x, count=1, flags=re.S)
    p.write_text(x, encoding="utf-8")
    print("UPDATED:", p)

decorate("bibouroku.html", "bibouroku-reading.png", True)
decorate("articles/hoikuen-sagashi-hajimekata.html", "hoikuen-start-map.png")
decorate("articles/hoikuen-erabikata-part1.html", "hoikuen-erabikata-part1.png")
decorate("articles/hoikuen-erabikata-part2.html", "hoikuen-erabikata-part2.png")
print("DONE")
