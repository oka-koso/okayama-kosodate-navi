(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const fmt = (iso) => new Intl.DateTimeFormat('ja-JP', {
    year:'numeric',month:'long',day:'numeric',weekday:'short',timeZone:'Asia/Tokyo'
  }).format(new Date(`${iso}T00:00:00+09:00`));
  let data;

  function render(){
    if(!data)return;
    const d=data, now=Date.now();
    // Always choose from official monthly deadlines; April's recruitment has a separate UI.
    const rows=d.deadlines || (d.deadline_iso_jst ? [d] : []);
    const next=window.OKNAvailability.nextDeadline({...d,deadlines:rows},now);
    const badge=$('#midyear-countdown');
    if(next){
      const deadline=new Date(next.deadline_iso_jst);
      const left=Math.ceil((deadline.getTime()-now)/86400000);
      $('#midyear-target').textContent=`次に申し込める月：${next.target_label}入園`;
      $('#midyear-deadline').textContent=`${fmt(next.deadline_date)} 17:15 必着`;
      badge.textContent=left<=0?'本日17:15締切':left===1?'締切まで1日':`締切まで約${left}日`;
      badge.className=left<=1?'deadline-badge is-urgent':left<=7?'deadline-badge is-soon':'deadline-badge';
    }else{
      $('#midyear-target').textContent='次の途中入園の申込日程';
      $('#midyear-deadline').textContent='岡山市の最新案内をご確認ください';
      badge.textContent='確認済みの締切一覧に次の募集がありません';
      badge.className='deadline-badge is-closed';
    }

    const current=(d.availability_for||'').replace(/\s+/g,'');
    $('#midyear-availability-target').textContent=current?`${d.availability_for}入園の資料`:'直近の公表資料';
    $('#midyear-asof').textContent=d.availability_as_of||'基準日未確認';
    const summary=window.OKNAvailability.describe(d,'monthly',d,now);
    const published=summary.published;
    const state=$('#midyear-next-availability');
    if(!next){
      state.textContent='次の募集の受入見込みは、岡山市の公式ページで確認してください。';
    }else{
      state.textContent=summary.nextText;
    }
    $('#midyear-availability-status').textContent=summary.notice;

    const latestLink=$('#midyear-availability-link');
    // Keep the midyear link on monthly mode even when April becomes the MAP default.
    latestLink.href='hoikuen.html?availability=monthly';
    latestLink.textContent=current?`${d.availability_for}の参考資料をMAPで見る`:'途中入園の参考資料をMAPで見る';
    $('#midyear-rule').textContent=d.application_rule||'';
    $('#midyear-start-note').textContent=d.application_start_note||'';
    $('#midyear-publish-note').textContent=d.availability_publish_note||'';
    const verified=d.checked_at ? new Date(d.checked_at) : null;
    const stale=!verified || now-verified.getTime()>48*3600000;
    const warning=$('#midyear-update-warning');
    warning.hidden=!summary.warning&&d.check_status!=='failed'&&!stale;
    warning.textContent=d.check_status==='failed'
      ?'公式ページの更新確認に失敗したため、最後に確認できた締切を表示しています。申込前には公式情報を確認してください。'
      :summary.warning||'公式ページの確認から時間が経っています。申込前には岡山市の最新案内を確認してください。';
    $('#midyear-generated').textContent=verified?`申込日程の公式ページ確認：${new Intl.DateTimeFormat('ja-JP',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Tokyo'}).format(verified)}`:'';
    const publicationChecked=d.publications_checked_at?new Date(d.publications_checked_at):null;
    $('#midyear-publication-checked').textContent=publicationChecked?`受入見込みの公式ページ確認：${new Intl.DateTimeFormat('ja-JP',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Tokyo'}).format(publicationChecked)}`:'';
    if(d.sources?.application)$('#official-application').href=d.sources.application;
    if(d.sources?.guide)$('#official-guide').href=d.sources.guide;
    if(d.sources?.availability)$('#official-availability').href=d.sources.availability;
    const pdf=$('#official-pdf');
    pdf.hidden=!d.availability_source_pdf_url;
    if(!pdf.hidden)pdf.href=d.availability_source_pdf_url;
    const nextPDF=$('#next-availability-pdf');
    nextPDF.hidden=!published || d.publication_check_status==='failed';
    if(!nextPDF.hidden){nextPDF.href=published.url;nextPDF.textContent=`${next.target_label}の公式受入見込みPDF ↗`;}
    $('#midyear-loading').hidden=true;
    $('#midyear-content').hidden=false;
  }

  async function init(){
    try{
      const r=await fetch(`data/midyear_admission.json?v=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      data=await r.json();render();
      // A tab left open through 17:15 must move to the next confirmed deadline too.
      setInterval(render,30000);
    }catch(e){
      console.error(e);
      $('#midyear-loading').textContent='最新の途中入園情報を読み込めませんでした。岡山市の公式案内から申込期限を確認してください。';
      $('#midyear-loading').className='notice midyear-error';
    }
  }
  window.addEventListener('DOMContentLoaded',init);
})();
