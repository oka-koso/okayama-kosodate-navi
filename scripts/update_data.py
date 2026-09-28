#!/usr/bin/env python3
"""岡山市公式の「保育・幼児教育施設の受入見込み情報」を確認し、
最新の認可保育施設PDFが更新されたときに施設データを更新する。

方針:
- 岡山市の受入見込みページを定期確認し、最新PDFを自動取得する。
- PDFから施設名・種別・設置区分・電話・所在地を抽出する。
- 年齢別の○/△/×はPDF上の位置情報を利用して可能な範囲で抽出する。
- 解析件数が少ない場合は既存データを壊さない。
- 制度解説の文章はこのスクリプトでは書き換えない。
"""
from __future__ import annotations
import io, json, re, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'facilities.json'
SOURCE_PAGE = 'https://www.city.okayama.jp/kurashi/0000012977.html'
UA = 'OkayamaKosodateNavi/1.1 (official-data refresh)'
JST = timezone(timedelta(hours=9))

FAC_RE = re.compile(r'^(.*?)\s+(保|こ|小|事)\s+(公|私)\s+(.+)$')
# PDFでは市外局番086が省略され、"℡ 222-7583" のように出ることがある。
PHONE_POST_RE = re.compile(
    r'(?:℡|TEL|Tel)?\s*(?:(086)[-－])?([0-9]{3,4})[-－]([0-9]{4})'
    r'.*?〒?\s*(\d{3})[-－](\d{4})\s+(.+)$'
)
TYPE_MAP = {'保': '保育園', 'こ': '認定こども園', '小': '地域型保育', '事': '地域型保育'}
WARD_BY_7P = ['北区', '北区', '北区', '中区', '東区', '南区', '南区']
STATUS_MAP = {'〇': '○', '○': '○', '△': '△', '×': '×'}


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()


def get_latest_pdf():
    r = requests.get(SOURCE_PAGE, headers={'User-Agent': UA}, timeout=30)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, 'html.parser')
    page_text = normalize(soup.get_text(' ', strip=True))

    # 岡山市ページ自体の更新日
    page_updated = None
    m = re.search(r'\[(\d{4})年(\d{1,2})月(\d{1,2})日\]', soup.get_text('\n', strip=True))
    if m:
        page_updated = f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    candidates = []
    for a in soup.find_all('a', href=True):
        text = normalize(' '.join(a.stripped_strings))
        href = requests.compat.urljoin(SOURCE_PAGE, a['href'])
        if href.lower().endswith('.pdf') and '受入見込み' in text and ('認可保育園' in text or '認可' in text):
            candidates.append((text, href))
    if not candidates:
        raise RuntimeError('認可保育園等の受入見込みPDFを発見できませんでした')

    # ページ上の「令和8年9月17日現在」のような基準日
    as_of_text = None
    m = re.search(r'こちらの表をご覧ください。?（([^）]*?現在)）', page_text)
    if m:
        as_of_text = m.group(1)

    return candidates[0][0], candidates[0][1], page_updated, as_of_text


def ward_for_page(i: int, n: int) -> str:
    if n == 7:
        return WARD_BY_7P[i]
    r = i / max(n - 1, 1)
    return '北区' if r < .43 else '中区' if r < .58 else '東区' if r < .73 else '南区'


