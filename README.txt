定例更新 206施設マスタ保護パッチ v1

今回の「固定施設マスタが206施設ではありません: 232」対策です。

・現在の正常な206施設マスタを復元用スナップショットとして固定
・定例更新開始時に件数確認
・206件ならそのまま更新
・232件などへ変化していたら、検証済み206件版へ自動復元して更新続行
・復元用データ自体が206件でなければ安全停止
・既存の206件安全チェックは残します

適用:
1. ZIPの中身をリポジトリ直下へアップロードしてCommit
2. Actions → Install Facility Master 206 Guard → Run workflow
3. その後 Update childcare availability (monthly + April + midyear guide) を手動で1回実行
