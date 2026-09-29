#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
AVAILABILITY = ROOT / 'data' / 'availability_monthly.json'
OUT = ROOT / 'data' / 'midyear_admission.json'
SOURCE_PAGE = 'https://www.city.okayama.jp/kurashi/0000072787.html'
AVAILABILITY_PAGE = 'https://www.city.okayama.jp/kurashi/0000012977.html'
GUIDE_PAGE = 'https://www.city.okayama.jp/kurashi/0000013000.html'
UA = 'OkayamaKosodateNavi/midyear-admission-v1'
JST = timezone(timedelta(hours=9))


def clean(v):
    return re.sub(r'\s+', ' ', v or '').strip()


def z2h(s):
    return str(s).translate(str.maketrans('０１２３４５６７８９', '0123456789'))


def parse_reiwa_ym(text):
    text = z2h(clean(text))
    m = re.search(r'令和\s*(\d+)年\s*(\d+)月', text)
    if not m:
        return None
    return 2018 + int(m.group(1)), int(m.group(2))


def parse_jp_date(text):
    text = z2h(clean(text))
    m = re.search(r'令和\s*(\d+)年\s*(\d+)月\s*(\d+)日', text)
    if not m:
        return None
    y, mo, d = 2018 + int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f'{y:04d}-{mo:02d}-{d:02d}'


def deadline_from_official_table(html, target_y, target_m):
    soup = BeautifulSoup(html, 'html.parser')
    target_reiwa = target_y - 2018
    target_pat = re.compile(rf'令和\s*{target_reiwa}年\s*0?{target_m}月\s*入園')

    for tr in soup.find_all('tr'):
        cells = [clean(x.get_text(' ', strip=True)) for x in tr.find_all(['th', 'td'])]
        if len(cells) < 2:
            continue
        joined = ' '.join(cells)
        if target_pat.search(z2h(joined)):
            for cell in cells[1:]:
                iso = parse_jp_date(cell)
                if iso:
                    return iso, cell

    # HTML table structure changes can happen. Fall back to page text, but only
    # when the target-month label and a deadline date are adjacent.
    text = clean(soup.get_text(' ', strip=True))
    text = z2h(text)
    m = re.search(
        rf'令和\s*{target_reiwa}年\s*0?{target_m}月\s*入園.{{0,100}}?'
        r'(令和\s*\d+年\s*\d+月\s*\d+日(?:（[^）]+）)?)',
        text,
    )
    if m:
        iso = parse_jp_date(m.group(1))
        if iso:
            return iso, m.group(1)
    return None, None


def main():
    if not AVAILABILITY.exists():
        raise RuntimeError('availability_monthly.json がありません。先に受入見込み更新を実行してください。')

    availability = json.loads(AVAILABILITY.read_text(encoding='utf-8'))
    target_label = clean(availability.get('availability_for', ''))
    ym = parse_reiwa_ym(target_label)
    if not ym:
        raise RuntimeError(f'対象入園月を解釈できません: {target_label!r}')
    target_y, target_m = ym

    r = requests.get(SOURCE_PAGE, headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    if r.apparent_encoding:
        r.encoding = r.apparent_encoding

    deadline_iso, deadline_label = deadline_from_official_table(r.text, target_y, target_m)
    if not deadline_iso:
        raise RuntimeError(
            f'岡山市公式ページから {target_y}年{target_m}月入園の締切日を取得できません。'
            '誤った日付を公開しないため既存データを保持します。'
        )

    deadline_dt = datetime.strptime(deadline_iso + ' 17:15', '%Y-%m-%d %H:%M').replace(tzinfo=JST)
    publish_estimate = (deadline_dt - timedelta(days=7)).date().isoformat()

    payload = {
        'generated_at': datetime.now(JST).strftime('%Y-%m-%d %H:%M'),
        'target_year': target_y,
        'target_month': target_m,
        'target_label': target_label or f'{target_y}年{target_m}月',
        'deadline_date': deadline_iso,
        'deadline_time': '17:15',
        'deadline_label_official': deadline_label,
        'deadline_iso_jst': deadline_dt.isoformat(),
        'application_rule': '必要書類は入園希望月の前月1日（閉庁日の場合は翌開庁日）の17:15必着です。',
        'application_start_note': '年度途中の申込みは、利用希望月のおおむね4カ月前から受け付けられます。',
        'availability_publish_note': '年度途中の受入見込みは、申込締切日の1週間程度前から締切日まで岡山市ホームページで公開されます。',
        'availability_publish_estimate': publish_estimate,
        'availability_as_of': availability.get('availability_as_of', ''),
        'availability_source_pdf_title': availability.get('source_pdf_title', ''),
        'availability_source_pdf_url': availability.get('source_pdf_url', ''),
        'availability_source_sha256': availability.get('source_pdf_sha256', ''),
        'source_page_updated': availability.get('source_page_updated', ''),
        'sources': {
            'application': SOURCE_PAGE,
            'availability': AVAILABILITY_PAGE,
            'guide': GUIDE_PAGE,
        },
    }

    new_text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if OUT.exists() and OUT.read_text(encoding='utf-8') == new_text:
        print('[midyear-admission] unchanged')
        return
    OUT.write_text(new_text, encoding='utf-8')
    print(f'[midyear-admission] wrote {OUT}: {payload["target_label"]} deadline={deadline_iso} 17:15')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[midyear-admission] ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
