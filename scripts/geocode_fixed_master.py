#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "geocode_audit.json"

UA = "OkayamaKosodateNavi/geocoder-v2"
JST = timezone(timedelta(hours=9))

GSI_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# 岡山市を十分に包含する安全用bbox
MIN_LAT, MAX_LAT = 34.45, 34.95
MIN_LON, MAX_LON = 133.65, 134.25

KANJI_NUM = {
    "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()

def valid_coord(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return False
    return (
        MIN_LAT <= lat <= MAX_LAT
        and MIN_LON <= lon <= MAX_LON
    )

def jp_num_to_int(text):
    """
    1～99程度の漢数字を整数へ。
    住所正規化にだけ使用。
    """
    if not text:
        return text

    if text.isdigit():
        return text

    total = 0

    if "十" in text:
        left, _, right = text.partition("十")
        tens = KANJI_NUM.get(left, 1) if left else 1
        ones = KANJI_NUM.get(right, 0) if right else 0
        total = tens * 10 + ones
    else:
        if all(ch in KANJI_NUM for ch in text):
            digits = "".join(str(KANJI_NUM[ch]) for ch in text)
            try:
                total = int(digits)
            except Exception:
                return text
        else:
            return text

    return str(total)

def normalize_japanese_address(address):
    """
    岡山市北区津島東一丁目4-3
      -> 岡山市北区津島東1丁目4-3

    「番地」「号」も検索しやすいハイフン形式へ寄せる。
    """
    s = clean(address)
    s = s.replace("−", "-").replace("－", "-").replace("ー", "-")

    def repl_chome(m):
        return jp_num_to_int(m.group(1)) + "丁目"

    s = re.sub(
        r"([〇一二三四五六七八九十]+)丁目",
        repl_chome,
        s,
    )

    s = re.sub(r"(\d+)番地(\d+)", r"\1-\2", s)
    s = re.sub(r"(\d+)番地", r"\1", s)
    s = re.sub(r"(\d+)号", r"\1", s)

    return s

def query_variants(facility):
    address = clean(facility.get("address", ""))
    name = clean(facility.get("name", ""))

    variants = []

    def add(q):
        q = clean(q)
        if q and q not in variants:
            variants.append(q)

    add(address)
    add(normalize_japanese_address(address))

    # 「岡山市」を落とした形式がGSIで通りやすい場合の保険
    if address.startswith("岡山市"):
        add(address.replace("岡山市", "", 1))

    normalized = normalize_japanese_address(address)
    if normalized.startswith("岡山市"):
        add(normalized.replace("岡山市", "", 1))

    # 最後の補助。施設名だけでは誤地点の危険があるため
    # 必ず「岡山市」とセットにする。
    if name:
        add(f"岡山市 {name}")

    return variants

def gsi_search(query):
    r = requests.get(
        GSI_URL,
        params={"q": query},
        headers={"User-Agent": UA},
        timeout=20,
    )
    r.raise_for_status()

    data = r.json()

    results = []

    for item in data if isinstance(data, list) else []:
        geom = item.get("geometry") or {}
        coords = geom.get("coordinates") or []

        if len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]

        if not valid_coord(lat, lon):
            continue

        results.append({
            "lat": float(lat),
            "lon": float(lon),
            "title": (item.get("properties") or {}).get("title", ""),
            "source": "GSI",
            "query": query,
        })

    return results

def nominatim_search(query):
    r = requests.get(
        NOMINATIM_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 3,
            "countrycodes": "jp",
        },
        headers={"User-Agent": UA},
        timeout=20,
    )
    r.raise_for_status()

    results = []

    for item in r.json():
        lat = item.get("lat")
        lon = item.get("lon")

        if not valid_coord(lat, lon):
            continue

        results.append({
            "lat": float(lat),
            "lon": float(lon),
            "title": item.get("display_name", ""),
            "source": "Nominatim",
            "query": query,
        })

    return results

