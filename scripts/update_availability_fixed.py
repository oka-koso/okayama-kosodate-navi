#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
OUT = ROOT / "data" / "availability_fixed.json"
AUDIT = ROOT / "data" / "availability_fixed_audit.json"

SOURCE_PAGE = "https://www.city.okayama.jp/kurashi/0000012977.html"
UA = "OkayamaKosodateNavi/availability-fixed-v1"
JST = timezone(timedelta(hours=9))

STATUS_MAP = {"○": "○", "〇": "○", "△": "△", "×": "×"}
WARD_BY_7P = ["北区", "北区", "北区", "中区", "東区", "南区", "南区"]


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_name(value: str | None) -> str:
    value = clean(value)
    value = value.replace("　", "")
    value = value.replace("（", "(").replace("）", ")")
    value = value.replace("・", "")
    value = re.sub(r"\s+", "", value)
    return value


def normalized_variants(name: str, aliases=None):
    """
    PDF側の軽微な表記差だけを吸収する。
    あいまいな略称を勝手に作らない。
    """
    raw = [name] + list(aliases or [])
    result = set()

    for item in raw:
        n = normalize_name(item)
        if not n:
            continue

        result.add(n)

        # 「（仮称）」の有無だけは安全に吸収
        result.add(n.replace("(仮称)", ""))

        # PDFによって全角/半角括弧が違うケース
        result.add(
            n.replace("(", "").replace(")", "")
        )

    return {x for x in result if len(x) >= 2}


def ward_for_page(page_index: int, page_count: int) -> str:
    if page_count == 7:
        return WARD_BY_7P[page_index]

    # ページ数変更時の保険。通常は7ページ。
    ratio = page_index / max(page_count - 1, 1)
    if ratio < .43:
        return "北区"
    if ratio < .58:
        return "中区"
    if ratio < .73:
        return "東区"
    return "南区"


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
        href = requests.compat.urljoin(
            SOURCE_PAGE,
            a["href"],
        )
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
            candidates.append(
                (score, text or filename, href)
            )

    if not candidates:
        raise RuntimeError(
            "岡山市の最新『認可保育園等の受入見込み』PDFを発見できません。"
        )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    _, title, url = candidates[0]

    return title, url, page_updated, page_text


def group_words_by_row(words, tolerance=3.0):
    """
    文字のY座標から紙面上の横一列を復元。
    """
    words = sorted(
        words,
        key=lambda w: (
            float(w["top"]),
            float(w["x0"]),
        ),
    )

    rows = []

    for word in words:
        top = float(word["top"])

        if (
            not rows
            or abs(top - rows[-1]["top"]) > tolerance
        ):
            rows.append({
                "top": top,
                "words": [word],
            })
        else:
            rows[-1]["words"].append(word)

            count = len(rows[-1]["words"])

            rows[-1]["top"] = (
                rows[-1]["top"] * (count - 1)
                + top
            ) / count

    for row in rows:
        row["words"].sort(
            key=lambda w: float(w["x0"])
        )

    return rows


def row_text(row) -> str:
    return clean(
        " ".join(
            str(word["text"])
            for word in row["words"]
        )
    )


def block_text(rows, index, before=1, after=1):
    """
    園名と○△×が上下別行になっていても照合できるよう、
    近傍行を連結する。
    """
    lo = max(0, index - before)
    hi = min(len(rows), index + after + 1)

    return clean(
        " ".join(
            row_text(rows[i])
            for i in range(lo, hi)
        )
    )


def find_age_centers(rows):
    """
    0歳～5歳の見出し位置を取得。
    """
    age_centers = {}

    fullwidth = str.maketrans(
        "０１２３４５",
        "012345",
    )

    for row in rows:
        for word in row["words"]:
            text = clean(str(word["text"]))

            m = re.fullmatch(
                r"([0-5０-５])歳",
                text,
            )

            if not m:
                continue

            age = int(
                m.group(1).translate(fullwidth)
            )

            age_centers[age] = (
                float(word["x0"])
                + float(word["x1"])
            ) / 2

    return age_centers


def status_from_token(text):
    return STATUS_MAP.get(clean(text))


