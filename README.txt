岡山子育てナビ 途中入園ページ + 自動更新 v1.2

v1.2 修正
・途中入園ページ上部を既存ページと同じヘッダー構造へ統一
・🌱ブランドマーク、既存ナビ、既存 footer をそのまま使用
・独自のハンバーガーボタンを廃止（既存サイトのレスポンシブ仕様に統一）
・独自 hero ではなく既存の page-hero デザインを利用
・トップページ「いま確認したい情報」に「途中入園（4月以外）」を追加
・その行をクリックすると tochuu.html へ直接移動
・同じWorkflowを再実行しても重複追加しない
・v1.1のGit rebase時 unstaged changes 対策を維持

導入
1. ZIP内をリポジトリの同じパスへ上書きアップロード
2. Actions → Install midyear admission page → Run workflow
3. 緑になれば導入完了

自動更新
既存の Update childcare availability (monthly + April + midyear guide) が毎日実行され、
年度途中の受入見込みPDF更新処理と同じ実行内で data/midyear_admission.json を同期します。
