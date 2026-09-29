from pathlib import Path

index = Path("index.html")
if not index.exists():
    raise SystemExit("index.html が見つかりません")

html = index.read_text(encoding="utf-8")
heading = "岡山子育てナビでできること"

count = html.count(heading)
if count == 0:
    # Already-installed case: do not fail if the new section exists.
    if 'id="application-flow-title"' in html and "保育園探し・申込みの流れ" in html:
        print("OK: すでに導入済みです")
        raise SystemExit(0)
    raise SystemExit("置換対象の見出し「岡山子育てナビでできること」が見つかりません")
if count != 1:
    raise SystemExit(f"置換対象の見出しが1件ではありません: {count}件")

heading_pos = html.index(heading)
section_start = html.rfind("<section", 0, heading_pos)
section_end_start = html.find("</section>", heading_pos)

if section_start == -1 or section_end_start == -1:
    raise SystemExit("対象見出しを含むsectionの境界を特定できません")

section_end = section_end_start + len("</section>")

# Extra safety: ensure the selected section really contains the target heading.
old_section = html[section_start:section_end]
if heading not in old_section:
    raise SystemExit("安全確認に失敗しました: 対象section内に見出しがありません")

new_section = """<section class="application-flow-section" aria-labelledby="application-flow-title">
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
</section>"""

html = html[:section_start] + new_section + html[section_end:]

css_link = '<link rel="stylesheet" href="css/home-application-flow.css">'
if css_link not in html:
    marker = '<link rel="stylesheet" href="css/home-map.css">'
    if marker in html:
        html = html.replace(marker, marker + "\n" + css_link, 1)
    elif "</head>" in html:
        html = html.replace("</head>", css_link + "\n</head>", 1)
    else:
        raise SystemExit("CSSリンクの挿入位置を特定できません")

index.write_text(html, encoding="utf-8")
print("OK: 「保育園探し・申込みの流れ」へ安全に置換しました")