def extract_statuses(rows, index, age_centers):
    """
    施設名行の上下を含めて○△×を探し、
    0～5歳見出しのX座標に最近傍で割り当てる。
    """
    if len(age_centers) < 4:
        return {}

    base_top = rows[index]["top"]
    candidates = []

    for j in range(
        max(0, index - 2),
        min(len(rows), index + 3),
    ):
        if abs(rows[j]["top"] - base_top) > 15:
            continue

        for word in rows[j]["words"]:
            status = status_from_token(
                str(word["text"])
            )

            if not status:
                continue

            center = (
                float(word["x0"])
                + float(word["x1"])
            ) / 2

            candidates.append(
                (center, status)
            )

    result = {}

    for center, status in candidates:
        age = min(
            age_centers,
            key=lambda a: abs(
                age_centers[a] - center
            ),
        )

        distance = abs(
            age_centers[age] - center
        )

        # 備考欄等の記号を誤採用しない。
        if distance <= 30:
            result[str(age)] = status

    return result


def master_index(master):
    """
    区別の固定施設マスタ。
    """
    by_ward = {
        "北区": [],
        "中区": [],
        "東区": [],
        "南区": [],
    }

    for facility in master.get(
        "facilities",
        [],
    ):
        ward = facility.get("ward", "")

        if ward not in by_ward:
            continue

        variants = normalized_variants(
            facility.get("name", ""),
            facility.get("aliases", []),
        )

        by_ward[ward].append({
            "facility": facility,
            "variants": variants,
        })

    return by_ward


