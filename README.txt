子育て備忘録 ヘッダー/フッター修正 v1.2

原因:
備忘録v1で、新規ページに既存サイトの基本CSS・共通shell CSS・polish CSSの読み込みが不足していました。
また共通ナビへ「子育て備忘録」を追加する処理にも正規表現のエスケープ不備がありました。

修正:
- bibouroku.html
- articles/hoikuen-sagashi-hajimekata.html
に以下を既存階層に合わせて追加:
  css/style.css
  css/site-shell.css
  css/site-shell-polish.css
  js/common.js
  js/site-shell.js
  js/site-shell-polish.js

さらに:
- js/site-shell.js の共通ナビへ「子育て備忘録」を確実に追加
- 新規ページは旧AdSense一括導入後に作られたため、AdSense接続コードも追加
- articles/配下は ../ パスで読み込み
- site-shell.js自体がarticles階層を判定するため、ヘッダー/フッター内リンクも正しい階層になる

導入:
ZIPの中身を okayama-kosodate-navi リポジトリ直下へアップロードしてCommit。
Actions → Fix Bibouroku Header Footer → Run workflow。

追加変更 v1.2:
- ヘッダーの「点数計算」を「子育て備忘録」に置換
- 点数計算ページ score.html 自体は削除しない
- score.html への導線はトップや途中入園ページ、記事内リンク等に残す
- 既に「子育て備忘録」が別位置に追加されている場合は重複を除去
