施設マスタ修復＋定例保護 v2

現在232件でも実行できます。

1. Git履歴から facilities 配列が実際に206件だった最新正常版を探す
2. facility_master.json を正常版へ復元
3. 正常206件版を復元用として固定
4. 定例更新時に再び232件等になれば206件版へ自動復元
5. 復元用データまで異常なら安全停止

適用:
ZIPをリポジトリ直下へアップロードしてCommit
→ Actions → Repair and Guard Facility Master → Run workflow

成功後:
Update childcare availability (monthly + April + midyear guide)
を手動で1回実行。
