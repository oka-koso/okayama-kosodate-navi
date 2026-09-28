#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
OUT = ROOT / "data" / "availability_fixed.json"
AUDIT = ROOT / "data" / "availability_fixed_audit.json"

SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
UA = "OkayamaKosodateNavi/availability-fixed-v3.2-shared-contact-address-clean"
JST = timezone(timedelta(hours=9))

STATUS_MAP = {"○": "○", "〇": "○", "△": "△", "×": "×"}

PHONE_3_RE = re.compile(r"(?:(086)[-－ー])?([0-9]{3,4})[-－ー]([0-9]{4})")
POSTAL_RE = re.compile(r"〒\s*([0-9]{3})[-－ー]([0-9]{4})")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def digits(value):
    return re.sub(r"\D", "", value or "")


def normalize_phone(value):
    d = digits(value)

    # 岡山市内PDFは市外局番086を省略する。
    if len(d) == 7:
        return "086" + d

    return d


def normalize_postal(value):
    d = digits(value)
    return d if len(d) == 7 else ""


def latest_pdf():
    r = requests.get(
        SOURCE_PAGE,
        headers={"User-Agent": UA},
        timeout=30,
    )
    r.raise_for_status()

    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    soup = BeautifulSoup(r.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    page_updated = ""
    m = re.search(
        r"\[(\d{4})年(\d{1,2})月(\d{1,2})日\]",
        soup.get_text("\n", strip=True),
    )
    if m:
        page_updated = (
            f"{int(m.group(1)):04d}-"
            f"{int(m.group(2)):02d}-"
            f"{int(m.group(3)):02d}"
        )

    candidates = []

    for a in soup.find_all("a", href=True):
        text = clean(" ".join(a.stripped_strings))
        href = requests.compat.urljoin(SOURCE_PAGE, a["href"])
        path = href.split("?", 1)[0].lower()

        if not path.endswith(".pdf"):
            continue
        if "認可外" in text or "教育利用" in text:
            continue

        filename = path.rsplit("/", 1)[-1]
        score = 0

        if "受入見込み" in text:
            score += 5
        if "認可保育園" in text:
            score += 5
        elif "認可" in text:
            score += 2
        if "ninka" in filename and "ninkagai" not in filename:
            score += 5

        if score >= 5:
            candidates.append((score, text or filename, href))

    if not candidates:
        raise RuntimeError("最新の認可保育施設受入見込みPDFを発見できません。")

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, title, url = candidates[0]

    return title, url, page_updated, page_text


def group_words_by_row(words, tolerance=2.8):
    words = sorted(
        words,
        key=lambda w: (float(w["top"]), float(w["x0"])),
    )

    rows = []

    for word in words:
        top = float(word["top"])

        if not rows or abs(top - rows[-1]["top"]) > tolerance:
            rows.append({
                "top": top,
                "words": [word],
            })
        else:
            rows[-1]["words"].append(word)
            n = len(rows[-1]["words"])
            rows[-1]["top"] = (
                rows[-1]["top"] * (n - 1) + top
            ) / n

    for row in rows:
        row["words"].sort(key=lambda w: float(w["x0"]))

    return rows


def row_text(row):
    return clean(
        " ".join(str(w["text"]) for w in row["words"])
    )


def find_age_centers(rows):
    """
    ヘッダの0～5歳のx座標を取得。
    """
    result = {}
    trans = str.maketrans("０１２３４５", "012345")

    for row in rows:
        for word in row["words"]:
            text = clean(str(word["text"]))
            m = re.fullmatch(r"([0-5０-５])歳", text)

            if not m:
                continue

            age = int(m.group(1).translate(trans))
            result[age] = (
                float(word["x0"]) + float(word["x1"])
            ) / 2

    return result


def normalize_locality(value):
    value = clean(value)
    value = value.replace("　", "")
    value = re.sub(r"^岡山市(?:北区|中区|東区|南区)", "", value)
    value = re.sub(r"^(?:北区|中区|東区|南区)", "", value)
    value = re.sub(r"\s+", "", value)

    # 受入PDFでは住所セルの後ろに次列の「園」等が混ざることがある。
    # 例: 「今7-17-7 園」→「今7-17-7」
    # 住所末尾が数字で終わっている場合に限り、後続の非住所文字を除去する。
    m = re.match(r"^(.+?\d(?:[-－ー]\d+)*)[^0-9０-９-－ー]*$", value)
    if m:
        value = m.group(1)

    return value


def normalize_name(value):
    value = clean(value)
    value = value.replace("　", "")
    value = value.replace("（", "(").replace("）", ")")
    value = value.replace("・", "")
    value = re.sub(r"\s+", "", value)
    return value


def parse_contact_row(row):
    """
    各施設の電話番号・〒所在地行を施設キーとして使う。
    locality（町名以下）も保持し、同じ電話+郵便番号を共有する施設を住所で分離する。
    """
    text = row_text(row)

    postal_m = POSTAL_RE.search(text)
    if not postal_m:
        return None

    postal = postal_m.group(1) + postal_m.group(2)

    prefix = text[:postal_m.start()]
    phone_m = PHONE_3_RE.search(prefix)
    if not phone_m:
        return None

    area, p2, p3 = phone_m.groups()
    phone = normalize_phone(f"{area or ''}{p2}{p3}")

    locality = text[postal_m.end():].strip()

    # 年齢欄・備考などが後ろに混ざった場合を除去
    locality = re.split(
        r"\s+(?:[○〇△×](?:\s+[○〇△×])|0歳|1歳|2歳|3歳|4歳|5歳)",
        locality,
        maxsplit=1,
    )[0].strip()

    return {
        "phone": phone,
        "postal": postal,
        "locality": locality,
        "text": text,
        "top": row["top"],
    }


def collect_contact_rows(rows):
    contacts = []

    for index, row in enumerate(rows):
        item = parse_contact_row(row)
        if not item:
            continue

        item["row_index"] = index

        # 園名が別行に分かれるPDF対策。
        # 電話行の直前2行～直後1行を照合用contextとして保存。
        lo = max(0, index - 2)
        hi = min(len(rows), index + 2)
        item["context"] = clean(
            " ".join(row_text(rows[i]) for i in range(lo, hi))
        )

        contacts.append(item)

    return contacts


def master_indexes(master):
    """
    固定マスタを電話・郵便番号・住所で索引化する。
    同一連絡先を完全共有する施設については、固定マスタ上の順序も保持する。
    """
    by_phone_postal = {}
    by_phone = {}
    by_postal = {}
    master_order = {}

    for order, facility in enumerate(master.get("facilities", [])):
        master_order[facility["id"]] = order
        phone = normalize_phone(facility.get("phone", ""))
        postal = normalize_postal(facility.get("postal", ""))

        if phone and postal:
            by_phone_postal.setdefault((phone, postal), []).append(facility)

        if phone:
            by_phone.setdefault(phone, []).append(facility)

        if postal:
            by_postal.setdefault(postal, []).append(facility)

    return {
        "by_phone_postal": by_phone_postal,
        "by_phone": by_phone,
        "by_postal": by_postal,
        "master_order": master_order,
    }


def disambiguate_candidates(contact, candidates):
    """
    同じ電話+郵便番号を共有する施設を
    1) 所在地
    2) PDF近傍の園名
    の順で一意化する。
    """
    if len(candidates) <= 1:
        return candidates[0] if candidates else None, "single"

    pdf_locality = normalize_locality(contact.get("locality", ""))

    # 1. 住所完全/包含一致
    address_matches = []
    if pdf_locality:
        for facility in candidates:
            master_locality = normalize_locality(facility.get("address", ""))

            if not master_locality:
                continue

            if (
                pdf_locality == master_locality
                or pdf_locality in master_locality
                or master_locality in pdf_locality
            ):
                address_matches.append(facility)

    if len(address_matches) == 1:
        return address_matches[0], "address"

    if len(address_matches) > 1:
        candidates = address_matches

    # 2. 同一住所・同一電話を共有する施設のみ、PDF近傍に園名があるか確認
    context = normalize_name(contact.get("context", ""))

    name_matches = []
    for facility in candidates:
        names = [facility.get("name", "")] + list(facility.get("aliases", []))

        for name in names:
            n = normalize_name(name)
            if not n:
                continue

            variants = {
                n,
                n.replace("(仮称)", ""),
                n.replace("認定", ""),
            }

            if any(v and v in context for v in variants):
                name_matches.append(facility)
                break

    # 重複除去
    unique = {}
    for facility in name_matches:
        unique[facility["id"]] = facility
    name_matches = list(unique.values())

    if len(name_matches) == 1:
        return name_matches[0], "context-name"

    return None, "ambiguous"


def match_contact(contact, indexes):
    phone = contact["phone"]
    postal = contact["postal"]

    exact = indexes["by_phone_postal"].get((phone, postal), [])

    if exact:
        facility, method = disambiguate_candidates(contact, exact)

        if facility:
            return {
                "facility": facility,
                "method": f"phone+postal+{method}",
                "ambiguous": False,
            }

        return {
            "facility": None,
            "method": "phone+postal-ambiguous",
            "ambiguous": True,
            "candidates": [x["name"] for x in exact],
        }

    # 電話番号が一意なら安全に救済。
    phone_matches = indexes["by_phone"].get(phone, [])

    if len(phone_matches) == 1:
        return {
            "facility": phone_matches[0],
            "method": "phone-only-unique",
            "ambiguous": False,
        }

    # 郵便番号が一意なら補助キーとして使用。
    postal_matches = indexes["by_postal"].get(postal, [])

    if len(postal_matches) == 1:
        return {
            "facility": postal_matches[0],
            "method": "postal-only-unique",
            "ambiguous": False,
        }

    # phone/postal単独候補が複数ある場合も、住所→園名で一意化を試す。
    union = {}
    for facility in phone_matches + postal_matches:
        union[facility["id"]] = facility

    if union:
        facility, method = disambiguate_candidates(contact, list(union.values()))

        if facility:
            return {
                "facility": facility,
                "method": f"rescued-{method}",
                "ambiguous": False,
            }

    return {
        "facility": None,
        "method": "none",
        "ambiguous": len(union) > 1,
        "candidates": [x["name"] for x in union.values()],
    }



def duplicate_contact_key(contact):
    """
    電話・郵便番号・所在地まで完全一致する行だけを同一キーにする。
    """
    return (
        contact.get("phone", ""),
        contact.get("postal", ""),
        normalize_locality(contact.get("locality", "")),
    )


def build_occurrence_resolution(contacts, indexes):
    """
    どんぐり保育園 / ノイエ保育園のように、
    電話・郵便番号・住所まで完全に共有する施設を
    PDF出現順と固定マスタ順で対応付ける。

    適用条件を厳しく限定:
    - 同一 contact key のPDF行が2件以上
    - 同じ phone+postal 候補が2件以上
    - 候補施設の住所もそのcontact localityと一致
    - PDF行数と候補施設数が完全一致

    これ以外には使わない。
    """
    groups = {}

    for idx, contact in enumerate(contacts):
        key = duplicate_contact_key(contact)
        groups.setdefault(key, []).append(idx)

    resolution = {}

    for key, contact_indexes in groups.items():
        if len(contact_indexes) < 2:
            continue

        phone, postal, locality = key

        candidates = indexes["by_phone_postal"].get(
            (phone, postal),
            [],
        )

        if len(candidates) < 2:
            continue

        address_candidates = []

        for facility in candidates:
            master_locality = normalize_locality(
                facility.get("address", "")
            )

            if master_locality == locality:
                address_candidates.append(facility)

        if len(address_candidates) != len(contact_indexes):
            continue

        address_candidates.sort(
            key=lambda f: indexes["master_order"].get(
                f["id"],
                10**9,
            )
        )

        for pdf_index, facility in zip(
            contact_indexes,
            address_candidates,
        ):
            resolution[pdf_index] = facility

    return resolution

def status_token(text):
    return STATUS_MAP.get(clean(text))


def extract_statuses_for_band(
    words,
    top,
    bottom,
    age_centers,
):
    """
    1施設の横一列（前後の電話行の中間）にある○△×を
    0～5歳ヘッダのx座標へ割り当てる。

    名前の抽出順や改称に一切依存しない。
    """
    result = {}

    for word in words:
        cy = (
            float(word["top"])
            + float(word["bottom"])
        ) / 2

        if not (top <= cy < bottom):
            continue

        st = status_token(str(word["text"]))
        if not st:
            continue

        cx = (
            float(word["x0"])
            + float(word["x1"])
        ) / 2

        age = min(
            age_centers,
            key=lambda a: abs(age_centers[a] - cx),
        )

        distance = abs(age_centers[age] - cx)

        if distance <= 28:
            result[str(age)] = st

    return result


def pdf_meta(pdf_bytes, title, page_text):
    result = {
        "availability_for": "",
        "availability_as_of": "",
    }

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(
                (pdf.pages[i].extract_text() or "")
                for i in range(min(2, len(pdf.pages)))
            )

        m = re.search(
            r"確認時点\s*([^\n]*?時点)",
            text,
        )
        if m:
            result["availability_as_of"] = clean(m.group(1))

        m = re.search(
            r"施設利用\s*開始月\s*([^\n]+)",
            text,
        )
        if m:
            result["availability_for"] = clean(m.group(1))

    except Exception:
        pass

    if not result["availability_for"]:
        m = re.search(
            r"令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月",
            title,
        )
        if m:
            result["availability_for"] = (
                f"令和{m.group(1)}年{m.group(2)}月"
            )

    if not result["availability_as_of"]:
        m = re.search(
            r"令和\s*[0-9０-９]+年\s*"
            r"[0-9０-９]+月\s*"
            r"[0-9０-９]+日\s*時点",
            page_text,
        )
        if m:
            result["availability_as_of"] = clean(m.group(0))

    return result


def parse_pdf(pdf_bytes, master):
    indexes = master_indexes(master)

    by_id = {}
    matched = {}
    unmatched_contacts = []
    ambiguous_contacts = []
    rescued_matches = []
    duplicate_ids = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            words = page.extract_words(
                use_text_flow=False,
                keep_blank_chars=False,
                x_tolerance=1.5,
                y_tolerance=2.0,
            ) or []

            rows = group_words_by_row(words)
            age_centers = find_age_centers(rows)

            if len(age_centers) < 4:
                raise RuntimeError(
                    f"{page_index + 1}ページ目で年齢列の位置を取得できません。"
                )

            contacts = collect_contact_rows(rows)

            if not contacts:
                raise RuntimeError(
                    f"{page_index + 1}ページ目で施設連絡先行を取得できません。"
                )

            # row top順
            contacts.sort(key=lambda x: x["top"])

            occurrence_resolution = build_occurrence_resolution(
                contacts,
                indexes,
            )

            page_matched = 0
            page_unmatched = 0
            page_status = 0

            for i, contact in enumerate(contacts):
                if i in occurrence_resolution:
                    forced = occurrence_resolution[i]
                    match = {
                        "facility": forced,
                        "method": "shared-contact-occurrence-order",
                        "ambiguous": False,
                    }
                else:
                    match = match_contact(
                        contact,
                        indexes,
                    )

                if match.get("ambiguous"):
                    ambiguous_contacts.append({
                        "page": page_index + 1,
                        "phone": contact["phone"],
                        "postal": contact["postal"],
                        "raw": contact["text"],
                        "locality": contact.get("locality", ""),
                        "context": contact.get("context", ""),
                        "candidates": match.get("candidates", []),
                    })
                    continue

                facility = match.get("facility")

                if not facility:
                    unmatched_contacts.append({
                        "page": page_index + 1,
                        "phone": contact["phone"],
                        "postal": contact["postal"],
                        "raw": contact["text"],
                        "locality": contact.get("locality", ""),
                        "context": contact.get("context", ""),
                    })
                    page_unmatched += 1
                    continue

                fid = facility["id"]

                if fid in matched:
                    duplicate_ids.append({
                        "facility_id": fid,
                        "name": facility["name"],
                        "first_page": matched[fid]["page"],
                        "second_page": page_index + 1,
                    })
                    continue

                # contact行は施設行の下段。
                # 前後contact行の中点で施設1行分の縦範囲を作る。
                current_y = contact["top"]

                if i == 0:
                    if len(contacts) > 1:
                        gap = contacts[1]["top"] - current_y
                    else:
                        gap = 24
                    band_top = current_y - max(18, gap * 0.75)
                else:
                    band_top = (
                        contacts[i - 1]["top"]
                        + current_y
                    ) / 2

                if i == len(contacts) - 1:
                    if i > 0:
                        gap = current_y - contacts[i - 1]["top"]
                    else:
                        gap = 24
                    band_bottom = current_y + max(10, gap * 0.45)
                else:
                    band_bottom = (
                        current_y
                        + contacts[i + 1]["top"]
                    ) / 2

                statuses = extract_statuses_for_band(
                    words,
                    band_top,
                    band_bottom,
                    age_centers,
                )

                by_id[fid] = statuses

                matched[fid] = {
                    "name": facility["name"],
                    "page": page_index + 1,
                    "method": match["method"],
                    "phone": contact["phone"],
                    "postal": contact["postal"],
                }

                if match["method"] != "phone+postal":
                    rescued_matches.append({
                        "facility_id": fid,
                        "name": facility["name"],
                        "method": match["method"],
                        "pdf_phone": contact["phone"],
                        "pdf_postal": contact["postal"],
                        "master_phone": normalize_phone(
                            facility.get("phone", "")
                        ),
                        "master_postal": normalize_postal(
                            facility.get("postal", "")
                        ),
                    })

                page_matched += 1

                if statuses:
                    page_status += 1

            print(
                f"[availability-v3.2] page "
                f"{page_index + 1}/{len(pdf.pages)} "
                f"contacts={len(contacts)} "
                f"matched={page_matched} "
                f"with_status={page_status} "
                f"unmatched={page_unmatched}"
            )

    return {
        "by_id": by_id,
        "matched": matched,
        "unmatched_contacts": unmatched_contacts,
        "ambiguous_contacts": ambiguous_contacts,
        "rescued_matches": rescued_matches,
        "duplicate_ids": duplicate_ids,
    }


def main():
    if not MASTER.exists():
        raise RuntimeError("data/facility_master.json がありません。")

    master = json.loads(
        MASTER.read_text(encoding="utf-8")
    )

    facilities = master.get("facilities", [])

    if len(facilities) != 206:
        raise RuntimeError(
            f"固定施設マスタが206施設ではありません: {len(facilities)}"
        )

    title, pdf_url, page_updated, page_text = latest_pdf()

    r = requests.get(
        pdf_url,
        headers={"User-Agent": UA},
        timeout=45,
    )
    r.raise_for_status()

    parsed = parse_pdf(
        r.content,
        master,
    )

    matched_count = len(parsed["matched"])
    with_status_count = sum(
        1 for v in parsed["by_id"].values()
        if v
    )

    all_ids = {
        f["id"]: f
        for f in facilities
    }

    master_not_in_pdf = [
        {
            "facility_id": fid,
            "name": facility["name"],
            "ward": facility.get("ward", ""),
        }
        for fid, facility in all_ids.items()
        if fid not in parsed["matched"]
    ]

    meta = pdf_meta(
        r.content,
        title,
        page_text,
    )

    digest = hashlib.sha256(r.content).hexdigest()

    audit = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source_pdf_url": pdf_url,
        "fixed_master_count": len(facilities),
        "matched_facility_count": matched_count,
        "with_status_count": with_status_count,
        "unmatched_contact_count": len(parsed["unmatched_contacts"]),
        "ambiguous_contact_count": len(parsed["ambiguous_contacts"]),
        "duplicate_count": len(parsed["duplicate_ids"]),
        "rescued_match_count": len(parsed["rescued_matches"]),
        "unmatched_contacts": parsed["unmatched_contacts"],
        "ambiguous_contacts": parsed["ambiguous_contacts"],
        "duplicate_matches": parsed["duplicate_ids"],
        "rescued_matches": parsed["rescued_matches"],
        "master_not_in_pdf": master_not_in_pdf,
    }

    # 失敗時にも原因をGitHubログだけでなくファイルで追えるよう先に書く。
    AUDIT.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    if parsed["unmatched_contacts"]:
        raise RuntimeError(
            "固定マスタに照合できない電話・郵便番号の施設が"
            f"{len(parsed['unmatched_contacts'])}件あります。"
            "新設・移転・電話変更の可能性があります。"
        )

    if parsed["ambiguous_contacts"]:
        raise RuntimeError(
            "電話・郵便番号から一意に決められない施設が"
            f"{len(parsed['ambiguous_contacts'])}件あります。"
        )

    if parsed["duplicate_ids"]:
        raise RuntimeError(
            "同じ固定施設へ複数行が照合されました: "
            f"{len(parsed['duplicate_ids'])}件"
        )

    # 最新PDFには固定マスタ206件すべてが必ず載るとは限らない。
    # PDFに実際に載っている連絡先行が全件マッチしていることを重視。
    if matched_count < 190:
        raise RuntimeError(
            f"照合施設数が少なすぎます: {matched_count}"
        )

    if with_status_count < 180:
        raise RuntimeError(
            f"受入記号を取得できた施設が少なすぎます: {with_status_count}"
        )

    payload = {
        "schema_version": 32,
        "matching_key": "official phone + postal + address; exact shared-contact duplicates resolved by PDF/master occurrence order",
        "generated_at": audit["generated_at"],
        "availability_for": meta["availability_for"],
        "availability_as_of": meta["availability_as_of"],
        "source_page_updated": page_updated,
        "source_pdf_title": title,
        "source_pdf_url": pdf_url,
        "source_pdf_sha256": digest,
        "fixed_master_count": len(facilities),
        "matched_facility_count": matched_count,
        "with_status_count": with_status_count,
        "master_not_in_pdf": master_not_in_pdf,
        "by_facility_id": parsed["by_id"],
    }

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "[availability-v3.2] SUCCESS "
        f"master=206 "
        f"matched={matched_count} "
        f"with_status={with_status_count} "
        f"master_not_in_pdf={len(master_not_in_pdf)} "
        f"rescued={len(parsed['rescued_matches'])}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"[availability-v3.2] ERROR: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
