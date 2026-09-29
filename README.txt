Google AdSense 接続パッチ v1

Publisher ID:
ca-pub-2321879700607801

処理:
- サイト内HTMLの </head> 直前へAdSenseコードを追加
- 同じPublisher IDが既にあるページには重複追加しない
- 404.htmlは対象外
- 本文・CSS・既存機能は変更しない
- 主要ページでPublisher IDをSafety check

導入:
1. ZIPの中身をリポジトリのルートへ上書きアップロード
2. GitHub → Actions
3. Install Google AdSense code
4. Run workflow
5. GitHub Pages反映後、AdSense側でサイト確認/審査へ進む

注意:
これはAdSense接続コードの導入です。
ads.txtはGitHub Pagesのサブパス構成を確認して別途対応します。
