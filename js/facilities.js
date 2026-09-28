let allFacilities = [];
let map;
let markers = [];

const $ = (selector) => document.querySelector(selector);

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function safeId(value) {
  return String(value || '')
    .replace(/[^a-zA-Z0-9_-]/g, '-');
}

function cardId(facility) {
  return `facility-${safeId(facility.id || facility.name)}`;
}

function focusFacility(id) {
  const card = document.getElementById(id);
  if (!card) return;

  card.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });

  card.classList.remove('facility-highlight');
  void card.offsetWidth;
  card.classList.add('facility-highlight');

  window.setTimeout(() => {
    card.classList.remove('facility-highlight');
  }, 2200);
}

window.focusFacility = focusFacility;

function availabilityHtml(facility, compact = false) {
  const a = facility.availability || {};

  if (!Object.keys(a).length) {
    return '<p class="availability-none">受入見込み：公表なし</p>';
  }

  return `
    <div class="availability ${compact ? 'availability-popup' : ''}">
      ${[0,1,2,3,4,5].map((age) => {
        const status = a[String(age)] ?? a[age] ?? '—';
        let cls = '';
        if (status === '○') cls = 'o';
        if (status === '△') cls = 'd';
        if (status === '×') cls = 'x';

        return `
          <span class="age-pill ${cls}" title="${age}歳：${esc(status)}">
            ${age}歳<br>${esc(status)}
          </span>
        `;
      }).join('')}
    </div>
  `;
}

function siteButton(facility, compact = false) {
  if (!facility.website) return '';

  return `
    <a class="${compact ? 'popup-site-link' : 'facility-site-link'}"
       href="${esc(facility.website)}"
       target="_blank"
       rel="noopener noreferrer">
      施設のホームページを見る ↗
    </a>
  `;
}

function init() {
  map = L.map('map').setView([34.655, 133.92], 11);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  fetch(`data/facilities.json?v=${Date.now()}`, { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error(`facilities.json: HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      allFacilities = Array.isArray(data.facilities) ? data.facilities : [];

      const meta = [];
      if (data.availability_for) meta.push(`${data.availability_for}入園`);
      if (data.availability_as_of) meta.push(data.availability_as_of);
      if (data.source_page_updated) meta.push(`岡山市ページ更新 ${data.source_page_updated}`);
      if (data.facility_count) meta.push(`掲載 ${data.facility_count}施設`);

      if ($('#updated')) $('#updated').textContent = meta.join('｜');

      applyQueryParams();
      render();
      setTimeout(() => map.invalidateSize(), 100);
    })
    .catch((error) => {
      console.error(error);
      if ($('#count')) $('#count').textContent = '0';
      if ($('#facility-list')) {
        $('#facility-list').innerHTML = `
          <div class="notice">
            <strong>施設情報を読み込めませんでした。</strong><br>
            時間をおいて再読み込みしてください。
          </div>
        `;
      }
    });

  ['q', 'ward', 'type', 'service'].forEach((id) => {
    const el = $('#' + id);
    if (!el) return;
    el.addEventListener(id === 'q' ? 'input' : 'change', render);
  });
}

function applyQueryParams() {
  const p = new URLSearchParams(location.search);
  if (p.get('ward') && $('#ward')) $('#ward').value = p.get('ward');
}

function filterData() {
  const q = ($('#q')?.value || '').trim().toLowerCase();
  const ward = $('#ward')?.value || '';
  const type = $('#type')?.value || '';
  const service = $('#service')?.value || '';

  return allFacilities.filter((f) => {
    const searchable =
      `${f.name || ''} ${(f.aliases || []).join(' ')} ${f.address || ''} ${f.operator || ''}`
        .toLowerCase();

    return (
      (!q || searchable.includes(q)) &&
      (!ward || f.ward === ward) &&
      (!type || f.type === type) &&
      (!service || Boolean(f.services?.[service]))
    );
  });
}

function popupHtml(f) {
  const id = cardId(f);

  return `
    <div class="facility-popup">
      <button class="map-facility-link"
              type="button"
              onclick="focusFacility('${id}')">
        ${esc(f.name || '')}
      </button>

      <div class="popup-meta">
        ${esc(f.type || '')}${f.type ? '・' : ''}${f.public ? '公立' : '私立等'}
      </div>

      <div class="popup-address">${esc(f.address || '所在地情報なし')}</div>

      ${f.phone ? `
        <div><a href="tel:${String(f.phone).replace(/-/g, '')}">
          ${esc(f.phone)}
        </a></div>` : ''}

      ${availabilityHtml(f, true)}

      <button class="popup-card-link"
              type="button"
              onclick="focusFacility('${id}')">
        下の詳細を見る ↓
      </button>

      ${siteButton(f, true)}
    </div>
  `;
}

function render() {
  const facilities = filterData();

  if ($('#count')) $('#count').textContent = facilities.length;
  if ($('#facility-list')) {
    $('#facility-list').innerHTML = facilities.map(card).join('');
  }

  markers.forEach((marker) => marker.remove());
  markers = [];

  facilities
    .filter((f) => Number.isFinite(Number(f.lat)) && Number.isFinite(Number(f.lon)))
    .forEach((f) => {
      const marker = L.marker([Number(f.lat), Number(f.lon)]).addTo(map);
      marker.bindPopup(popupHtml(f), { maxWidth: 340 });
      markers.push(marker);
    });

  if (markers.length) {
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.08), { maxZoom: 14 });
  }

  setTimeout(() => map.invalidateSize(), 50);
}

function card(f) {
  const id = cardId(f);

  return `
    <article class="facility-card" id="${id}">
      <h3>${esc(f.name || '')}</h3>

      <div class="badges">
        ${f.type ? `<span class="badge">${esc(f.type)}</span>` : ''}
        <span class="badge ${f.public ? 'public' : ''}">
          ${f.public ? '公立' : '私立等'}
        </span>
        ${f.services?.extended ? '<span class="badge">延長保育</span>' : ''}
        ${f.services?.temporary ? '<span class="badge temp">一時預かり</span>' : ''}
      </div>

      <dl class="facility-info">
        ${f.postal ? `<dt>郵便番号</dt><dd>〒${esc(f.postal)}</dd>` : ''}
        <dt>所在地</dt>
        <dd>${esc(f.address || '—')}</dd>
        <dt>電話</dt>
        <dd>
          ${f.phone
            ? `<a href="tel:${String(f.phone).replace(/-/g, '')}">${esc(f.phone)}</a>`
            : '—'}
        </dd>
      </dl>

      ${availabilityHtml(f)}
      ${siteButton(f)}
    </article>
  `;
}

window.addEventListener('DOMContentLoaded', () => {
  const waitForLeaflet = () => {
    if (window.L) init();
    else setTimeout(waitForLeaflet, 80);
  };
  waitForLeaflet();
});
