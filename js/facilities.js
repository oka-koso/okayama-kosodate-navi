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
  const availability = facility.availability || {};

  if (!Object.keys(availability).length) {
    return '<div class="small">受入見込み：公表なし</div>';
  }

  const pills = [0, 1, 2, 3, 4, 5].map((age) => {
    const status =
      availability[String(age)] ??
      availability[age] ??
      '—';

    let cls = '';
    if (status === '○') cls = 'o';
    if (status === '△') cls = 'd';
    if (status === '×') cls = 'x';

    return `
      <span class="age-pill ${cls}" title="${age}歳：${esc(status)}">
        ${age}歳<br>${esc(status)}
      </span>
    `;
  }).join('');

  return `<div class="availability ${compact ? 'availability-popup' : ''}">${pills}</div>`;
}

function officialLinkHtml(facility, popup = false) {
  if (!facility.website) {
    return '';
  }

  const cls = popup ? 'popup-site-link' : 'facility-site-link';

  return `
    <a class="${cls}"
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
      if (!response.ok) {
        throw new Error(`facilities.json: HTTP ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      allFacilities = Array.isArray(data.facilities)
        ? data.facilities
        : [];

      const meta = [];

      if (data.availability_for) {
        meta.push(`${data.availability_for}入園`);
      }

      if (data.availability_as_of) {
        meta.push(data.availability_as_of);
      }

      if (data.source_page_updated) {
        meta.push(`岡山市ページ更新 ${data.source_page_updated}`);
      }

      if (Number.isFinite(Number(data.facility_count))) {
        meta.push(`掲載 ${Number(data.facility_count)}施設`);
      }

      const updated = $('#updated');
      if (updated) {
        updated.textContent = meta.join('｜');
      }

      applyQueryParams();
      render();

      setTimeout(() => map.invalidateSize(), 100);
    })
    .catch((error) => {
      console.error(error);

      const count = $('#count');
      if (count) count.textContent = '0';

      const list = $('#facility-list');
      if (list) {
        list.innerHTML = `
          <div class="notice">
            <strong>施設情報を読み込めませんでした。</strong><br>
            ページを再読み込みしても改善しない場合は、時間をおいてお試しください。
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
  const params = new URLSearchParams(location.search);

  if (params.get('ward')) {
    const ward = $('#ward');
    if (ward) ward.value = params.get('ward');
  }
}

function filterData() {
  const q = ($('#q')?.value || '').trim().toLowerCase();
  const ward = $('#ward')?.value || '';
  const type = $('#type')?.value || '';
  const service = $('#service')?.value || '';

  return allFacilities.filter((facility) => {
    const searchable =
      `${facility.name || ''} ${facility.address || ''} ${facility.operator || ''}`
        .toLowerCase();

    return (
      (!q || searchable.includes(q)) &&
      (!ward || facility.ward === ward) &&
      (!type || facility.type === type) &&
      (!service || Boolean(facility.services?.[service]))
    );
  });
}

function popupHtml(facility) {
  const phone = facility.phone
    ? `<div><a href="tel:${String(facility.phone).replace(/-/g, '')}">
         ${esc(facility.phone)}
       </a></div>`
    : '';

  return `
    <div class="facility-popup">
      <strong>${esc(facility.name || '')}</strong>
      <div class="small">${esc(facility.type || '')}・${facility.public ? '公立' : '私立等'}</div>
      <div>${esc(facility.address || '所在地情報なし')}</div>
      ${phone}
      ${availabilityHtml(facility, true)}
      ${officialLinkHtml(facility, true)}
    </div>
  `;
}

function render() {
  const facilities = filterData();

  const count = $('#count');
  if (count) count.textContent = facilities.length;

  const list = $('#facility-list');
  if (list) {
    list.innerHTML = facilities.map(card).join('');
  }

  markers.forEach((marker) => marker.remove());
  markers = [];

  facilities
    .filter((facility) => (
      Number.isFinite(Number(facility.lat)) &&
      Number.isFinite(Number(facility.lon))
    ))
    .forEach((facility) => {
      const marker = L.marker([
        Number(facility.lat),
        Number(facility.lon)
      ]).addTo(map);

      marker.bindPopup(popupHtml(facility), {
        maxWidth: 330
      });

      markers.push(marker);
    });

  if (markers.length > 0) {
    const group = L.featureGroup(markers);

    map.fitBounds(
      group.getBounds().pad(0.08),
      { maxZoom: 14 }
    );
  }

  setTimeout(() => map.invalidateSize(), 50);
}

function card(facility) {
  return `
    <article class="facility-card">
      <h3>${esc(facility.name || '')}</h3>

      <div class="badges">
        ${
          facility.type
            ? `<span class="badge">${esc(facility.type)}</span>`
            : ''
        }

        <span class="badge ${facility.public ? 'public' : ''}">
          ${facility.public ? '公立' : '私立等'}
        </span>

        ${
          facility.services?.extended
            ? '<span class="badge">延長保育</span>'
            : ''
        }

        ${
          facility.services?.temporary
            ? '<span class="badge temp">一時預かり</span>'
            : ''
        }
      </div>

      <dl class="facility-info">
        <dt>所在地</dt>
        <dd>${esc(facility.address || '—')}</dd>

        <dt>電話</dt>
        <dd>
          ${
            facility.phone
              ? `<a href="tel:${String(facility.phone).replace(/-/g, '')}">
                   ${esc(facility.phone)}
                 </a>`
              : '—'
          }
        </dd>
      </dl>

      ${availabilityHtml(facility)}
      ${officialLinkHtml(facility)}
    </article>
  `;
}

window.addEventListener('DOMContentLoaded', () => {
  const waitForLeaflet = () => {
    if (window.L) {
      init();
    } else {
      setTimeout(waitForLeaflet, 80);
    }
  };

  waitForLeaflet();
});
