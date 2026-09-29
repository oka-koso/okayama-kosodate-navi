Google Analytics 4 導入パッチ
測定ID: G-961RLY7WVE

・全HTMLページの head 内にGA4タグを追加
・既に測定IDがあるページはスキップし、二重設置を防止
・記事ページも対象

適用:
1. ZIPの中身を okayama-kosodate-navi リポジトリ直下へアップロードしてCommit
2. Actions → Install Google Analytics 4
3. Run workflow
4. Pages反映後、Google Analytics → レポート → リアルタイム を開き、自分でサイトへアクセスして確認

今後、新しいHTML記事を追加した場合も、このActionを再実行すれば未設置ページだけに追加されます。
