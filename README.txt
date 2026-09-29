岡山子育てナビ：トップ「保育園探し・申込みの流れ」パッチ v1.1

v1の修正:
- section検出の正規表現エスケープ不具合を修正。
- 「岡山子育てナビでできること」の見出し位置から、直前の<section>と直後の</section>を特定する方式へ変更。
- すでに導入済みの場合は正常終了し、二重挿入しません。
- 対象を安全に特定できない場合はindex.htmlを書き換えません。

導入:
ZIPを展開して同じ階層へ上書き後、
Actions → Install home application flow → Run workflow
