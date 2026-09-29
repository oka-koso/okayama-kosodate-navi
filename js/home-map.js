(() => {
  'use strict';
  const WARD_COLORS={'北区':'#2f80ed','中区':'#27ae60','東区':'#f2994a','南区':'#9b51e0'};
  let map, all=[], markers=[], activeWard='';
  const esc=(v)=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');

  function wardIcon(ward){
    const color=WARD_COLORS[ward]||'#66736e';
    return L.divIcon({className:'ward-div-icon',html:`<span class="ward-pin" style="--pin-color:${color}" aria-hidden="true"></span>`,iconSize:[24,32],iconAnchor:[12,30],popupAnchor:[0,-28]});
  }
  function availabilityHtml(f){
    const a=f.availability||{};
    if(!Object.keys(a).length)return '<div class="home-map-no-status">受入見込み：情報なし</div>';
    return `<div class="home-map-availability">${[0,1,2,3,4,5].map(age=>{
      const status=a[String(age)]??'—';
      const cls=status==='○'?'o':status==='△'?'d':status==='×'?'x':'';
      return `<span class="home-age-pill ${cls}">${age}歳<br><strong>${esc(status)}</strong></span>`;
    }).join('')}</div>`;
  }
  function popupHtml(f){
    return `<div class="home-map-popup"><strong>${esc(f.name)}</strong><div class="home-map-popup-meta">${esc(f.category||'')}・${esc(f.public_private||'')}・${esc(f.ward||'')}</div><div class="home-map-popup-address">${esc(f.address||'')}</div><div class="home-map-popup-label">年齢別の受入見込み</div>${availabilityHtml(f)}<a class="home-map-detail-link" href="hoikuen.html?ward=${encodeURIComponent(f.ward||'')}">${esc(f.ward||'岡山市')}の施設を詳しく見る →</a></div>`;
  }
  async function loadJson(url){
    const r=await fetch(`${url}?v=${Date.now()}`,{cache:'no-store'});
    if(!r.ok)throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  }
  async function loadData(){
    const master=await loadJson('data/facility_master.json');
    let availability={by_facility_id:{}};
    for(const path of ['data/availability_monthly.json','data/availability_fixed.json']){
      try{availability=await loadJson(path);if(availability?.by_facility_id)break;}catch(_){}
    }
    const byId=availability.by_facility_id||{};
    all=(master.facilities||[]).filter(f=>Number.isFinite(Number(f.lat))&&Number.isFinite(Number(f.lon))).map(f=>({...f,availability:byId[f.id]||{}}));
    const meta=document.getElementById('home-map-meta');
    if(meta){
      const parts=[];
      if(availability.availability_for)parts.push(`${availability.availability_for}入園`);
      if(availability.availability_as_of)parts.push(availability.availability_as_of);
      meta.textContent=parts.length?`受入見込み：${parts.join('・')}`:'受入見込み：岡山市の最新公表情報を掲載';
    }
  }
  function clearMarkers(){markers.forEach(m=>m.remove());markers=[];}
  function fit(fs){
    if(!fs.length)return;
    const bounds=L.latLngBounds(fs.map(f=>[Number(f.lat),Number(f.lon)]));
    map.fitBounds(bounds.pad(.035),{maxZoom:activeWard?13:11,animate:false});
  }
  function render(){
    const fs=activeWard?all.filter(f=>f.ward===activeWard):all;
    clearMarkers();
    fs.forEach(f=>{
      const marker=L.marker([Number(f.lat),Number(f.lon)],{icon:wardIcon(f.ward)}).addTo(map).bindPopup(popupHtml(f),{maxWidth:330});
      markers.push(marker);
    });
    const count=document.getElementById('home-map-count');
    if(count)count.textContent=`${fs.length}施設を表示中`;
    fit(fs);
    setTimeout(()=>map.invalidateSize(),80);
  }
  function setWard(ward){
    activeWard=ward;
    document.querySelectorAll('[data-home-map-ward]').forEach(btn=>{
      const selected=btn.dataset.homeMapWard===ward;
      btn.classList.toggle('active',selected);
      btn.setAttribute('aria-pressed',selected?'true':'false');
    });
    render();
  }
  function initMap(){
    map=L.map('home-map',{zoomControl:true,scrollWheelZoom:false}).setView([34.655,133.92],11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
    document.querySelectorAll('[data-home-map-ward]').forEach(btn=>btn.addEventListener('click',()=>setWard(btn.dataset.homeMapWard||'')));
  }
  async function init(){
    const mapEl=document.getElementById('home-map');
    if(!mapEl||!window.L)return;
    initMap();
    try{await loadData();render();}
    catch(error){
      console.error(error);
      mapEl.innerHTML='<div class="home-map-error">地図情報を読み込めませんでした。時間をおいて再読み込みしてください。</div>';
      const count=document.getElementById('home-map-count');if(count)count.textContent='';
    }
  }
  window.addEventListener('DOMContentLoaded',()=>{const wait=()=>window.L?init():setTimeout(wait,80);wait();});
})();
