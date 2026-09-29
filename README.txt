岡山子育てナビ「利用調整点数かんたん計算」v1

追加ファイル
- score.html
- css/score-calculator.css
- js/score-calculator.js
- data/admission-score-rules-R8.json
- scripts/install_score_calculator.py
- .github/workflows/install-score-calculator.yml

実装内容
- 保護者2人分の基礎点数
- ひとり親の場合「不存在10点」を自動適用 + 区分A +3
- 就労/内職/妊娠出産/疾病/障害/介護看護/災害/求職/就学/
  社会的養護/育休中/育休復帰予定/採用等予定に対応
- 調整点 A〜K に対応
- 同一区分はselect/radio相当のUIで最高1項目だけを適用
- 区分Iは該当祖父母1人ごと -3
- 区分Kは通常合計を表示した上で最終1点にする
- 同点時基準7項目を表示
- 入園可能性・合格率は推測しない
- 入力内容はブラウザ内でのみ計算し、外部送信しない
- ルールはJSON分離。令和9年度版への更新が容易

公式根拠
令和8年度保育利用ガイド P.11-12
https://www.city.okayama.jp/kurashi/cmsfiles/contents/0000012/13000/R8_1-23hoiku.pdf

岡山市保育所等保育利用調整基準
https://www.city.okayama.jp/kurashi/cmsfiles/contents/0000012/12573/R060904kaisei_riyouchouseikizyun.pdf

導入手順
1. ZIP内のファイルを同じパスでGitHubへアップロード。
2. Actions → Install admission score calculator → Run workflow。
3. 緑になったら score.html を確認。
4. index.html / hoikuen.html / moushikomi.html のナビに「点数計算」が追加される。
5. moushikomi.html の点数欄にも計算ページへのボタンが追加される。

注意
令和9年度保育利用ガイドは2026-10-14公開予定。
公開後はR8→R9の基準差分を確認し、
data/admission-score-rules-R9.json 等へ更新する想定。