def choose_result(results, address):
    if not results:
        return None

    # 1件ならそのまま。
    if len(results) == 1:
        return results[0]

    # GSIは同一住所に複数候補が返る場合がある。
    # タイトルに町名末尾が多く含まれるものを優先する。
    normalized_address = re.sub(r"\s+", "", address)

    def score(item):
        title = re.sub(r"\s+", "", item.get("title", ""))
        common = 0
        for size in range(min(12, len(normalized_address)), 2, -1):
            fragment = normalized_address[-size:]
            if fragment in title:
                common = size
                break
        return common

    return max(results, key=score)

def geocode_one(facility):
    address = clean(facility.get("address", ""))

    if not address:
        return None, []

    attempts = []

    # まず日本住所に強い国土地理院
    for query in query_variants(facility):
        try:
            results = gsi_search(query)
            attempts.append({
                "source": "GSI",
                "query": query,
                "results": len(results),
            })

            if results:
                return choose_result(results, address), attempts

        except Exception as e:
            attempts.append({
                "source": "GSI",
                "query": query,
                "error": str(e),
            })

        time.sleep(0.25)

    # GSIで取れなかったものだけNominatim
    for query in query_variants(facility):
        try:
            results = nominatim_search(query)
            attempts.append({
                "source": "Nominatim",
                "query": query,
                "results": len(results),
            })

            if results:
                return choose_result(results, address), attempts

        except Exception as e:
            attempts.append({
                "source": "Nominatim",
                "query": query,
                "error": str(e),
            })

        # Nominatimは低頻度アクセス
        time.sleep(1.1)

    return None, attempts

def main():
    if not MASTER.exists():
        raise RuntimeError("data/facility_master.json がありません。")

    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])

    if len(facilities) != 206:
        raise RuntimeError(
            f"固定施設マスタが206施設ではありません: {len(facilities)}"
        )

    existing_valid = 0
    updated = 0
    failures = []
    source_counts = {
        "GSI": 0,
        "Nominatim": 0,
    }

    for index, facility in enumerate(facilities, start=1):
        if valid_coord(
            facility.get("lat"),
            facility.get("lon"),
        ):
            existing_valid += 1
            continue

        result, attempts = geocode_one(facility)

        if result:
            facility["lat"] = result["lat"]
            facility["lon"] = result["lon"]
            facility["geocode_source"] = result["source"]
            facility["geocode_query"] = result["query"]
            facility["geocode_title"] = result["title"]

            source_counts[result["source"]] += 1
            updated += 1

            print(
                f"[geocode-v2] {index}/206 OK "
                f"{facility['name']} -> "
                f"{result['lat']}, {result['lon']} "
                f"({result['source']})"
            )
        else:
            facility["lat"] = None
            facility["lon"] = None

            failures.append({
                "id": facility.get("id"),
                "name": facility.get("name"),
                "address": facility.get("address"),
                "attempts": attempts,
            })

            print(
                f"[geocode-v2] {index}/206 FAILED "
                f"{facility['name']} / {facility.get('address','')}"
            )

    valid_total = sum(
        1 for f in facilities
        if valid_coord(f.get("lat"), f.get("lon"))
    )

    data["geocoded_at"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    data["geocoded_count"] = valid_total

    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    audit = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "facility_count": len(facilities),
        "previous_valid_coordinates": existing_valid,
        "newly_geocoded": updated,
        "valid_coordinate_count": valid_total,
        "failure_count": len(failures),
        "source_counts": source_counts,
        "failures": failures,
    }

    AUDIT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "[geocode-v2] SUMMARY "
        f"valid={valid_total}/206 "
        f"new={updated} "
        f"failed={len(failures)} "
        f"GSI={source_counts['GSI']} "
        f"Nominatim={source_counts['Nominatim']}"
    )

    # MAPとして実用可能な最低ライン。
    # 失敗分はauditへ残すが、200件以上ならサイト更新を許可。
    if valid_total < 200:
        raise RuntimeError(
            f"座標取得が{valid_total}/206件です。"
            "200件未満のため本番反映を停止します。"
        )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[geocode-v2] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
