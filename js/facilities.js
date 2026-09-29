let allFacilities = [];
let map;
let markers = [];
let markerById = new Map();

const $ = (selector) => document.querySelector(selector);

const WARD_COLORS = {
  '北区': '#2f80ed',
  '中区': '#27ae60',
  '東区': '#f2994a',
  '南区': '#9b51e0'
};

const PUBLIC_NURSERY_PAGE =
  'https://www.city.okayama.jp/kurashi/0000030497.html';
const PUBLIC_KODOMO_PAGE =
  'https://www.city.okayama.jp/kurashi/0000030473.html';

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function normalizeFacilityLinks(f) {
  // 本来はpublic_private / official_info_urlを固定マスタから読む。
  // ただし旧キャッシュや旧マスタでも公立リンクが消えないよう、
  // 岡山市公立施設HTML由来の印を安全なフォールバックにする。
  const publicByMaster = f.public_private === '公立';
  const publicBySource =
    f.contact_source === 'Okayama City public-facility HTML' ||
    Boolean(f.public_source);

  const isPublic = publicByMaster || publicBySource;

  let officialInfoUrl = f.official_info_url || '';

  if (isPublic && !officialInfoUrl) {
    officialInfoUrl =
      f.category === '認定こども園'
        ? PUBLIC_KODOMO_PAGE
        : PUBLIC_NURSERY_PAGE;
  }

  let websiteStatus = f.website_status || 'unchecked';

  if (isPublic) {
    websiteStatus = 'none';
  } else if (f.website) {
    websiteStatus = 'verified';
  }

  return {
    ...f,
    public_private:
      isPublic ? '公立' : (f.public_private || '私立'),
    website_status: websiteStatus,
    official_info_url: officialInfoUrl
  };
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
        const cls =
          status === '○' ? 'o' :
          status === '△' ? 'd' :
          status === '×' ? 'x' : '';

        return `<span class="age-pill ${cls}">${age}歳<br>${esc(status)}</span>`;
      }).join('')}
    </div>
  `;
}

function serviceState(value) {
  if (value === true) return { label: '実施', cls: 'yes' };
  if (value === false) return { label: 'なし', cls: 'no' };
  return { label: '未確認', cls: 'unknown' };
}

function servicesHtml(f, compact = false) {
  const s = f.services || {};
  const defs = [
    ['extended', '延長保育'],
    ['temporary', '一時預かり'],
    ['holiday', '休日保育'],
    ['support_center', '支援センター']
  ];

  return `
    <div class="service-list ${compact ? 'service-list-popup' : ''}">
      ${defs.map(([key, label]) => {
        const state = serviceState(s[key]);
        return `
          <span class="service-chip ${state.cls}" title="${esc(label)}">
            ${esc(label)}：${state.label}
          </span>
        `;
      }).join('')}
    </div>
  `;
}

function externalLinksHtml(f, compact = false) {
  const rows = [];

  if (f.website) {
    rows.push(
      `<a class="facility-site-link"
          href="${esc(f.website)}"
          target="_blank"
          rel="noopener noreferrer">
         公式ホームページを見る ↗
       </a>`
    );
  } else if (f.website_status === 'none') {
    rows.push(
      '<span class="facility-site-none">公式ホームページ：なし</span>'
    );
  } else {
    rows.push(
      '<span class="facility-site-pending">公式ホームページ：確認中</span>'
    );
  }

  if (f.official_info_url) {
    const label =
      f.public_private === '公立'
        ? '岡山市の掲載ページを見る ↗'
        : '岡山市の施設情報を見る ↗';

    rows.push(
      `<a class="facility-city-link"
          href="${esc(f.official_info_url)}"
          target="_blank"
          rel="noopener noreferrer">
         ${label}
       </a>`
    );
  }

  return `
    <div class="facility-links ${compact ? 'facility-links-popup' : ''}">
      ${rows.join('')}
    </div>
  `;
}

function wardPinIcon(ward) {
  const color = WARD_COLORS[ward] || '#66736e';

  return L.divIcon({
    className: 'ward-div-icon',
    html: `<span class="ward-pin" style="--pin-color:${color}" aria-hidden="true"></span>`,
    iconSize: [24, 32],
    iconAnchor: [12, 30],
    popupAnchor: [0, -28]
  });
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
  } catch (_) {}

  const byId = availability.by_facility_id || {};

  allFacilities = (master.facilities || []).map((raw) => {
    const f = normalizeFacilityLinks(raw);

    return {
      ...f,
      type: f.category || '',
      public: f.public_private === '公立',
      availability: byId[f.id] || {},
      services: {
        extended: f.services?.extended ?? null,
        temporary: f.services?.temporary ?? null,
        holiday: f.services?.holiday ?? null,
        support_center: f.services?.support_center ?? null
      }
    };
  });

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
  map = L.map('map', {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView([34.655, 133.92], 11);

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }
  ).addTo(map);

  const legend = L.control({ position: 'bottomright' });

  legend.onAdd = function() {
    const div = L.DomUtil.create('div', 'map-legend');

    div.innerHTML = `
      <strong>区別</strong>
      ${Object.entries(WARD_COLORS).map(([ward, color]) => `
        <span><i style="background:${color}"></i>${ward}</span>
      `).join('')}
    `;

    return div;
  };

  legend.addTo(map);
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
      (
        type === '地域型保育' &&
        String(f.category).startsWith('地域型保育事業')
      );

    return (
      (!q || text.includes(q)) &&
      (!ward || f.ward === ward) &&
      typeMatches &&
      (!service || f.services?.[service] === true)
    );
  });
}

function popupHtml(f) {
  return `
    <div class="facility-popup">
      <a class="popup-facility-name"
         href="#facility-${esc(f.id)}"
         data-facility-id="${esc(f.id)}">
        ${esc(f.name)}
      </a>

      <div>
        ${esc(f.category || '')}・
        ${esc(f.public_private || '')}・
        ${esc(f.ward || '')}
      </div>

      ${f.postal ? `<div>〒${esc(f.postal)}</div>` : ''}

      <div>${esc(f.address || '所在地情報なし')}</div>

      ${f.phone
        ? `<div><a href="tel:${esc(String(f.phone).replace(/-/g, ''))}">${esc(f.phone)}</a></div>`
        : ''}

      ${servicesHtml(f, true)}
      ${availabilityHtml(f, true)}

      <div class="facility-section-title">関連リンク</div>
      ${externalLinksHtml(f, true)}

      <a class="popup-detail-link"
         href="#facility-${esc(f.id)}"
         data-facility-id="${esc(f.id)}">
        下の施設カードを見る ↓
      </a>
    </div>
  `;
}

function card(f) {
  return `
    <article class="facility-card"
             id="facility-${esc(f.id)}"
             data-facility-id="${esc(f.id)}">

      <div class="facility-card-head">
        <h3>${esc(f.name)}</h3>

        <button type="button"
                class="map-focus-btn"
                data-map-id="${esc(f.id)}">
          地図で見る
        </button>
      </div>

      <div class="badges">
        <span class="badge">${esc(f.category || '')}</span>

        <span class="badge ${f.public_private === '公立' ? 'public' : ''}">
          ${esc(f.public_private || '')}
        </span>

        <span class="badge ward-badge">${esc(f.ward || '')}</span>
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
            ? `<a href="tel:${esc(String(f.phone).replace(/-/g, ''))}">${esc(f.phone)}</a>`
            : '—'}
        </dd>
      </dl>

      <div class="facility-section-title">保育サービス</div>
      ${servicesHtml(f)}

      <div class="facility-section-title">年齢別の受入見込み</div>
      ${availabilityHtml(f)}

      <div class="facility-section-title">関連リンク</div>
      ${externalLinksHtml(f)}
    </article>
  `;
}

function scrollToCard(id) {
  const cardEl = document.getElementById(`facility-${id}`);
  if (!cardEl) return;

  cardEl.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });

  cardEl.classList.add('facility-card-highlight');

  window.setTimeout(() => {
    cardEl.classList.remove('facility-card-highlight');
  }, 1800);
}

function focusMarker(id) {
  const marker = markerById.get(id);
  if (!marker) return;

  const ll = marker.getLatLng();

  map.setView(
    ll,
    Math.max(map.getZoom(), 16),
    { animate: true }
  );

  marker.openPopup();

  document.getElementById('map')?.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });
}

function clearMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
  markerById.clear();
}

function fitMarkersToView(fs) {
  const withCoords = fs.filter((f) =>
    Number.isFinite(Number(f.lat)) &&
    Number.isFinite(Number(f.lon))
  );

  if (!withCoords.length) return;

  const bounds = L.latLngBounds(
    withCoords.map((f) => [
      Number(f.lat),
      Number(f.lon)
    ])
  );

  map.fitBounds(bounds.pad(0.04), {
    maxZoom:
      fs.length === allFacilities.length ? 12 : 15,
    animate: false
  });
}

function render() {
  const fs = filterData();

  if ($('#count')) {
    $('#count').textContent = fs.length;
  }

  if ($('#facility-list')) {
    $('#facility-list').innerHTML =
      fs.map(card).join('');
  }

  clearMarkers();

  fs.filter((f) =>
    Number.isFinite(Number(f.lat)) &&
    Number.isFinite(Number(f.lon))
  ).forEach((f) => {
    const marker = L.marker(
      [Number(f.lat), Number(f.lon)],
      { icon: wardPinIcon(f.ward) }
    ).addTo(map);

    marker.bindPopup(
      popupHtml(f),
      { maxWidth: 360 }
    );

    markers.push(marker);
    markerById.set(f.id, marker);
  });

  fitMarkersToView(fs);

  setTimeout(() => map.invalidateSize(), 80);
}

function bindInteractions() {
  ['q', 'ward', 'type', 'service'].forEach((id) => {
    const el = $('#' + id);
    if (!el) return;

    el.addEventListener(
      id === 'q' ? 'input' : 'change',
      render
    );
  });

  document.addEventListener('click', (event) => {
    // 「地図で見る」を最優先で処理する。
    // 施設カード自体にも data-facility-id が付いているため、
    // 先に [data-facility-id] を拾うとボタンクリックが
    // scrollToCard() に吸われてしまう。
    const mapBtn =
      event.target.closest('[data-map-id]');

    if (mapBtn) {
      const id = mapBtn.dataset.mapId;

      if (id) {
        event.preventDefault();
        focusMarker(id);
      }

      return;
    }

    const detail =
      event.target.closest('[data-facility-id]');

    if (detail) {
      const id = detail.dataset.facilityId;

      if (id) {
        event.preventDefault();
        scrollToCard(id);
      }
    }
  });
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

  bindInteractions();
}

window.addEventListener('DOMContentLoaded', () => {
  const wait = () => {
    if (window.L) {
      init();
    } else {
      setTimeout(wait, 80);
    }
  };

  wait();
});
