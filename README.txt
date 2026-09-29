子育て備忘録 v1
タイトル: 子育て備忘録
キャッチ: 知っておくとちょっと助かる、子育てのあれこれ。

ZIPの中身を okayama-kosodate-navi の直下へアップロードしてCommit。
Actions → Install Kosodate Bibouroku → Run workflow。

追加内容:
・bibouroku.html 記事一覧
・トップページに新着記事欄
・共通ナビへ「子育て備忘録」を追加（既存ナビを検出できた場合）
・記事データ data/bibouroku.json
・最初の記事「保育園探し、まず何から始める？」
・sitemap.xmlへ一覧・記事を追加
・既存の保育園検索、MAP、点数計算等には触れません。

今後の記事追加は articles/ にHTMLを追加し、data/bibouroku.json に1件追記すれば、
一覧とトップ新着欄へ自動表示できます。
