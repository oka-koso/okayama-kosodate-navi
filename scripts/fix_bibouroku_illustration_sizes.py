#!/usr/bin/env python3
from pathlib import Path

p = Path("css/bibouroku.css")
if not p.exists():
    raise SystemExit("ERROR: css/bibouroku.css not found")

s = p.read_text(encoding="utf-8")
marker = "/* bibouroku illustration compact fix v1 */"
block = """
/* bibouroku illustration compact fix v1 */
.bibouroku-hero__illust{
  width:110px !important;
  right:22px !important;
  bottom:4px !important;
}
.bibouroku-card__thumb{
  width:82px !important;
  height:72px !important;
  object-fit:contain !important;
  object-position:center !important;
  margin:0 auto 8px !important;
}
.article-spot-illust{
  width:135px !important;
  max-width:28vw !important;
  margin:14px auto 8px !important;
}
@media(max-width:760px){
  .bibouroku-hero{padding-right:82px !important}
  .bibouroku-hero__illust{
    width:72px !important;
    right:8px !important;
    bottom:4px !important;
  }
  .bibouroku-card__thumb{
    width:68px !important;
    height:60px !important;
    margin:0 auto 6px !important;
  }
  .article-spot-illust{
    width:105px !important;
    max-width:32vw !important;
    margin:10px auto 6px !important;
  }
}
"""
if marker not in s:
    p.write_text(s.rstrip()+"\n"+block+"\n", encoding="utf-8")
    print("UPDATED:", p)
else:
    print("ALREADY APPLIED")