def best_facility_match(text, candidates):
    """
    固定マスタ名をPDF近傍テキストから探す。

    優先順位:
      1. 正規化名の完全包含
      2. 仮称除去等の安全なvariant包含
      3. 高い文字列類似度（監査対象）
    """
    nt = normalize_name(text)

    exact = []

    for candidate in candidates:
        facility = candidate["facility"]

        for variant in candidate["variants"]:
            if variant and variant in nt:
                exact.append(
                    (
                        len(variant),
                        facility,
                        variant,
                        "substring",
                        1.0,
                    )
                )

    if exact:
        exact.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best = exact[0]

        # 同じ最長文字数の別施設があれば曖昧。
        ties = [
            x for x in exact
            if x[0] == best[0]
            and x[1]["id"] != best[1]["id"]
        ]

        if ties:
            return {
                "facility": None,
                "ambiguous": True,
                "candidates": [
                    best[1]["name"]
                ] + [
                    x[1]["name"]
                    for x in ties
                ],
                "method": "ambiguous_substring",
                "score": 1.0,
            }

        return {
            "facility": best[1],
            "ambiguous": False,
            "method": best[3],
            "score": best[4],
            "variant": best[2],
        }

    # 完全包含で拾えない特殊ケースのみ。
    # 閾値を高くして、曖昧一致はauditへ残す。
    best_facility = None
    best_score = 0.0

    for candidate in candidates:
        facility = candidate["facility"]

        for variant in candidate["variants"]:
            if len(variant) < 4:
                continue

            # 行全体ではなく、短いwindow単位で比較
            # textに他列が多く混ざるため。
            if len(nt) < len(variant):
                score = SequenceMatcher(
                    None,
                    variant,
                    nt,
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_facility = facility

                continue

            size = len(variant)

            for start in range(
                0,
                max(1, len(nt) - size + 1),
            ):
                piece = nt[start:start + size]

                score = SequenceMatcher(
                    None,
                    variant,
                    piece,
                ).ratio()

                if score > best_score:
                    best_score = score
                    best_facility = facility

    if best_facility and best_score >= 0.96:
        return {
            "facility": best_facility,
            "ambiguous": False,
            "method": "high_similarity",
            "score": round(
                best_score,
                4,
            ),
        }

    return {
        "facility": None,
        "ambiguous": False,
        "method": "none",
        "score": round(
            best_score,
            4,
        ),
    }


def candidate_status_row(rows, index):
    """
    受入施設行かどうかの目安。
    近傍に○△×が2つ以上あれば施設行候補とみなす。
    """
    count = 0
    base_top = rows[index]["top"]

    for j in range(
        max(0, index - 1),
        min(len(rows), index + 2),
    ):
        if abs(rows[j]["top"] - base_top) > 10:
            continue

        for word in rows[j]["words"]:
            if status_from_token(
                str(word["text"])
            ):
                count += 1

    return count >= 2


def pdf_meta(pdf_bytes, title, page_text):
    result = {
        "availability_for": "",
        "availability_as_of": "",
    }

    try:
        with pdfplumber.open(
            io.BytesIO(pdf_bytes)
        ) as pdf:
            text = "\n".join(
                (pdf.pages[i].extract_text() or "")
                for i in range(
                    min(
                        2,
                        len(pdf.pages),
                    )
                )
            )

        m = re.search(
            r"確認時点\s*([^\n]*?時点)",
            text,
        )

        if m:
            result["availability_as_of"] = clean(
                m.group(1)
            )

        m = re.search(
            r"施設利用\s*開始月\s*([^\n]+)",
            text,
        )

        if m:
            result["availability_for"] = clean(
                m.group(1)
            )

    except Exception:
        pass

    if not result["availability_for"]:
        m = re.search(
            r"令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月",
            title,
        )

        if m:
            result["availability_for"] = (
                f"令和{m.group(1)}年"
                f"{m.group(2)}月"
            )

    if not result["availability_as_of"]:
        m = re.search(
            r"令和\s*[0-9０-９]+年\s*"
            r"[0-9０-９]+月\s*"
            r"[0-9０-９]+日\s*時点",
            page_text,
        )

        if m:
            result["availability_as_of"] = clean(
                m.group(0)
            )

    return result


def parse_pdf(pdf_bytes, master):
    index = master_index(master)

    by_id = {}
    matched = {}
    ambiguous = []
    unknown_rows = []
    fuzzy_matches = []
    duplicate_rows = []

    with pdfplumber.open(
        io.BytesIO(pdf_bytes)
    ) as pdf:
        for page_index, page in enumerate(
            pdf.pages
        ):
            ward = ward_for_page(
                page_index,
                len(pdf.pages),
            )

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
                    f"PDF {page_index + 1}ページ目で"
                    "0～5歳欄の位置を十分に取得できませんでした。"
                )

            page_seen = set()
            page_matched = 0
            page_unknown = 0

            for i, row in enumerate(rows):
                text = block_text(
                    rows,
                    i,
                    before=1,
                    after=1,
                )

                match = best_facility_match(
                    text,
                    index[ward],
                )

                if match.get("ambiguous"):
                    if candidate_status_row(
                        rows,
                        i,
                    ):
                        ambiguous.append({
                            "page": page_index + 1,
                            "ward": ward,
                            "raw": text,
                            "candidates": match[
                                "candidates"
                            ],
                        })

                    continue

                facility = match.get("facility")

                if not facility:
                    if candidate_status_row(
                        rows,
                        i,
                    ):
                        unknown_rows.append({
                            "page": page_index + 1,
                            "ward": ward,
                            "raw": text,
                            "best_similarity": match[
                                "score"
                            ],
                        })
                        page_unknown += 1

                    continue

                fid = facility["id"]

                # 同一施設を近傍行で複数回拾うので、
                # ページ内では最も情報量の多い受入結果を採用。
                statuses = extract_statuses(
                    rows,
                    i,
                    age_centers,
                )

                existing = by_id.get(fid, {})

                if len(statuses) > len(existing):
                    by_id[fid] = statuses

                if fid not in page_seen:
                    page_seen.add(fid)
                    page_matched += 1

                if match["method"] == "high_similarity":
                    fuzzy_matches.append({
                        "page": page_index + 1,
                        "pdf_text": text,
                        "facility_id": fid,
                        "facility_name": facility[
                            "name"
                        ],
                        "score": match["score"],
                    })

            for fid in page_seen:
                if fid in matched:
                    duplicate_rows.append({
                        "facility_id": fid,
                        "facility_name": matched[
                            fid
                        ]["name"],
                        "first_page": matched[
                            fid
                        ]["page"],
                        "second_page": page_index + 1,
                    })
                else:
                    facility = next(
                        x["facility"]
                        for x in index[ward]
                        if x["facility"]["id"] == fid
                    )

                    matched[fid] = {
                        "name": facility["name"],
                        "ward": ward,
                        "page": page_index + 1,
                    }

            print(
                f"[availability] page "
                f"{page_index + 1}/{len(pdf.pages)} "
                f"ward={ward} "
                f"matched={page_matched} "
                f"unknown_status_rows={page_unknown}"
            )

    return {
        "by_id": by_id,
        "matched": matched,
        "ambiguous": ambiguous,
        "unknown_rows": unknown_rows,
        "fuzzy_matches": fuzzy_matches,
        "duplicate_rows": duplicate_rows,
    }


