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

function availabilityHtml(facility, compact = false) {
  const a = facility.availability || {};
  const values = Object.keys(a);

  if (!values.length) {
    return '<div class="availability-note">受入見込み：現在のデータとの照合作業中</div>';
  }

  return `
    <div class="availability ${compact ? 'availability-popup' : ''}">
      ${[0,1,2,3,4,5].map((age) => {
        const status = a[String(age)] ?? '—';
        const cls = status === '○' ? 'o' : status === '△' ? 'd' : status === '×' ? 'x' : '';
        return `<span class="age-pill ${cls}">${age}歳<br>${esc(status)}</span>`;
      }).join('')}
    </div>
  `;
}

function officialLink(f) {
  if (!f.website) return '';
  return `<a class="facility-site-link"
            href="${esc(f.website)}"
            target="_blank"
            rel="noopener noreferrer">施設のホームページを見る ↗</a>`;
}

async function loadData() {
  const ts = Date.now();

  const masterResp = await fetch(`data/facility_master.json?v=${ts}`, {
    cache: 'no-store'
  });

  if (!masterResp.ok) {
    throw new Error(`facility_master.json: HTTP ${masterResp.status}`);
  }

  const master = await masterResp.json();

  let availability = {
    by_facility_id: {},
    availability_for: '',
    availability_as_of: '',
    source_page_updated: ''
  };

  try {
    const aResp = await fetch(`data/availability_fixed.json?v=${ts}`, {
      cache: 'no-store'
    });

    if (aResp.ok) {
      availability = await aResp.json();
    }
  } catch (_) {
    // 受入情報はなくても施設マスタだけでサイトを表示する。
  }

  const byId = availability.by_facility_id || {};

  allFacilities = (master.facilities || []).map((f) => ({
    ...f,
    type: f.category || '',
    public: f.public_private === '公立',
    availability: byId[f.id] || {}
  }));

  const meta = [];

  if (availability.availability_for) {
    meta.push(`${availability.availability_for}入園`);
  }
  if (availability.availability_as_of) {
    meta.push(availability.availability_as_of);
  }
  if (availability.source_page_updated) {
    meta.push(`岡山市ページ更新 ${availability.source_page_updated}`);
  }

  meta.push(`認可保育施設 ${allFacilities.length}施設`);

  if ($('#updated')) {
    $('#updated').textContent = meta.join('｜');
  }
}

function initMap() {
  map = L.map('map').setView([34.655, 133.92], 11);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
}

function applyQueryParams() {
  const params = new URLSearchParams(location.search);
  if (params.get('ward') && $('#ward')) {
    $('#ward').value = params.get('ward');
  }
}

function filterData() {
  const q = ($('#q')?.value || '').trim().toLowerCase();
  const ward = $('#ward')?.value || '';
  const type = $('#type')?.value || '';
  const service = $('#service')?.value || '';

  return allFacilities.filter((f) => {
    const text =
      `${f.name || ''} ${f.address || ''} ${f.operator || ''}`.toLowerCase();

    const typeMatches =
      !type ||
      f.category === type ||
      (type === '保育園' && f.category === '認可保育園') ||
      (type === '認定こども園' && f.category === '認定こども園') ||
      (type === '地域型保育' && String(f.category).startsWith('地域型保育事業'));

    return (
      (!q || text.includes(q)) &&
      (!ward || f.ward === ward) &&
      typeMatches &&
      (!service || Boolean(f.services?.[service]))
    );
  });
}

function popupHtml(f) {
  return `
    <div class="facility-popup">
      <strong>${esc(f.name)}</strong>
      <div>${esc(f.category || '')}・${esc(f.public_private || '')}</div>
      ${f.postal ? `<div>〒${esc(f.postal)}</div>` : ''}
      <div>${esc(f.address || '所在地情報なし')}</div>
      ${f.phone
        ? `<div><a href="tel:${esc(String(f.phone).replace(/-/g, ''))}">
             ${esc(f.phone)}
           </a></div>`
        : ''}
      ${availabilityHtml(f, true)}
      ${officialLink(f)}
    </div>
  `;
}

function card(f) {
  return `
    <article class="facility-card">
      <h3>${esc(f.name)}</h3>

      <div class="badges">
        <span class="badge">${esc(f.category || '')}</span>
        <span class="badge ${f.public_private === '公立' ? 'public' : ''}">
          ${esc(f.public_private || '')}
        </span>
      </div>

      <dl class="facility-info">
        <dt>所在地</dt>
        <dd>
          ${f.postal ? `〒${esc(f.postal)}<br>` : ''}
          ${esc(f.address || '—')}
        </dd>

        <dt>電話</dt>
        <dd>
          ${f.phone
            ? `<a href="tel:${esc(String(f.phone).replace(/-/g, ''))}">
                 ${esc(f.phone)}
               </a>`
            : '—'}
        </dd>
      </dl>

      ${availabilityHtml(f)}
      ${officialLink(f)}
    </article>
  `;
}

function render() {
  const fs = filterData();

  if ($('#count')) {
    $('#count').textContent = fs.length;
  }

  if ($('#facility-list')) {
    $('#facility-list').innerHTML = fs.map(card).join('');
  }

  markers.forEach((m) => m.remove());
  markers = [];

  fs.filter((f) =>
    Number.isFinite(Number(f.lat)) &&
    Number.isFinite(Number(f.lon))
  ).forEach((f) => {
    const marker = L.marker([
      Number(f.lat),
      Number(f.lon)
    ]).addTo(map);

    marker.bindPopup(popupHtml(f), {
      maxWidth: 340
    });

    markers.push(marker);
  });

  if (markers.length) {
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.08), { maxZoom: 14 });
  }

  setTimeout(() => map.invalidateSize(), 80);
}

async function init() {
  initMap();

  try {
    await loadData();
    applyQueryParams();
    render();
  } catch (error) {
    console.error(error);

    if ($('#count')) {
      $('#count').textContent = '0';
    }

    if ($('#facility-list')) {
      $('#facility-list').innerHTML = `
        <div class="notice">
          <strong>施設情報を読み込めませんでした。</strong><br>
          ページを再読み込みしても改善しない場合は、
          時間をおいてお試しください。
        </div>
      `;
    }
  }

  ['q', 'ward', 'type', 'service'].forEach((id) => {
    const el = $('#' + id);
    if (!el) return;

    el.addEventListener(
      id === 'q' ? 'input' : 'change',
      render
    );
  });
}

window.addEventListener('DOMContentLoaded', () => {
  const wait = () => {
    if (window.L) init();
    else setTimeout(wait, 80);
  };
  wait();
});
