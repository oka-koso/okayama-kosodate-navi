#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = ROOT / "scripts" / "update_availability_fixed.py"
SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
DISCOVERY_AUDIT = ROOT / "data" / "availability_dual_discovery_audit.json"
JST = timezone(timedelta(hours=9))
UA = "OkayamaKosodateNavi/availability-dual-v1"


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def load_legacy():
    spec = importlib.util.spec_from_file_location("availability_fixed_v32", LEGACY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("update_availability_fixed.py を読み込めません。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_source_page():
    r = requests.get(SOURCE_PAGE, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    raw_text = soup.get_text("\n", strip=True)
    page_text = soup.get_text(" ", strip=True)

    page_updated = ""
    m = re.search(r"\[(\d{4})年(\d{1,2})月(\d{1,2})日\]", raw_text)
    if m:
        page_updated = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    candidates = []
    for order, a in enumerate(soup.find_all("a", href=True)):
        title = clean(" ".join(a.stripped_strings))
        href = requests.compat.urljoin(SOURCE_PAGE, a["href"])
        path = href.split("?", 1)[0].lower()

        if not path.endswith(".pdf"):
            continue
        if "認可外" in title or "教育利用" in title:
            continue

        filename = path.rsplit("/", 1)[-1]
        if not (
            "受入見込み" in title
            or ("ninka" in filename and "ninkagai" not in filename)
        ):
            continue

        # 4月入園は専用ストリーム。それ以外の認可保育PDFは年度途中。
        is_april = bool(re.search(r"(?:令和\s*[0-9０-９]+年\s*)?4月", title))
        stream = "april" if is_april else "monthly"

        score = 0
        if "受入見込み" in title:
            score += 5
        if "認可保育園" in title:
            score += 5
        elif "認可" in title:
            score += 2
        if "ninka" in filename and "ninkagai" not in filename:
            score += 5
        if stream == "april" and "4月" in title:
            score += 5

        candidates.append({
            "stream": stream,
            "score": score,
            "order": order,
            "title": title or filename,
            "url": href,
        })

    return page_updated, page_text, candidates


def choose_candidate(candidates, stream):
    rows = [x for x in candidates if x["stream"] == stream]
    if not rows:
        return None
    rows.sort(key=lambda x: (x["score"], x["order"]), reverse=True)
    return rows[0]


def run_legacy_for(legacy, candidate, page_updated, page_text, out_name, audit_name):
    legacy.OUT = ROOT / "data" / out_name
    legacy.AUDIT = ROOT / "data" / audit_name
    legacy.latest_pdf = lambda: (
        candidate["title"],
        candidate["url"],
        page_updated,
        page_text,
    )
    legacy.main()


def main():
    if not LEGACY_PATH.exists():
        raise RuntimeError("scripts/update_availability_fixed.py がありません。")

    legacy = load_legacy()
    page_updated, page_text, candidates = fetch_source_page()
    monthly = choose_candidate(candidates, "monthly")
    april = choose_candidate(candidates, "april")

    discovery = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source_page": SOURCE_PAGE,
        "source_page_updated": page_updated,
        "monthly_candidate": monthly,
        "april_candidate": april,
        "all_candidates": candidates,
        "results": {},
    }

    if not monthly:
        discovery["results"]["monthly"] = "not-found"
        DISCOVERY_AUDIT.write_text(
            json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("年度途中入園の認可保育施設PDFを発見できません。")

    # 1) 年度途中入園。既存 availability_fixed.json も互換用に同期する。
    run_legacy_for(
        legacy, monthly, page_updated, page_text,
        "availability_monthly.json",
        "availability_monthly_audit.json",
    )
    shutil.copyfile(
        ROOT / "data" / "availability_monthly.json",
        ROOT / "data" / "availability_fixed.json",
    )
    shutil.copyfile(
        ROOT / "data" / "availability_monthly_audit.json",
        ROOT / "data" / "availability_fixed_audit.json",
    )
    discovery["results"]["monthly"] = "updated"

    # 2) 翌年度4月入園。未公表なら正常終了し、既存ファイルは消さない。
    #    公表された瞬間から同じv3.2厳格パーサーで別JSONへ保存する。
    if april:
        try:
            run_legacy_for(
                legacy, april, page_updated, page_text,
                "availability_april.json",
                "availability_april_audit.json",
            )
            discovery["results"]["april"] = "updated"
        except Exception as exc:
            discovery["results"]["april"] = f"parse-error: {exc}"
            DISCOVERY_AUDIT.write_text(
                json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            raise
    else:
        discovery["results"]["april"] = "not-published-yet"

    DISCOVERY_AUDIT.write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "[availability-dual] SUCCESS "
        f"monthly={discovery['results']['monthly']} "
        f"april={discovery['results']['april']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[availability-dual] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
