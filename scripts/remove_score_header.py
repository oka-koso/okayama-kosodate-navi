#!/usr/bin/env python3
from pathlib import Path
import re

p = Path("js/site-shell.js")
if not p.exists():
    raise SystemExit("ERROR: js/site-shell.js not found")

s = p.read_text(encoding="utf-8")
before = s

patterns = [
    r"<a\b[^>]*href=[\"'][^\"']*score\.html(?:[^\"']*)[\"'][^>]*>\s*点数計算\s*</a>",
    r"\[\s*[\"'][^\"']*score\.html[^\"']*[\"']\s*,\s*[\"']点数計算[\"']\s*\]\s*,?",
    r"\{\s*[^{}]*(?:href|url|path)\s*:\s*[\"'][^\"']*score\.html[^\"']*[\"'][^{}]*(?:label|text|name)\s*:\s*[\"']点数計算[\"'][^{}]*\}\s*,?",
    r"\{\s*[^{}]*(?:label|text|name)\s*:\s*[\"']点数計算[\"'][^{}]*(?:href|url|path)\s*:\s*[\"'][^\"']*score\.html[^\"']*[\"'][^{}]*\}\s*,?"
]

for pat in patterns:
    s = re.sub(pat, "", s, flags=re.I)

s = re.sub(r"<a\b[^>]*>\s*点数計算\s*</a>", "", s, flags=re.I)
s = re.sub(r",\s*,", ",", s)
s = re.sub(r"\[\s*,", "[", s)
s = re.sub(r",\s*\]", "]", s)

if s == before:
    print("WARN: No score navigation item matched.")
    print("Diagnostic lines:")
    for i,line in enumerate(before.splitlines(),1):
        if "点数計算" in line or "score.html" in line:
            print(f"{i}: {line[:500]}")
    raise SystemExit("ERROR: score header item was not removed")

if "子育て備忘録" not in s:
    raise SystemExit("ERROR: 子育て備忘録 nav item disappeared; aborting")

if "点数計算" in s:
    print("Remaining lines:")
    for i,line in enumerate(s.splitlines(),1):
        if "点数計算" in line:
            print(f"{i}: {line[:500]}")
    raise SystemExit("ERROR: remaining 点数計算 found in shared shell")

p.write_text(s, encoding="utf-8")
print("OK: removed 点数計算 from shared header")
print("OK: 子育て備忘録 remains")
