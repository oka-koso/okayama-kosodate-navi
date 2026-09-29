共通ヘッダー・フッター v1.2

v1.2修正:
- footerが存在するページ → 既存footerを共通footerホストへ置換
- footerが存在しない about/operator/privacy → </body>直前へ共通footerホストを追加
- headerは従来どおり安全に置換
- 全主要ページをSafety check
- エラー時はcommit前に停止
- 再実行可能

v1.1が失敗した状態から、そのまま上書き導入できます。
Actions → Install unified header and footer → Run workflow
