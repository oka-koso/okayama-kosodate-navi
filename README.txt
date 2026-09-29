岡山子育てナビ：トップ「保育園探し・申込みの流れ」パッチ v1

変更内容:
「岡山子育てナビでできること」のセクションだけを5ステップの導線へ置換します。

1. 保育園を探す → hoikuen.html
2. 空き状況を確認 → hoikuen.html
3. 入園時期・締切を確認 → tochuu.html
4. 利用調整点数を確認 → score.html
5. 申込み方法を確認 → moushikomi.html

既存MAP・いま確認したい情報・区別検索・申込ガイドは変更しません。

導入:
ZIPを展開してリポジトリの同じ階層へアップロード後、
Actions → Install home application flow → Run workflow

安全設計:
対象見出しを含むsectionがちょうど1件の場合のみ置換します。