def main():
    if not MASTER.exists():
        raise RuntimeError(
            "data/facility_master.json がありません。"
        )

    master = json.loads(
        MASTER.read_text(
            encoding="utf-8"
        )
    )

    facilities = master.get(
        "facilities",
        [],
    )

    if len(facilities) != 206:
        raise RuntimeError(
            f"固定施設マスタが206施設ではありません: "
            f"{len(facilities)}"
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

    matched_count = len(
        parsed["matched"]
    )

    with_status_count = sum(
        1
        for statuses in parsed["by_id"].values()
        if statuses
    )

    # 重要:
    # 「知らない受入行」が残るなら、新施設または表記変更の可能性がある。
    # その場合は自動公開しない。
    if parsed["unknown_rows"]:
        raise RuntimeError(
            "固定206施設マスタに照合できない受入行が"
            f"{len(parsed['unknown_rows'])}件あります。"
            " 新設園・改称・PDF表記変更を確認してください。"
        )

    if parsed["ambiguous"]:
        raise RuntimeError(
            "複数施設に一致する曖昧な受入行が"
            f"{len(parsed['ambiguous'])}件あります。"
        )

    if parsed["duplicate_rows"]:
        raise RuntimeError(
            "複数ページに重複照合された施設が"
            f"{len(parsed['duplicate_rows'])}件あります。"
        )

    # 現在のPDFは全認可施設を掲載する前提だが、
    # 将来の資料仕様変更も考え、最低190施設を要求。
    if matched_count < 190:
        raise RuntimeError(
            f"PDFから固定マスタへ照合できた施設が"
            f"{matched_count}件しかありません。"
        )

    # ○△×が取れた施設も最低180施設を要求。
    if with_status_count < 180:
        raise RuntimeError(
            f"年齢別受入記号を取得できた施設が"
            f"{with_status_count}件しかありません。"
        )

    meta = pdf_meta(
        r.content,
        title,
        page_text,
    )

    all_ids = {
        f["id"]: f
        for f in facilities
    }

    master_not_in_pdf = [
        {
            "facility_id": fid,
            "name": facility["name"],
            "ward": facility["ward"],
        }
        for fid, facility in all_ids.items()
        if fid not in parsed["matched"]
    ]

    digest = hashlib.sha256(
        r.content
    ).hexdigest()

    payload = {
        "schema_version": 1,
        "source": "Okayama City official childcare availability PDF",
        "generated_at": datetime.now(
            JST
        ).strftime("%Y-%m-%d %H:%M"),
        "availability_for": meta[
            "availability_for"
        ],
        "availability_as_of": meta[
            "availability_as_of"
        ],
        "source_page_updated": page_updated,
        "source_pdf_title": title,
        "source_pdf_url": pdf_url,
        "source_pdf_sha256": digest,
        "fixed_master_count": len(
            facilities
        ),
        "matched_facility_count": matched_count,
        "with_status_count": with_status_count,
        "master_not_in_pdf": master_not_in_pdf,
        "by_facility_id": parsed["by_id"],
    }

    audit = {
        "generated_at": payload[
            "generated_at"
        ],
        "source_pdf_url": pdf_url,
        "fixed_master_count": len(
            facilities
        ),
        "matched_facility_count": matched_count,
        "with_status_count": with_status_count,
        "master_not_in_pdf": master_not_in_pdf,
        "high_similarity_matches": parsed[
            "fuzzy_matches"
        ],
        "unknown_status_rows": parsed[
            "unknown_rows"
        ],
        "ambiguous_rows": parsed[
            "ambiguous"
        ],
        "duplicate_matches": parsed[
            "duplicate_rows"
        ],
    }

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    AUDIT.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "[availability] SUCCESS "
        f"master={len(facilities)} "
        f"matched={matched_count} "
        f"with_status={with_status_count} "
        f"master_not_in_pdf={len(master_not_in_pdf)} "
        f"fuzzy={len(parsed['fuzzy_matches'])}"
    )

    if master_not_in_pdf:
        print(
            "[availability] master not in latest PDF:",
            " / ".join(
                x["name"]
                for x in master_not_in_pdf
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # auditが生成できる箇所まで進んでいなくても、
        # ログで原因を明確にする。
        print(
            f"[availability] ERROR: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
