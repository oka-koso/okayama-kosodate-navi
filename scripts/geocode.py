#!/usr/bin/env python3
import json,time,urllib.parse
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'data'/'facilities.json'
URL='https://msearch.gsi.go.jp/address-search/AddressSearch?q='
UA='OkayamaKosodateNavi/1.0'
d=json.loads(P.read_text(encoding='utf-8')); changed=0
for f in d.get('facilities',[]):
    if f.get('lat') and f.get('lon'): continue
    q='岡山市'+f['address']
    try:
        r=requests.get(URL+urllib.parse.quote(q),headers={'User-Agent':UA},timeout=15); r.raise_for_status(); a=r.json()
        if a:
            lon,lat=a[0]['geometry']['coordinates']; f['lat']=lat; f['lon']=lon; changed+=1
        time.sleep(.25)
    except Exception as e: print('geocode skip',f['name'],e)
if changed: P.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('geocoded',changed)
