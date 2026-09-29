共通ヘッダー・フッター v1.1 修正版

v1の失敗原因:
インストーラーの正規表現で <header>/<footer> 検出用の word boundary が誤って二重エスケープされ、
全ページ header=0 footer=0 になっていました。

v1.1:
- 正規表現を修正
- 全HTMLで構造検証
- 一部ページだけ失敗した場合はcommitせず停止
- 再実行しても二重導入しない
- v1が失敗した状態からそのまま導入可能

導入:
ZIPを展開し、同じパスへ上書きアップロード。
Actions → Install unified header and footer → Run workflow
