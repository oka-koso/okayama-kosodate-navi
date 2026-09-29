#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"

PUBLIC_NURSERY_PAGE = "https://www.city.okayama.jp/kurashi/0000030497.html"
PUBLIC_KODOMO_PAGE = "https://www.city.okayama.jp/kurashi/0000030473.html"

def main():
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    facilities = data.get("facilities", [])

    for f in facilities:
        # servicesは「未確認」と「なし」を区別するため、欠落時はnull。
        current = f.get("services") or {}
        f["services"] = {
            "extended": current.get("extended"),
            "temporary": current.get("temporary"),
            "holiday": current.get("holiday"),
            "support_center": current.get("support_center"),
        }

        if f.get("public_private") == "公立":
            # 公立園は独立HPではなく岡山市の一覧ページを案内。
            f["website"] = ""
            f["website_status"] = "none"

            if f.get("category") == "認定こども園":
                f["official_info_url"] = PUBLIC_KODOMO_PAGE
            else:
                f["official_info_url"] = PUBLIC_NURSERY_PAGE
        else:
            if f.get("website"):
                f["website_status"] = "verified"
            else:
                # 私立は「未調査」と「HPなし」を混同しない。
                f.setdefault("website_status", "unchecked")

            f.setdefault("official_info_url", "")

    data["schema_version"] = max(int(data.get("schema_version", 2)), 5)
    MASTER.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[links-v5] updated {len(facilities)} facilities")

if __name__ == "__main__":
    main()
