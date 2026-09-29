岡山子育てナビ：年度途中入園 / 4月入園 受入見込み切替 v1

目的
- 10月以降に岡山市が同時公開する「年度途中入園」と「翌年4月入園」を混同しない。
- 画面上でワンタッチ切替。
- 4月分が未公表の時期は切替UIを表示しない。
- 既存のv3.2厳格照合（電話+郵便番号+住所）をそのまま再利用する。

アップロードするファイル
1. hoikuen.html
2. js/facilities.js
3. css/availability-switch.css  ← 新規
4. scripts/update_availability_dual.py  ← 新規
5. scripts/update_availability_fixed.py  ← 現行v3.2（依存元。既存と同内容なら上書きでOK）
6. .github/workflows/update-availability-fixed.yml  ← 既存workflowを置換

データ
- data/availability_monthly.json : 年度途中入園
- data/availability_april.json   : 翌年度4月入園
- data/availability_fixed.json   : 旧コード互換用。monthlyと同じ内容を維持

初回実行
Actions → Update childcare availability (monthly + April) → Run workflow

2026-09-29現在、岡山市は令和9年4月分を10月14日公開予定のため、
現時点では availability_april.json は生成されないのが正常です。
初回実行では availability_monthly.json が生成されます。

10月14日以降
公式ページに4月分PDFが追加されると、毎日のActionが自動検出します。
既存v3.2パーサーで安全に206施設へ照合できた場合のみ
availability_april.json を生成/更新します。
ブラウザはこのファイルを検出すると自動で切替UIを表示します。

表示期間
- 9～12月: 翌年4月データだけを4月タブとして表示
- 1～4月 : 当年4月データを表示
- 5～8月 : 古い4月データは自動的に非表示
このため前年の4月データが残っても、翌年度に誤表示しません。

安全策
- 4月PDF未公表: 正常終了（エラーにしない）
- 4月PDF公表済みだが解析失敗: 誤データを書かずActionを失敗扱い
- monthlyは availability_fixed.json にも同期するため旧表示との互換性あり
- 施設カード自体には data-facility-id を付けない既存v4設計を維持
- card→map は data-map-id、popup→card は data-scroll-card-id のまま
- 公式HP/telリンクの標準ブラウザ動作も維持

確認済み
- Python 2ファイル py_compile OK
- facilities.js node --check OK
