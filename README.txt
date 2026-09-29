岡山子育てナビ 施設マスター復旧パッチ v1

原因:
月次の受入見込みPDFから固定施設マスターを自動更新する旧処理が、
PDF文字列を誤結合して非正規施設を追加し、郵便番号等も破損させていました。
固定施設マスターと月次空き状況は分離するという本来の設計に戻します。

使い方:
1. ZIPの中身をリポジトリのルートへアップロード（同名は上書き）
2. GitHub Actions で "Repair facility master and guard it" を Run workflow
3. 成功後、"Update childcare availability (monthly + April + midyear guide)" を再実行

処理内容:
- facility_name_master.json の正規206 IDだけを残す
- PDF由来で誤追加された非正規レコードを削除
- 園名/区/種別などの固定識別情報を正規名マスターへ戻す
- address 内に明示された 〒xxx-xxxx からのみ郵便番号を復旧（推測しない）
- 監査 data/facility_master_repair_audit.json を出力
- auto_added_from_availability_pdf_v5_2 を生成する旧スクリプトを検出
- その旧スクリプトを呼ぶ workflow の schedule だけを除去し、手動実行は残す

安全設計:
- 正規206 IDの欠落が1件でもあれば復旧を中止
- 復旧後が206件でなければ中止
- 郵便番号形式が不正なら中止
