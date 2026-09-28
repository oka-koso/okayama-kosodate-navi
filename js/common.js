window.OKN = {
  formatDate(iso){ if(!iso) return '未確認'; const d=new Date(iso+'T00:00:00+09:00'); return new Intl.DateTimeFormat('ja-JP',{year:'numeric',month:'long',day:'numeric'}).format(d); },
  esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
};
