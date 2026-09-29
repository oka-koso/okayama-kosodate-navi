from pathlib import Path
import re

index = Path("index.html")
if not index.exists():
    raise SystemExit("index.html が見つかりません")

html = index.read_text(encoding="utf-8")

new_section = '''<section class="application-flow-section" aria-labelledby="application-flow-title">
<div class="container">
  <div class="section-head">
    <div>
      <h2 id="application-flow-title">保育園探し・申込みの流れ</h2>
      <p>何から始めればいいか迷ったら、順番に確認できます。</p>
    </div>
  </div>
  <div class="application-flow">
    <a class="flow-step" href="hoikuen.html">
      <span class="flow-number">1</span><span class="flow-icon" aria-hidden="true">🔎</span>
      <span class="flow-copy"><strong>保育園を探す</strong><small>地域・地図・条件から希望の園を探す</small></span>
      <span class="flow-arrow" aria-hidden="true">→</span>
    </a>
    <a class="flow-step" href="hoikuen.html">
      <span class="flow-number">2</span><span class="flow-icon" aria-hidden="true">👶</span>
      <span class="flow-copy"><strong>空き状況を確認</strong><small>年齢別の最新の受入見込みを確認する</small></span>
      <span class="flow-arrow" aria-hidden="true">→</span>
    </a>
    <a class="flow-step" href="tochuu.html">
      <span class="flow-number">3</span><span class="flow-icon" aria-hidden="true">📅</span>
      <span class="flow-copy"><strong>入園時期・締切を確認</strong><small>途中入園の対象月や申込締切を確認する</small></span>
      <span class="flow-arrow" aria-hidden="true">→</span>
    </a>
    <a class="flow-step" href="score.html">
      <span class="flow-number">4</span><span class="flow-icon" aria-hidden="true">🧮</span>
      <span class="flow-copy"><strong>利用調整点数を確認</strong><small>世帯状況から点数の目安を計算する</small></span>
      <span class="flow-arrow" aria-hidden="true">→</span>
    </a>
    <a class="flow-step flow-step-primary" href="moushikomi.html">
      <span class="flow-number">5</span><span class="flow-icon" aria-hidden="true">📝</span>
      <span class="flow-copy"><strong>申込み方法を確認</strong><small>必要書類・申込日程・手続きの流れを見る</small></span>
      <span class="flow-arrow" aria-hidden="true">→</span>
    </a>
  </div>
  <p class="flow-note">※ 4月入園を希望する方は「申込み方法を確認」から年度別の申込情報をご確認ください。</p>
</div>
</section>'''

pattern = re.compile(
    r'<section\\b[^>]*>(?:(?!</section>).)*?岡山子育てナビでできること(?:(?!</section>).)*?</section>',
    re.S
)
matches = list(pattern.finditer(html))
if len(matches) != 1:
    raise SystemExit(f"置換対象sectionが1件ではありません: {len(matches)}件")

html = pattern.sub(new_section, html, count=1)

css_link = '<link rel="stylesheet" href="css/home-application-flow.css">'
if css_link not in html:
    marker = '<link rel="stylesheet" href="css/home-map.css">'
    if marker in html:
        html = html.replace(marker, marker + css_link, 1)
    else:
        html = html.replace('</head>', css_link + '</head>', 1)

index.write_text(html, encoding="utf-8")
print("OK: トップの案内セクションを置換しました")
