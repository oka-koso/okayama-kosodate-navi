#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber
import requests

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AUDIT = ROOT / "data" / "services_audit.json"

DEFAULT_PDF = "https://www.city.okayama.jp/kurashi/cmsfiles/contents/0000012/13000/R8_32-ura_hoiku.pdf"
UA = "OkayamaKosodateNavi/services-v1"
JST = timezone(timedelta(hours=9))

PHONE_RE = re.compile(r"(?:(086)[-－ー])?([0-9]{3,4})[-－ー]([0-9]{4})")
POSTAL_RE = re.compile(r"〒\s*([0-9]{3})[-－ー]([0-9]{4})")
TIME_RE = re.compile(r"(?:1[89]|2[0-3]):[0-5][0-9]")

def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()

def digits(v):
    return re.sub(r"\D", "", str(v or ""))

def normalize_phone(v):
    d = digits(v)
    return "086" + d if len(d) == 7 else d

def normalize_postal(v):
    d = digits(v)
    return d if len(d) == 7 else ""

def normalize_locality(v):
    s = clean(v).replace("　", "")
    s = re.sub(r"^岡山市(?:北区|中区|東区|南区)", "", s)
    s = re.sub(r"^(?:北区|中区|東区|南区)", "", s)
    s = re.sub(r"\s+", "", s)
    s = s.replace("一丁目", "1丁目").replace("二丁目", "2丁目").replace("三丁目", "3丁目")
    s = s.replace("四丁目", "4丁目").replace("五丁目", "5丁目").replace("六丁目", "6丁目")
    return s

def row_groups(words, tolerance=2.8):
    words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))
    rows = []
    for word in words:
        top = float(word["top"])
        if not rows or abs(top - rows[-1]["top"]) > tolerance:
            rows.append({"top": top, "words": [word]})
        else:
            rows[-1]["words"].append(word)
    for row in rows:
        row["words"].sort(key=lambda w: float(w["x0"]))
    return rows

def row_text(row):
    return clean(" ".join(str(w["text"]) for w in row["words"]))

def collect_contacts(rows):
    contacts = []
    for row in rows:
        text = row_text(row)
        pm = POSTAL_RE.search(text)
        if not pm:
            continue
        phone_m = PHONE_RE.search(text[:pm.start()])
        if not phone_m:
            continue

        area, p2, p3 = phone_m.groups()
        contacts.append({
            "top": float(row["top"]),
            "phone": normalize_phone(f"{area or ''}{p2}{p3}"),
            "postal": pm.group(1) + pm.group(2),
            "locality": text[pm.end():].strip(),
            "raw": text,
        })
    return contacts

def master_indexes(facilities):
    by_pair = {}
    order = {}
    for i, f in enumerate(facilities):
        phone = normalize_phone(f.get("phone", ""))
        postal = normalize_postal(f.get("postal", ""))
        order[f["id"]] = i
        by_pair.setdefault((phone, postal), []).append(f)
    return by_pair, order

def address_match(contact, candidates):
    loc = normalize_locality(contact.get("locality", ""))
    matches = []
    for f in candidates:
        addr = normalize_locality(f.get("address", ""))
        if loc and addr and (loc in addr or addr in loc):
            matches.append(f)
    return matches

def find_service_centers(words, page_width, first_contact_top):
    """
    表ヘッダの縦書き4列のx座標を自動検出。
    右側40%かつ最初の施設連絡先より上を対象にする。
    """
    header = [
        w for w in words
        if float(w["x0"]) > page_width * 0.60
        and float(w["top"]) < first_contact_top
    ]

    def centers_for(chars):
        xs = []
        for w in header:
            t = clean(w["text"])
            if any(ch in t for ch in chars):
                xs.append((float(w["x0"]) + float(w["x1"])) / 2)
        return xs

    candidates = []
    for chars in [
        ["延", "長"],
        ["一", "時", "預", "か", "り"],
        ["休", "日"],
        ["支", "援", "セ", "ン", "タ"]
    ]:
        xs = centers_for(chars)
        if xs:
            candidates.append(sum(xs) / len(xs))
        else:
            candidates.append(None)

    # 自動検出が崩れた場合は、表の位置比率から安全な既定値を使用。
    defaults = [
        page_width * 0.665,
        page_width * 0.705,
        page_width * 0.727,
        page_width * 0.750,
    ]

    centers = [
        candidates[i] if candidates[i] is not None else defaults[i]
        for i in range(4)
    ]

    # x順が崩れていれば既定値に戻す。
    if centers != sorted(centers):
        centers = defaults

    return {
        "extended": centers[0],
        "temporary": centers[1],
        "holiday": centers[2],
        "support_center": centers[3],
    }

def words_in_band(words, y0, y1):
    result = []
    for w in words:
        cy = (float(w["top"]) + float(w["bottom"])) / 2
        if y0 <= cy < y1:
            result.append(w)
    return result

