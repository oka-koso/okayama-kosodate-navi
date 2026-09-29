#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'data' / 'facility_master.json'
NAME_MASTER = ROOT / 'data' / 'facility_name_master.json'
AUDIT = ROOT / 'data' / 'facility_master_repair_audit.json'
JST = timezone(timedelta(hours=9))
POSTAL_IN_ADDRESS = re.compile(r'〒\s*([0-9]{3})[-－ー]([0-9]{4})\s*')
POSTAL = re.compile(r'^[0-9]{3}-[0-9]{4}$')
AUTO_MARKER = 'auto_added_from_availability_pdf_v5_2'

def die(msg):
    raise RuntimeError(msg)

def main():
    if not MASTER.exists() or not NAME_MASTER.exists():
        die('facility_master.json または facility_name_master.json がありません。')
    current = json.loads(MASTER.read_text(encoding='utf-8'))
    names = json.loads(NAME_MASTER.read_text(encoding='utf-8'))
    canonical = names.get('facilities', [])
    if len(canonical) != 206:
        die(f'固定名マスターが206施設ではありません: {len(canonical)}')
    cur_rows = current.get('facilities', [])
    by_id = {}
    duplicate_ids = []
    for row in cur_rows:
        fid = row.get('id')
        if not fid:
            continue
        if fid in by_id:
            duplicate_ids.append(fid)
            continue
        by_id[fid] = row
    canonical_ids = [x['id'] for x in canonical]
    missing = [fid for fid in canonical_ids if fid not in by_id]
    if missing:
        die(f'固定206施設のIDが欠落しています: {len(missing)}件 {missing[:5]}')
    removed = [r for r in cur_rows if r.get('id') not in set(canonical_ids)]
    repaired_postal = []
    repaired_names = []
    out_rows = []
    for base in canonical:
        row = dict(by_id[base['id']])
        # Canonical identity must never be learned from the monthly availability PDF.
        for key in ('id','name','category','ward','source_pdf_page','verification'):
            if key in base:
                if row.get(key) != base.get(key) and key == 'name':
                    repaired_names.append({'id':base['id'],'from':row.get(key,''),'to':base.get(key,'')})
                row[key] = base[key]
        # The corrupted updater copied the phone suffix into postal while leaving
        # the real postal code embedded after 〒 in address. Recover only when
        # that explicit official-format marker is present; never guess a code.
        address = str(row.get('address') or '')
        m = POSTAL_IN_ADDRESS.search(address)
        if m:
            correct = f'{m.group(1)}-{m.group(2)}'
            if row.get('postal') != correct:
                repaired_postal.append({'id':base['id'],'name':base['name'],'from':row.get('postal',''),'to':correct})
            row['postal'] = correct
            address = POSTAL_IN_ADDRESS.sub('', address, count=1)
            address = re.sub(r'\s+', ' ', address).strip()
            row['address'] = address
        # Strip the known auto-add marker from canonical rows if somehow present.
        if row.get('review_status') == AUTO_MARKER:
            row.pop('review_status', None)
        out_rows.append(row)
    if len(out_rows) != 206:
        die(f'復旧後が206施設ではありません: {len(out_rows)}')
    bad_postal = [r for r in out_rows if r.get('postal') and not POSTAL.fullmatch(str(r['postal']))]
    if bad_postal:
        die(f'郵便番号形式が不正な施設が残っています: {len(bad_postal)}件')
    current['facilities'] = out_rows
    current['facility_count'] = 206
    current.pop('last_auto_added', None)
    current.pop('last_pdf_seen', None)
    current['repaired_at'] = datetime.now(JST).strftime('%Y-%m-%d %H:%M')
    current['repair_note'] = 'Restored to canonical 206 IDs; monthly availability PDF must not mutate facility master.'
    MASTER.write_text(json.dumps(current, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    audit = {
        'generated_at': current['repaired_at'],
        'before_array_count': len(cur_rows),
        'after_array_count': len(out_rows),
        'removed_noncanonical_count': len(removed),
        'removed_noncanonical': [{'id':r.get('id',''),'name':r.get('name',''),'review_status':r.get('review_status','')} for r in removed],
        'repaired_postal_count': len(repaired_postal),
        'repaired_postal': repaired_postal,
        'repaired_name_count': len(repaired_names),
        'repaired_names': repaired_names,
        'duplicate_id_count': len(duplicate_ids),
        'validation': 'PASS',
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f"[master-repair] PASS before={len(cur_rows)} after=206 removed={len(removed)} postal_repaired={len(repaired_postal)} names_repaired={len(repaired_names)}")

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'[master-repair] ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
