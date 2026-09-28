# 岡山子育てナビ

岡山市の保育施設・入園情報を整理する静的サイトです。GitHub Pages で無料運用する想定です。

## 公開方法
1. このフォルダ一式を GitHub の新規リポジトリへアップロード
2. Settings → Pages → Source を `GitHub Actions` に設定
3. Actions を有効化
4. `Deploy GitHub Pages` が実行されると公開

## 自動更新
`.github/workflows/update-data.yml` が毎週日曜 03:17 JST（UTC 18:17）に岡山市公式ページを確認します。
- 最新の受入見込みPDFのURL・更新日を検出
- PDFから施設情報を再生成（取得できた範囲）
- 緯度経度がない施設を国土地理院の住所検索でジオコーディング
- 変更があれば `data/facilities.json` を自動コミット

制度説明文は自動で書き換えません。

## 無料運用
- Hosting: GitHub Pages
- CI: GitHub Actions（通常の小規模利用の無料枠内想定）
- Map: Leaflet + OpenStreetMap
- Geocoding: 国土地理院 住所検索

## 注意
初期JSONは岡山市公立保育園・公立認定こども園を収録しています。Actionsの初回更新後、受入見込みPDFの解析に成功した施設が追加されます。PDFレイアウト変更時は `scripts/update_data.py` の修正が必要です。
