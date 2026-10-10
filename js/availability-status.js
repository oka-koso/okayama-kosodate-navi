(() => {
  'use strict';
  const normalize = value => String(value || '').replace(/[０-９]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0)).replace(/\s+/g, '');
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const date = value => new Intl.DateTimeFormat('ja-JP', {year:'numeric',month:'long',day:'numeric',timeZone:'Asia/Tokyo'}).format(new Date(`${value}T00:00:00+09:00`));
  const stamp = value => new Intl.DateTimeFormat('ja-JP', {dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Tokyo'}).format(new Date(value));
  const validTime = value => value && Number.isFinite(new Date(value).getTime());
  function nextDeadline(guide, now = Date.now()) {
    return (guide?.deadlines || []).filter(row => row.target_month !== 4 && validTime(row.deadline_iso_jst))
      .sort((a, b) => new Date(a.deadline_iso_jst) - new Date(b.deadline_iso_jst))
      .find(row => new Date(row.deadline_iso_jst).getTime() >= now) || null;
  }
  function describe(dataset = {}, mode = 'monthly', guide = {}, now = Date.now()) {
    const label = dataset.availability_for || '';
    const hasData = Boolean(label && (!dataset.by_facility_id || Object.keys(dataset.by_facility_id).length));
    const rows = guide.deadlines || [];
    const matched = mode === 'monthly' && rows.find(row => normalize(row.target_label) === normalize(label));
    const closed = Boolean(matched && now > new Date(matched.deadline_iso_jst).getTime());
    const checked = guide.publications_checked_at;
    const stale = !validTime(checked) || now - new Date(checked).getTime() > 48 * 3600000;
    const failed = guide.publication_check_status === 'failed';
    const next = mode === 'monthly' ? nextDeadline(guide, now) : null;
    const published = (guide.availability_publications || []).find(row => next && row.target_year === next.target_year && row.target_month === next.target_month);
    const plan = (guide.availability_publication_plans || []).find(row => next && row.target_year === next.target_year && row.target_month === next.target_month);
    let nextText = '';
    if (next) {
      const deadline = `${next.target_label}入園の申込締切：${date(next.deadline_date)} ${next.deadline_time || '17:15'}必着。`;
      let publication;
      if (failed || stale) {
        publication = `${next.target_label}の受入見込みの公開状況は、岡山市の公式ページで再確認してください。`;
      } else if (published) {
        publication = hasData && normalize(label) === normalize(next.target_label)
          ? `${next.target_label}の公表資料を表示しています。`
          : `${next.target_label}の資料は公表されています。園別表示への反映を確認中のため、公式資料をご確認ください。`;
      } else {
        publication = `${next.target_label}の受入見込みは、最終確認時点で未公開です。`;
        if (plan && validTime(`${plan.publish_date}T00:00:00+09:00`)) publication += `市の公表予定：${date(plan.publish_date)}（予定は変更される場合があります）。`;
      }
      nextText = `${deadline} ${publication}`;
    }
    const warning = dataset.display_load_failed
      ? '園別資料の読込みに失敗しました。最後に取得できた参考資料を表示している場合があります。公式資料をご確認ください。'
      : failed ? '受入見込みの公式ページの更新確認に失敗しています。未公開と判断せず、公式情報をご確認ください。'
      : stale ? '受入見込みの公開状況を最近確認できていません。申込前に公式情報をご確認ください。'
      : guide.check_status === 'failed' ? '申込日程の更新確認に失敗したため、最後に確認できた締切を表示しています。公式情報をご確認ください。' : '';
    return {
      closed, next, published, warning,
      title: !hasData ? '園別の受入見込みを表示できません' : `${closed ? '直近に公表された参考資料' : '公表された受入見込み（参考情報）'}：${label}入園`,
      caption: hasData ? `資料基準日：${dataset.availability_as_of || '未確認'}${dataset.source_page_updated ? `／資料取得時の市ページ更新日：${dataset.source_page_updated}` : ''}` : '資料の読込み・公表状況は公式ページでご確認ください。',
      notice: closed ? 'この月の申込受付は終了しています。表示中の○△×は、次の月の受入見込みではありません。' : '公表時点の参考情報です。現在の空きや入園を保証するものではありません。',
      nextText,
      checkedText: validTime(checked) ? `受入見込みの公式ページ・最終確認：${stamp(checked)}` : '受入見込みの公式ページ・確認日時：未確認'
    };
  }
  function render(element, dataset, mode, guide) {
    if (!element) return;
    const s = describe(dataset, mode, guide);
    element.innerHTML = `<p><strong>${esc(s.title)}</strong></p><p class="small">${esc(s.caption)}</p><p>${esc(s.notice)}</p>${s.nextText ? `<p>${esc(s.nextText)}</p>` : ''}${s.warning ? `<p class="availability-warning">${esc(s.warning)}</p>` : ''}<p class="small">${esc(s.checkedText)}／<a href="https://www.city.okayama.jp/kurashi/0000012977.html" target="_blank" rel="noopener noreferrer">岡山市の公式情報 ↗</a></p>`;
    element.hidden = false;
  }
  window.OKNAvailability = {describe, render, nextDeadline};
})();
