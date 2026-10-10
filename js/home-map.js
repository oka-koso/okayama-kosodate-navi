(() => {
  'use strict';
  const WARD_COLORS={'北区':'#2f80ed','中区':'#27ae60','東区':'#f2994a','南区':'#9b51e0'};
  let map, all=[], markers=[], activeWard='';
  let availabilityDatasets={}, activeAvailabilityKey='monthly', admissionGuide={};
  const esc=(v)=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');

  function wardIcon(ward){
    const color=WARD_COLORS[ward]||'#66736e';
    return L.divIcon({className:'ward-div-icon',html:`<span class="ward-pin" style="--pin-color:${color}" aria-hidden="true"></span>`,iconSize:[24,32],iconAnchor:[12,30],popupAnchor:[0,-28]});
  }

  function availabilityHtml(f){
    const a=f.availability||{};
    if(!Object.keys(a).length)return '<div class="home-map-no-status">受入見込み：情報なし</div>';
    const dataset=availabilityDatasets[activeAvailabilityKey]||{};
    return `<div class="home-map-popup-meta">${esc(dataset.availability_for||'対象月未確認')}入園／基準日：${esc(dataset.availability_as_of||'未確認')}${window.OKNAvailability.describe(dataset,activeAvailabilityKey,admissionGuide).closed?'／この月の受付終了':''}</div><div class="home-map-availability">${[0,1,2,3,4,5].map(age=>{
      const status=a[String(age)]??'—';
      const cls=status==='○'?'o':status==='△'?'d':status==='×'?'x':'';
      return `<span class="home-age-pill ${cls}">${age}歳<br><strong>${esc(status)}</strong></span>`;
    }).join('')}</div>`;
  }

  function popupHtml(f){
    const mode=encodeURIComponent(activeAvailabilityKey);
    return `<div class="home-map-popup"><strong>${esc(f.name)}</strong><div class="home-map-popup-meta">${esc(f.category||'')}・${esc(f.public_private||'')}・${esc(f.ward||'')}</div><div class="home-map-popup-address">${esc(f.address||'')}</div><div class="home-map-popup-label">年齢別の受入見込み</div>${availabilityHtml(f)}<a class="home-map-detail-link" href="hoikuen.html?availability=${mode}&ward=${encodeURIComponent(f.ward||'')}">${esc(f.ward||'岡山市')}の施設を詳しく見る →</a></div>`;
  }

  async function loadJson(url){
    const r=await fetch(`${url}?v=${Date.now()}`,{cache:'no-store'});
    if(!r.ok)throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  }

  async function loadJsonIfExists(url){
    try{return await loadJson(url);}catch(_){return null;}
  }

  function reiwaToGregorian(reiwaYear){
    const n=Number(String(reiwaYear||'').replace(/[^0-9]/g,''));
    return Number.isFinite(n)&&n>0?2018+n:null;
  }

  function aprilDatasetIsRelevant(dataset){
    if(!dataset||!dataset.by_facility_id||!Object.keys(dataset.by_facility_id).length)return false;
    const text=String(dataset.availability_for||'');
    const m=text.match(/令和\s*([0-9０-９]+)年\s*4月/);
    if(!m)return /4月/.test(text);
    const normalized=m[1].replace(/[０-９]/g,ch=>String.fromCharCode(ch.charCodeAt(0)-0xFEE0));
    const year=reiwaToGregorian(normalized);
    if(!year)return true;
    const now=new Date();
    const currentYear=now.getFullYear();
    const currentMonth=now.getMonth()+1;
    if(currentMonth>=9)return year===currentYear+1;
    if(currentMonth<=4)return year===currentYear;
    return false;
  }

  function availabilityLabel(key,dataset){
    if(key==='april')return dataset?.availability_for?`${dataset.availability_for}入園`:'4月入園';
    return dataset?.availability_for?`${dataset.availability_for}入園（途中入園）`:'途中入園';
  }

  function updateMeta(){
    const availability=availabilityDatasets[activeAvailabilityKey]||{};
    const state=window.OKNAvailability.describe(availability,activeAvailabilityKey,admissionGuide);
    const meta=document.getElementById('home-map-meta');
    if(meta)meta.textContent=state.title;
    window.OKNAvailability.render(document.getElementById('home-map-summary'),availability,activeAvailabilityKey,admissionGuide);
    const latest=document.getElementById('latest-availability');
    if(latest)latest.textContent=`${state.title}。${state.closed?'この月の受付終了。':''}${availability.availability_as_of||''}`;
  }

  function renderAvailabilitySwitcher(){
    const wrap=document.getElementById('home-map-availability-switcher');
    if(!wrap)return;
    const keys=['monthly'];
    if(availabilityDatasets.april)keys.push('april');
    wrap.hidden=keys.length<2;
    if(keys.length<2){wrap.innerHTML='';return;}
    wrap.innerHTML=`
      <div class="home-map-availability-switch-head">
        <strong>受入見込みを切り替える</strong>
        <span class="home-map-availability-switch-note">${activeAvailabilityKey==='april'?'4月入園（新年度）':'年度途中入園'}を表示中</span>
      </div>
      <div class="home-map-availability-switch-buttons" role="group" aria-label="受入見込みの種類">
        ${keys.map(key=>{
          const active=key===activeAvailabilityKey;
          return `<button type="button" class="home-map-availability-switch-btn ${active?'is-active':''}" data-home-availability-mode="${key}" aria-pressed="${active?'true':'false'}"><span>${esc(availabilityLabel(key,availabilityDatasets[key]))}</span><small>${key==='april'?'新年度の申込用':'途中入園の参考資料'}</small></button>`;
        }).join('')}
      </div>`;
  }

  function applyAvailabilityDataset(key){
    const dataset=availabilityDatasets[key];
    if(!dataset)return;
    activeAvailabilityKey=key;
    const byId=dataset.by_facility_id||{};
    all.forEach(f=>{f.availability=byId[f.id]||{};});
    updateMeta();
    renderAvailabilitySwitcher();
    render();
  }

  async function loadData(){
    const master=await loadJson('data/facility_master.json');

    admissionGuide=await loadJsonIfExists('data/midyear_admission.json')||{publication_check_status:'failed',check_status:'failed'};
    let monthly=null,monthlyLoadFailed=false;
    for(const path of ['data/availability_monthly.json','data/availability_fixed.json']){
      monthly=await loadJsonIfExists(path);
      if(monthly?.by_facility_id)break;
      if(path==='data/availability_monthly.json')monthlyLoadFailed=true;
    }
    if(!monthly)monthly={by_facility_id:{},availability_for:'',availability_as_of:''};

    monthly.display_load_failed=monthlyLoadFailed;
    const aprilRaw=await loadJsonIfExists('data/availability_april.json');

    availabilityDatasets={monthly};
    if(aprilDatasetIsRelevant(aprilRaw))availabilityDatasets.april=aprilRaw;

    // 4月入園データが公表されている期間は、トップでも4月入園を初期表示。
    activeAvailabilityKey=availabilityDatasets.april?'april':'monthly';
    const active=availabilityDatasets[activeAvailabilityKey];
    const byId=active.by_facility_id||{};

    all=(master.facilities||[])
      .filter(f=>Number.isFinite(Number(f.lat))&&Number.isFinite(Number(f.lon)))
      .map(f=>({...f,availability:byId[f.id]||{}}));

    updateMeta();
    renderAvailabilitySwitcher();
    setInterval(updateMeta,30000);
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
    document.addEventListener('click',event=>{
      const btn=event.target.closest('[data-home-availability-mode]');
      if(!btn)return;
      const mode=btn.dataset.homeAvailabilityMode;
      if(mode&&availabilityDatasets[mode]){
        event.preventDefault();
        applyAvailabilityDataset(mode);
      }
    });
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
