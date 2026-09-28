#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "facility_master.json"
AVAIL = ROOT / "data" / "availability.json"
OUT = ROOT / "data" / "facilities.json"


def main():
    m = json.loads(MASTER.read_text(encoding="utf-8"))
    a = json.loads(AVAIL.read_text(encoding="utf-8"))
    by_id = a.get("by_facility_id", {})

    facilities = []
    for src in m.get("facilities", []):
        if not src.get("active", True):
            continue
        f = dict(src)
        f["availability"] = by_id.get(src["id"], {})
        facilities.append(f)

    ward_order = {"北区": 0, "中区": 1, "東区": 2, "南区": 3}
    facilities.sort(key=lambda x: (ward_order.get(x.get("ward"), 9), x.get("name", "")))

    out = {
        "schema_version": 5,
        "updated_at": a.get("updated_at"),
        "availability_for": a.get("availability_for"),
        "availability_as_of": a.get("availability_as_of"),
        "source_page_updated": a.get("source_page_updated"),
        "source_pdf_url": a.get("source_pdf_url"),
        "facility_count": len(facilities),
        "pdf_facility_count": a.get("pdf_facility_count"),
        "auto_added_facilities": a.get("auto_added_facilities", []),
        "facilities": facilities,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[build]", len(facilities), "facilities")


if __name__ == "__main__":
    main()
