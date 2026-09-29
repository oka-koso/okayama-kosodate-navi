from pathlib import Path
skip={"operator.html","privacy.html"}
for p in Path(".").glob("*.html"):
    if p.name in skip: continue
    s=p.read_text(encoding="utf-8"); old=s
    if 'href="privacy.html"' in s and 'href="operator.html"' not in s:
        s=s.replace('<a href="privacy.html"','<a href="operator.html">運営者情報</a><a href="privacy.html"',1)
    elif "</footer>" in s and 'href="privacy.html"' not in s:
        s=s.replace("</footer>",'<div class="footer-links footer-policy-links"><a href="operator.html">運営者情報</a><a href="privacy.html">プライバシーポリシー</a></div></footer>',1)
    if s!=old:
        p.write_text(s,encoding="utf-8"); print("updated:",p)