def column_words(words, center, radius):
    out = []
    for w in words:
        cx = (float(w["x0"]) + float(w["x1"])) / 2
        if abs(cx - center) <= radius:
            out.append(w)
    return out

def service_values(page_words, centers, y0, y1):
    band = words_in_band(page_words, y0, y1)
    ordered = sorted(centers.values())
    gaps = [b-a for a,b in zip(ordered, ordered[1:]) if b-a > 0]
    radius = max(5.0, min(gaps) * 0.42) if gaps else 10.0

    result = {}

    ext_words = column_words(band, centers["extended"], radius)
    ext_text = clean(" ".join(str(w["text"]) for w in ext_words))
    result["extended"] = bool(TIME_RE.search(ext_text) or "まで" in ext_text)

    for key in ["temporary", "holiday", "support_center"]:
        ws = column_words(band, centers[key], radius)
        text = "".join(clean(w["text"]) for w in ws)
        result[key] = ("○" in text or "〇" in text)

    return result

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])
    if len(facilities) != 206:
        raise RuntimeError(f"固定マスタが206施設ではありません: {len(facilities)}")

    pdf_url = data.get("source_contact_pdf") or DEFAULT_PDF
    r = requests.get(pdf_url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()

    by_pair, master_order = master_indexes(facilities)
    found = {}
    unresolved = []
    page_stats = []

    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(
                x_tolerance=1.5,
                y_tolerance=2.5,
                keep_blank_chars=False,
            )
            rows = row_groups(words)
            contacts = collect_contacts(rows)

            if not contacts:
                page_stats.append({"page": page_no, "contacts": 0})
                continue

            centers = find_service_centers(
                words,
                float(page.width),
                min(c["top"] for c in contacts),
            )

            # 同一連絡先共有施設を出現順で処理するため候補をキュー化。
            pair_seen = {}

            matched_page = 0

            for i, contact in enumerate(contacts):
                pair = (contact["phone"], contact["postal"])
                candidates = by_pair.get(pair, [])

                if not candidates:
                    unresolved.append({
                        "page": page_no,
                        "reason": "no-phone-postal-match",
                        **contact,
                    })
                    continue

                selected = None

                if len(candidates) == 1:
                    selected = candidates[0]
                else:
                    am = address_match(contact, candidates)
                    if len(am) == 1:
                        selected = am[0]
                    else:
                        pool = am if len(am) > 1 else candidates
                        pool = sorted(pool, key=lambda f: master_order[f["id"]])
                        idx = pair_seen.get(pair, 0)
                        if idx < len(pool):
                            selected = pool[idx]
                            pair_seen[pair] = idx + 1

                if not selected:
                    unresolved.append({
                        "page": page_no,
                        "reason": "ambiguous",
                        "candidates": [x["name"] for x in candidates],
                        **contact,
                    })
                    continue

                prev_top = contacts[i-1]["top"] if i > 0 else contact["top"] - 18
                next_top = contacts[i+1]["top"] if i+1 < len(contacts) else contact["top"] + 18
                y0 = (prev_top + contact["top"]) / 2
                y1 = (contact["top"] + next_top) / 2

                services = service_values(words, centers, y0, y1)

                found[selected["id"]] = {
                    **services,
                    "source": pdf_url,
                    "source_as_of": "令和7年8月時点",
                }
                matched_page += 1

            page_stats.append({
                "page": page_no,
                "contacts": len(contacts),
                "matched": matched_page,
                "centers": centers,
            })

    for f in facilities:
        if f["id"] in found:
            f["services"] = {
                "extended": found[f["id"]]["extended"],
                "temporary": found[f["id"]]["temporary"],
                "holiday": found[f["id"]]["holiday"],
                "support_center": found[f["id"]]["support_center"],
            }
            f["services_source"] = found[f["id"]]["source"]
            f["services_source_as_of"] = found[f["id"]]["source_as_of"]
        else:
            current = f.get("services") or {}
            f["services"] = {
                "extended": current.get("extended"),
                "temporary": current.get("temporary"),
                "holiday": current.get("holiday"),
                "support_center": current.get("support_center"),
            }

    audit = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source_pdf": pdf_url,
        "facility_count": len(facilities),
        "matched_count": len(found),
        "unresolved_count": len(unresolved),
        "page_stats": page_stats,
        "unresolved": unresolved,
        "service_true_counts": {
            key: sum(1 for v in found.values() if v[key] is True)
            for key in ["extended", "temporary", "holiday", "support_center"]
        },
    }

    AUDIT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "[services-v1] "
        f"matched={len(found)}/206 "
        f"unresolved={len(unresolved)} "
        f"true={audit['service_true_counts']}"
    )

    # 誤った「なし」を大量反映しないため、照合率を厳格チェック。
    if len(found) < 200 or unresolved:
        raise RuntimeError(
            "サービス情報の照合監査に失敗しました。"
            "facility_master.json は更新せず audit の確認が必要です。"
        )

    data["services_generated_at"] = audit["generated_at"]
    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[services-v1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