def clean_name(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip(' ■●◆')


def find_age_columns(page):
    """年齢列の中心X座標を取得。取得できない場合は空dict。"""
    cols = {}
    # 全角・半角の両方を試す
    for age in range(6):
        for label in (f'{age}歳', f'{str(age).translate(str.maketrans("0123456789", "０１２３４５６７８９"))}歳'):
            try:
                hits = page.search(label) or []
            except Exception:
                hits = []
            # 右側の表ヘッダにあるものを優先
            hits = [h for h in hits if h.get('x0', 0) > page.width * .45]
            if hits:
                h = sorted(hits, key=lambda x: x.get('top', 9999))[0]
                cols[age] = (h['x0'] + h['x1']) / 2
                break
    return cols


def extract_statuses(page, facility_name: str, age_cols: dict[int, float]):
    if len(age_cols) < 4:
        return {}
    try:
        hits = page.search(re.escape(facility_name), regex=True) or []
    except Exception:
        hits = []
    if not hits:
        # PDFで空白が混入する園名への簡易フォールバック
        key = facility_name.replace(' ', '')
        words = page.extract_words() or []
        hit_words = [w for w in words if key and key in (w.get('text', '').replace(' ', ''))]
        if not hit_words:
            return {}
        top = hit_words[0]['top']
    else:
        top = hits[0]['top']

    words = page.extract_words(x_tolerance=2, y_tolerance=3) or []
    symbols = []
    for w in words:
        t = normalize(w.get('text', ''))
        if t in STATUS_MAP and abs(w.get('top', 9999) - top) <= 9:
            symbols.append(((w['x0'] + w['x1']) / 2, STATUS_MAP[t]))
    if not symbols:
        return {}

    out = {}
    # 各シンボルを最も近い年齢列へ割り当てる。距離が大きすぎるものは除外。
    xs = sorted(age_cols.values())
    typical_gap = min([b-a for a,b in zip(xs, xs[1:]) if b-a > 0] or [40])
    for x, st in symbols:
        age, cx = min(age_cols.items(), key=lambda kv: abs(kv[1] - x))
        if abs(cx - x) <= max(typical_gap * .48, 16):
            out[str(age)] = st
    return out


def parse_pdf(content: bytes, old_by_name: dict):
    out = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pi, page in enumerate(pdf.pages):
            ward = ward_for_page(pi, len(pdf.pages))
            age_cols = find_age_columns(page)
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ''
            lines = [normalize(x) for x in text.splitlines() if normalize(x)]
            pending = None
            for line in lines:
                m = FAC_RE.match(line)
                if m:
                    name, typ, pub, operator = m.groups()
                    pending = {
                        'name': clean_name(name), 'ward': ward,
                        'type': TYPE_MAP.get(typ, '保育施設'),
                        'public': pub == '公', 'operator': operator.strip()
                    }
                    continue

                m = PHONE_POST_RE.search(line)
                if pending and m:
                    area, p2, p3, z1, z2, addr = m.groups()
                    name = pending['name']
                    prev = old_by_name.get(name, {})
                    phone = f'{area or "086"}-{p2}-{p3}'
                    status = extract_statuses(page, name, age_cols)
                    f = {
                        **pending,
                        'phone': phone,
                        'postal': f'{z1}-{z2}',
                        'address': f'{ward}{addr.strip()}',
                        # 公立一覧等で確認済みのサービス情報があれば維持
                        'services': prev.get('services', {'extended': False, 'temporary': False}),
                        'availability': status or prev.get('availability', {}),
                        'lat': prev.get('lat'), 'lon': prev.get('lon')
                    }
                    out.append(f)
                    pending = None

    uniq = {}
    for f in out:
        uniq[(f['name'], f['address'])] = f
    return list(uniq.values())


def extract_pdf_meta(content: bytes, title: str):
    meta = {'availability_as_of': None, 'availability_for': None}
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            first = pdf.pages[0].extract_text() or ''
        m = re.search(r'確認時点\s*([^\n]+?時点)', first)
        if m:
            meta['availability_as_of'] = normalize(m.group(1))
        m = re.search(r'施設利用\s*開始月\s*([^\n]+)', first)
        if m:
            meta['availability_for'] = normalize(m.group(1))
    except Exception:
        pass
    if not meta['availability_for']:
        m = re.search(r'令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月', title)
        if m:
            meta['availability_for'] = f'令和{m.group(1)}年{m.group(2)}月'
    return meta


def main():
    old = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {'facilities': []}
    old_by = {x['name']: x for x in old.get('facilities', [])}

    title, url, source_page_updated, page_as_of = get_latest_pdf()
    r = requests.get(url, headers={'User-Agent': UA}, timeout=45)
    r.raise_for_status()
    digest = hashlib.sha256(r.content).hexdigest()

    # 同じPDFなら、サイト側の「確認日時」だけを無意味に更新しない。
    if old.get('source_pdf_sha256') == digest and len(old.get('facilities', [])) >= 100:
        print('Official PDF unchanged; no data update needed.')
        return

    facilities = parse_pdf(r.content, old_by)
    print(f'PDF: {title} / parsed={len(facilities)}')
    if len(facilities) < 100:
        raise RuntimeError(f'解析件数が少なすぎます ({len(facilities)}件)。既存JSONを保持します。')

    meta = extract_pdf_meta(r.content, title)
    payload = {
        'updated_at': datetime.now(JST).strftime('%Y-%m-%d %H:%M'),
        'source_page_updated': source_page_updated,
        'data_scope': '岡山市公表の最新「認可保育園等の受入見込み」掲載施設',
        'availability_as_of': meta['availability_as_of'] or page_as_of,
        'availability_for': meta['availability_for'],
        'source_pdf_title': title,
        'source_pdf_url': url,
        'source_pdf_sha256': digest,
        'sources': [SOURCE_PAGE, 'https://www.city.okayama.jp/kurashi/0000013000.html'],
        'facilities': sorted(
            facilities,
            key=lambda x: (['北区', '中区', '東区', '南区'].index(x['ward']), x['name'])
        )
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'[update_data] {e}', file=sys.stderr)
        sys.exit(1)
