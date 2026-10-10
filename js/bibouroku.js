(() => {
  'use strict';
  const base = document.documentElement.dataset.siteBase || '';
  const categories = ['園選び・保活', '入園申込・手続き', '入園準備・通園生活'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const dateJP = value => { const p = String(value || '').split('-'); return p.length === 3 ? `${Number(p[0])}年${Number(p[1])}月${Number(p[2])}日` : value || ''; };
  function imageFor(article) {
    if (article.image) return String(article.image);
    const url = String(article.url || '');
    if (url.includes('hoikuen-sagashi-hajimekata')) return 'assets/bibouroku/hoikuen-start-map.png';
    if (url.includes('hoikuen-erabikata-part1')) return 'assets/bibouroku/hoikuen-erabikata-part1.png';
    if (url.includes('hoikuen-erabikata-part2')) return 'assets/bibouroku/hoikuen-erabikata-part2.png';
    if (url.includes('hoikuen-erabikata-part3')) return 'assets/bibouroku/hoikuen-erabikata-part1.png';
    return 'assets/bibouroku/bibouroku-reading.png';
  }
  function card(article) {
    return `<a class="bibouroku-card" href="${base}${esc(article.url)}"><img class="bibouroku-card__thumb" src="${base}${esc(imageFor(article))}" alt="" loading="lazy" decoding="async"><div class="bibouroku-card__meta"><span class="bibouroku-card__tag">${esc(article.category || '子育て')}</span><span>${esc(dateJP(article.published))}</span></div><h2>${esc(article.title)}</h2><p>${esc(article.description)}</p><span class="bibouroku-card__more">続きを読む →</span></a>`;
  }
  async function load() {
    const targets = [...document.querySelectorAll('[data-bibouroku-list]')];
    if (!targets.length) return;
    try {
      const res = await fetch(base + 'data/bibouroku.json?v=20261011-audit', {cache:'no-store'});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const parts = new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
      const dm = Object.fromEntries(parts.map(p => [p.type, p.value]));
      const todayKey = `${dm.year}-${dm.month}-${dm.day}`;
      const now = new Date();
      const items = (await res.json()).filter(article => article.publish_at ? new Date(article.publish_at) <= now : !article.published || article.published <= todayKey)
        .sort((a, b) => String(b.publish_at || b.published || '').localeCompare(String(a.publish_at || a.published || '')));
      targets.forEach(el => {
        const limit = Number(el.dataset.limit || 0);
        const filter = !limit && document.querySelector('[data-bibouroku-filters]');
        const count = !limit && document.querySelector('[data-bibouroku-count]');
        const render = category => {
          const selected = category ? items.filter(article => article.category === category) : items;
          const list = limit ? selected.slice(0, limit) : selected;
          el.innerHTML = list.length ? list.map(card).join('') : '<p class="bibouroku-empty">この分類の公開記事はまだありません。ほかの分類もご覧ください。</p>';
          if (count) count.textContent = category ? `${category}：${selected.length}記事` : `公開記事：${items.length}記事`;
        };
        render('');
        if (filter) {
          filter.innerHTML = ['', ...categories].map(category => `<button type="button" data-bibouroku-category="${esc(category)}" aria-pressed="${category ? 'false' : 'true'}">${esc(category || 'すべて')} <span>${category ? items.filter(article => article.category === category).length : items.length}</span></button>`).join('');
          filter.hidden = false;
          filter.addEventListener('click', event => {
            const button = event.target.closest('[data-bibouroku-category]');
            if (!button || !filter.contains(button)) return;
            filter.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
            render(button.dataset.bibourokuCategory);
          });
        }
      });
    } catch (error) {
      console.warn('記事一覧データを取得できないためHTML上の記事一覧を表示します', error);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
