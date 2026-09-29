#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'index.html'
if not p.exists(): raise RuntimeError('index.html not found')
s=p.read_text(encoding='utf-8')

if 'css/home-map.css' not in s:
    needle='<link rel="stylesheet" href="css/style.css">'
    if needle not in s: raise RuntimeError('style.css insertion point not found')
    s=s.replace(needle,needle+'<link rel="stylesheet" href="css/home-map.css"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">',1)

if 'js/home-map.js' not in s:
    needle='<script defer src="js/common.js"></script>'
    if needle not in s: raise RuntimeError('common.js insertion point not found')
    s=s.replace(needle,'<script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'+needle+'<script defer src="js/home-map.js"></script>',1)

map_section='<section class="home-map-section" aria-labelledby="home-map-title"><div class="container"><div class="section-head"><div><h2 id="home-map-title">地図から保育施設を探す</h2><p>岡山市内の認可保育施設を、場所から探せます。</p></div></div><div class="home-map-shell"><div class="home-map-toolbar"><div class="home-map-wards" aria-label="区で絞り込み"><button type="button" class="home-map-ward-btn active" data-home-map-ward="" aria-pressed="true">全域</button><button type="button" class="home-map-ward-btn" data-home-map-ward="北区" aria-pressed="false">北区</button><button type="button" class="home-map-ward-btn" data-home-map-ward="中区" aria-pressed="false">中区</button><button type="button" class="home-map-ward-btn" data-home-map-ward="東区" aria-pressed="false">東区</button><button type="button" class="home-map-ward-btn" data-home-map-ward="南区" aria-pressed="false">南区</button></div><div class="home-map-status"><span id="home-map-count">施設を読み込み中</span><span id="home-map-meta"></span></div></div><div id="home-map" class="home-map-canvas" aria-label="岡山市の保育施設マップ"></div><div class="home-map-footer"><p>ピンを押すと、施設情報と最新の年齢別受入見込みを確認できます。地図：© OpenStreetMap contributors</p><a class="home-map-all-link" href="hoikuen.html">検索・条件指定して詳しく見る →</a></div></div></div></section>'
if 'id="home-map"' not in s:
    anchor='<section><div class="container"><div class="section-head"><div><h2>区から保育園を探す</h2>'
    if anchor not in s: raise RuntimeError('home map insertion point not found')
    s=s.replace(anchor,map_section+anchor,1)

p.write_text(s,encoding='utf-8')
print('index.html: home map installed')
