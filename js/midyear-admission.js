(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const fmt = (iso) => {
    const d = new Date(`${iso}T00:00:00+09:00`);
    return new Intl.DateTimeFormat('ja-JP',{year:'numeric',month:'long',day:'numeric',weekday:'short',timeZone:'Asia/Tokyo'}).format(d);
  };
  const daysUntil = (deadline) => Math.ceil((deadline.getTime() - Date.now()) / 86400000);

  async function init(){
    try {
      const r = await fetch(`data/midyear_admission.json?v=${Date.now()}`, {cache:'no-store'});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const deadline = new Date(d.deadline_iso_jst);
      const left = daysUntil(deadline);
      const closed = Date.now() > deadline.getTime();

      $('#midyear-target').textContent = `${d.target_label}入園`;
      $('#midyear-deadline').textContent = `${fmt(d.deadline_date)} 17:15 必着`;
      $('#midyear-asof').textContent = d.availability_as_of || '最新公表分';
      $('#midyear-generated').textContent = d.generated_at ? `最終確認 ${d.generated_at}` : '';

      const badge = $('#midyear-countdown');
      if (closed) {
        badge.textContent = 'この月の受付は締切済み';
        badge.className = 'deadline-badge is-closed';
      } else if (left <= 1) {
        badge.textContent = left <= 0 ? '本日17:15締切' : '締切まで1日';
        badge.className = 'deadline-badge is-urgent';
      } else {
        badge.textContent = `締切まで約${left}日`;
        badge.className = left <= 7 ? 'deadline-badge is-soon' : 'deadline-badge';
      }

      $('#midyear-rule').textContent = d.application_rule || '';
      $('#midyear-start-note').textContent = d.application_start_note || '';
      $('#midyear-publish-note').textContent = d.availability_publish_note || '';

      const availabilityLink = $('#midyear-availability-link');
      availabilityLink.href = 'hoikuen.html';
      availabilityLink.textContent = `${d.target_label}の受入見込みを見る`;

      if (d.sources?.application) $('#official-application').href = d.sources.application;
      if (d.sources?.guide) $('#official-guide').href = d.sources.guide;
      if (d.sources?.availability) $('#official-availability').href = d.sources.availability;
      if (d.availability_source_pdf_url) {
        $('#official-pdf').href = d.availability_source_pdf_url;
        $('#official-pdf').hidden = false;
      }
      $('#midyear-loading').hidden = true;
      $('#midyear-content').hidden = false;
    } catch (e) {
      console.error(e);
      $('#midyear-loading').textContent = '最新の途中入園情報を読み込めませんでした。時間をおいて再読み込みしてください。';
      $('#midyear-loading').className = 'notice midyear-error';
    }
  }
  window.addEventListener('DOMContentLoaded', init);
})();
