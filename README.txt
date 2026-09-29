岡山子育てナビ トップページ施設MAP v1

トップのヒーロー直下、「区から保育園を探す」の前にMAPを追加します。

機能
・facility_master.json の既存施設をそのまま利用
・availability_monthly.json を優先して最新の途中入園○△×を表示
・monthlyが無い場合は availability_fixed.json にフォールバック
・全域 / 北区 / 中区 / 東区 / 南区 のワンタッチ絞り込み
・区別カラーのピン
・ピンを押すと園名 / 種別 / 公私 / 所在地 / 0〜5歳受入見込み
・詳しい検索は既存 hoikuen.html へ
・スマホは高さ360px
・マウスホイールズームOFF
・施設データの二重管理なし

導入
1. ZIP内のファイルを同じパスでGitHubへアップロード
2. Actions → Install home facility map → Run workflow
3. 緑になったらPages反映後にトップページを再読み込み

既存の hoikuen.html と js/facilities.js は変更しません。
