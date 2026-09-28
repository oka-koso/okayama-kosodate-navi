#!/usr/bin/env python3
"""岡山市公式の最新受入見込みPDFから施設情報を更新する。

安全策:
- 既存JSONを読み込み、解析結果が十分な件数に達しない場合は上書きしない。
- 制度説明ページは更新しない。
- PDFレイアウト変更時は失敗を明示して既存データを保持する。
"""
from __future__ import annotations
import io, json, re, sys
from pathlib import Path
from datetime import date
import requests
from bs4 import BeautifulSoup
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'facilities.json'
SOURCE_PAGE='https://www.city.okayama.jp/kurashi/0000012977.html'
UA='OkayamaKosodateNavi/1.0 (+non-commercial data refresh; contact via site)'

FAC_RE=re.compile(r'^(.*?)\s+(保|こ|小|事)\s+(公|私)\s+(.+)$')
PHONE_POST_RE=re.compile(r'(?:℡|TEL|Tel)?\s*([0-9]{3})[-－]([0-9]{3,4})[-－]([0-9]{4}).*?〒?\s*(\d{3})[-－](\d{4})\s+(.+)$')
TYPE_MAP={'保':'保育園','こ':'認定こども園','小':'地域型保育','事':'地域型保育'}

def get_latest_pdf():
    r=requests.get(SOURCE_PAGE,headers={'User-Agent':UA},timeout=30); r.raise_for_status()
    s=BeautifulSoup(r.text,'html.parser')
    candidates=[]
    for a in s.find_all('a',href=True):
        text=' '.join(a.stripped_strings)
        href=requests.compat.urljoin(SOURCE_PAGE,a['href'])
        if href.lower().endswith('.pdf') and '受入見込み' in text and ('認可保育園' in text or '認可' in text):
            candidates.append((text,href))
    if not candidates: raise RuntimeError('認可保育園の受入見込みPDFを発見できませんでした')
    return candidates[0]

def ward_for_page(i,n):
    # 現行7ページPDF: 北0-2 / 中3 / 東4 / 南5-6
    if n==7:
        return ['北区','北区','北区','中区','東区','南区','南区'][i]
    # レイアウト変更時の暫定推定。件数安全チェックにより誤解析時は保存しない。
    r=i/max(n-1,1)
    return '北区' if r<.43 else '中区' if r<.58 else '東区' if r<.73 else '南区'

def clean_name(s):
    return re.sub(r'\s+',' ',s).strip(' ■●◆')

def parse_pdf(content, old_by_name):
    out=[]
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for pi,page in enumerate(pdf.pages):
            ward=ward_for_page(pi,len(pdf.pages))
            text=page.extract_text(x_tolerance=2,y_tolerance=3) or ''
            lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines() if x.strip()]
            pending=None
            for line in lines:
                m=FAC_RE.match(line)
                if m:
                    name,typ,pub,operator=m.groups()
                    pending={'name':clean_name(name),'ward':ward,'type':TYPE_MAP.get(typ,'保育施設'),'public':pub=='公','operator':operator.strip()}
                    continue
                m=PHONE_POST_RE.search(line)
                if pending and m:
                    p1,p2,p3,z1,z2,addr=m.groups()
                    name=pending['name']
                    prev=old_by_name.get(name,{})
                    f={**pending,'phone':f'086-{p2}-{p3}' if p1=='086' else f'{p1}-{p2}-{p3}',
                       'postal':f'{z1}-{z2}','address':f'{ward}{addr.strip()}',
                       'services':prev.get('services',{'extended':False,'temporary':False}),
                       'availability':prev.get('availability',{}),'lat':prev.get('lat'),'lon':prev.get('lon')}
                    out.append(f); pending=None
    # de-duplicate by name+address
    uniq={}
    for f in out: uniq[(f['name'],f['address'])]=f
    return list(uniq.values())

def main():
    old=json.loads(DATA.read_text(encoding='utf-8'))
    old_by={x['name']:x for x in old.get('facilities',[])}
    title,url=get_latest_pdf()
    r=requests.get(url,headers={'User-Agent':UA},timeout=45); r.raise_for_status()
    facilities=parse_pdf(r.content,old_by)
    print(f'PDF: {title} / parsed={len(facilities)}')
    # 岡山市の認可施設は多数あるため、100件未満ならレイアウト解析失敗とみなす。
    if len(facilities)<100:
        raise RuntimeError(f'解析件数が少なすぎます ({len(facilities)}件)。既存JSONを保持します。')
    payload={
      'updated_at':date.today().isoformat(),
      'data_scope':'latest_official_acceptance_pdf',
      'availability_as_of':None,
      'source_pdf_title':title,'source_pdf_url':url,
      'sources':[SOURCE_PAGE,'https://www.city.okayama.jp/kurashi/0000013000.html'],
      'facilities':sorted(facilities,key=lambda x:(['北区','中区','東区','南区'].index(x['ward']),x['name']))
    }
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'[update_data] {e}',file=sys.stderr); sys.exit(1)
