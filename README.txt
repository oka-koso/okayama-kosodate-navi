岡山子育てナビ - facility master repair safe patch v1

目的
----
repair Action が .github/workflows や scripts を自動変更・commitしないようにします。
GitHub App に workflows 権限を追加する必要はありません。

アップロードするファイル
------------------------
.github/workflows/repair-facility-master.yml

使い方
------
1. ZIPを展開。
2. 上記ファイルをリポジトリの同じ場所へ上書き。
3. GitHub Actions から「Repair facility master safely」を手動実行。
4. Commit repaired data only が成功することを確認。

安全設計
--------
- commit対象は次の2ファイルだけです。
  data/facility_master.json
  data/facility_master_repair_audit.json
- scripts/ は自動commitしません。
- .github/workflows/ は自動commitしません。
- 想定外ファイルがstageされた場合はpush前に停止します。
- 206施設の検証は scripts/repair_facility_master.py 側に残したままです。

注意
----
既存の scripts/repair_facility_master.py はリポジトリに存在する前提です。
今回のパッチでは、そのスクリプト自体は変更しません。
