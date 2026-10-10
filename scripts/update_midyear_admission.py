#!/usr/bin/env python3
"""Sync official monthly deadlines independently of availability/April PDFs."""
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
UA = 'OkayamaKosodateNavi/midyear-admission-v2'
JST = timezone(timedelta(hours=9))


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def z2h(value):
    return str(value).translate(str.maketrans('０１２３４５６７８９', '0123456789'))


def parse_reiwa_ym(text):
    match = re.search(r'令和\s*(\d+)年\s*(\d+)月', z2h(clean(text)))
    return (2018 + int(match[1]), int(match[2])) if match else None


def parse_jp_date(text):
    match = re.search(r'令和\s*(\d+)年\s*(\d+)月\s*(\d+)日', z2h(clean(text)))
    if not match:
        return None
    return datetime(2018 + int(match[1]), int(match[2]), int(match[3])).date().isoformat()


def parse_deadlines(html):
    """Use official rows, including holiday-adjusted dates; never infer April."""
    soup = BeautifulSoup(html, 'html.parser')
    rows = {}
    for tr in soup.find_all('tr'):
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['th', 'td'])]
        if len(cells) < 2 or '入園' not in cells[0]:
            continue
        ym = parse_reiwa_ym(cells[0])
        deadline = parse_jp_date(cells[1])
        if not ym or not deadline or ym[1] == 4:
            continue
        target_year, target_month = ym
        if not 1 <= target_month <= 12:
            raise ValueError('対象月が不正です')
        cutoff = datetime.fromisoformat(deadline).replace(hour=17, minute=15, tzinfo=JST)
        target_date = datetime(target_year, target_month, 1, tzinfo=JST)
        if cutoff >= target_date or (target_date - cutoff).days > 62:
            raise ValueError('対象月と締切日の対応が不正です')
        key = (target_year, target_month)
        row = {
            'target_year': target_year,
            'target_month': target_month,
            'target_label': f'令和{target_year - 2018}年{target_month}月',
            'deadline_date': deadline,
            'deadline_time': '17:15',
            'deadline_label_official': cells[1],
            'deadline_iso_jst': cutoff.isoformat(),
        }
        if key in rows and rows[key] != row:
            raise ValueError('同じ入園月に複数の締切があります')
        rows[key] = row
    if not rows:
        raise ValueError('公式ページから年度途中の締切一覧を取得できません')
    return sorted(rows.values(), key=lambda row: row['deadline_iso_jst'])


def next_deadline(rows, now):
    return next((row for row in rows if datetime.fromisoformat(row['deadline_iso_jst']) >= now), None)


def fetch_html(url):
    response = requests.get(url, headers={'User-Agent': UA}, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or 'utf-8'
    return response.text


def availability_publications(html):
    """Identify currently linked recognised-nursery PDFs by their stated month."""
    result = []
    for a in BeautifulSoup(html, 'html.parser').find_all('a', href=True):
        title = clean(a.get_text(' ', strip=True))
        url = requests.compat.urljoin(AVAILABILITY_PAGE, a['href'])
        ym = parse_reiwa_ym(title)
        if (ym and url.split('?', 1)[0].lower().endswith('.pdf')
                and '受入見込み' in title and '認可外' not in title
                and ('認可保育園' in title or 'ninka' in url.lower()) and '教育利用' not in title):
            result.append({'target_year': ym[0], 'target_month': ym[1], 'title': title, 'url': url})
    return result


def availability_publication_plans(html):
    """Read explicit monthly publication plans; do not infer from deadlines."""
    text = z2h(clean(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)))
    pattern = (r'(令和\s*\d+年\s*\d+月)\s*入園に関する受入見込み情報は[、,\s]*'
               r'(令和\s*\d+年\s*\d+月\s*\d+日)[^。]{0,30}公表(?:する)?予定')
    plans = []
    for match in re.finditer(pattern, text):
        ym, publish = parse_reiwa_ym(match[1]), parse_jp_date(match[2])
        if not ym or not publish or ym[1] == 4:
            continue
        target = datetime(ym[0], ym[1], 1).date()
        planned = datetime.fromisoformat(publish).date()
        if not 0 < (target - planned).days <= 62:
            raise ValueError('入園月と公表予定日の対応が不正です')
        plans.append({'target_year': ym[0], 'target_month': ym[1],
                      'publish_date': publish, 'source': AVAILABILITY_PAGE})
    return plans


def main():
    now = datetime.now(JST)
    checked = now.isoformat(timespec='seconds')
    previous = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    try:
        rows = parse_deadlines(fetch_html(SOURCE_PAGE))
        selected = next_deadline(rows, now)
        availability = json.loads(AVAILABILITY.read_text(encoding='utf-8')) if AVAILABILITY.exists() else {}
        # Availability publication status is separate from official deadline success.
        publication_status = 'verified'
        publications_checked = checked
        try:
            publication_html = fetch_html(AVAILABILITY_PAGE)
            publications = availability_publications(publication_html)
            plans = availability_publication_plans(publication_html)
        except Exception:
            publication_status = 'failed'
            publications_checked = previous.get('publications_checked_at', '')
            publications = previous.get('availability_publications', [])
            plans = previous.get('availability_publication_plans', [])
        payload = {
            'schema_version': 2,
            'generated_at': now.strftime('%Y-%m-%d %H:%M'),
            'checked_at': checked,
            'check_attempted_at': checked,
            'check_status': 'verified',
            'deadlines': rows,
            'application_rule': '必要書類は入園希望月の前月1日（閉庁日の場合は翌開庁日）の17:15必着です。',
            'application_start_note': '年度途中の申込みは、利用希望月のおおむね4カ月前から受け付けられます。',
            'availability_publish_note': '年度途中の受入見込みは、申込締切日の1週間程度前から締切日まで岡山市ホームページで公開されます。',
            'availability_for': availability.get('availability_for', ''),
            'availability_as_of': availability.get('availability_as_of', ''),
            'availability_source_pdf_title': availability.get('source_pdf_title', ''),
            'availability_source_pdf_url': availability.get('source_pdf_url', ''),
            'availability_source_sha256': availability.get('source_pdf_sha256', ''),
            'source_page_updated': availability.get('source_page_updated', ''),
            'availability_publications': publications,
            'availability_publication_plans': plans,
            'publications_checked_at': publications_checked,
            'publication_check_status': publication_status,
            'sources': {'application': SOURCE_PAGE, 'availability': AVAILABILITY_PAGE, 'guide': GUIDE_PAGE},
        }
        # Legacy scalar fields remain compatible, but select from the deadline table.
        if selected:
            payload.update(selected)
            payload['availability_publish_estimate'] = (
                datetime.fromisoformat(selected['deadline_date']) - timedelta(days=7)
            ).date().isoformat()
    except Exception:
        if previous:
            previous['check_status'] = 'failed'
            previous['check_attempted_at'] = checked
            OUT.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raise
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[midyear-admission] synced {len(rows)} official deadlines; next={selected["target_label"] if selected else "not-published"}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'[midyear-admission] ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
