(() => {
  'use strict';

  let rules = null;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const employmentOptions = (selected='') => `
    <label class="field-label">月の所定時間（休憩時間を除く）</label>
    <select class="score-control detail-value">
      <option value="">選択してください</option>
      ${rules.base.employment.map(x => `<option value="${x.id}" ${selected===x.id?'selected':''}>${esc(x.label)}（${x.score}点）</option>`).join('')}
      <option value="under48">月48時間未満／この区分に該当しない</option>
    </select>`;

  const homeworkOptions = () => `
    <label class="field-label">月の内職時間</label>
    <select class="score-control detail-value">
      <option value="">選択してください</option>
      ${rules.base.homework.map(x => `<option value="${x.id}">${esc(x.label)}（${x.score}点）</option>`).join('')}
      <option value="under48">月48時間未満／この区分に該当しない</option>
    </select>`;

  function detailHTML(type) {
    const fixed = rules.base.fixed;
    if (['employment','care','school','return_planned','care_separate','return_schoolchild'].includes(type)) {
      const labels = {
        care:'介護・看護に相当する時間',
        school:'就学・職業訓練の時間',
        return_planned:'復帰後の月所定労働時間',
        care_separate:'介護・看護に相当する時間',
        return_schoolchild:'復帰後の月所定労働時間'
      };
      return (labels[type] ? `<p class="detail-note">${esc(labels[type])}を、区分1（就労）の時間区分に準じて選びます。</p>` : '') + employmentOptions();
    }
    if (type === 'employment_planned') {
      return `<p class="detail-note">採用・起業・就学予定は、区分1に準じた点数から1点減点します。</p>${employmentOptions()}`;
    }
    if (type === 'homework') return homeworkOptions();
    if (type === 'pregnancy') return `<div class="absence-box"><strong>${fixed.pregnancy.score}点</strong><span>出産予定日前6週（多胎14週）〜産後8週の期間を含む月単位の期間。</span></div>`;
    if (type === 'illness') return `
      <label class="field-label">状態</label><select class="score-control detail-value">
        <option value="">選択してください</option>
        <option value="illness_hospital">1か月以上の入院・入院見込み、常時臥床（10点）</option>
        <option value="illness_home">1か月以上の居宅内療養・安静等（8点）</option>
        <option value="illness_visit">週3日程度の通院加療等（4点）</option>
      </select>`;
    if (type === 'disability') return `
      <label class="field-label">基準表上の区分</label><select class="score-control detail-value">
        <option value="">選択してください</option>
        <option value="disability_high">重度区分（10点）</option>
        <option value="disability_mid">中度区分（6点）</option>
        <option value="disability_low">軽度区分（3点）</option>
      </select>
      <p class="detail-note">手帳の等級・要介護度の詳細は公式基準表をご確認ください。</p>`;
    if (type === 'disaster') return `<div class="absence-box"><strong>${fixed.disaster.score}点</strong><span>震災・風水害・火災その他の災害の復旧に当たっている場合。</span></div>`;
    if (type === 'job_search') return `<div class="absence-box"><strong>${fixed.job_search.score}点</strong><span>求職活動（起業準備を含む）を継続的に行っている場合。</span></div>`;
    if (type === 'social') return `
      <label class="field-label">状態</label><select class="score-control detail-value">
        <option value="">選択してください</option>
        <option value="social_abuse">児童虐待又はそのおそれ（基礎10点）</option>
        <option value="social_dv">DVにより保育困難（基礎5点）</option>
      </select>
      <p class="detail-note">公的機関等による認定が関係するため、実際の適用は岡山市の審査によります。</p>`;
    if (type === 'childcare_leave') return `<div class="absence-box"><strong>${fixed.childcare_leave.score}点</strong><span>公式基準の継続利用要件に該当する場合。</span></div>`;
    if (type === 'other') return `<div class="result-warning">「市長が特別に認める場合」はこのツールでは点数を自動判定できません。就園管理課へご確認ください。</div>`;
    return '';
  }

  function findScore(list, id) {
    const x = list.find(v => v.id === id);
    return x ? x.score : null;
  }

  function guardianScore(n) {
    if (n === 2 && $('single-parent').checked) {
      return {score:10, label:'不存在', warning:null};
    }
    const type = $(`g${n}-type`).value;
    if (!type) return {score:null,label:'未選択',warning:'保護者'+n+'の状況を選択してください。'};
    const detail = document.querySelector(`#g${n}-detail .detail-value`);
    const val = detail?.value || '';
    const fixed = rules.base.fixed;

    if (['employment','care','school','return_planned','care_separate','return_schoolchild'].includes(type)) {
      if (!val) return {score:null,label:'時間区分未選択',warning:'保護者'+n+'の時間区分を選択してください。'};
      if (val === 'under48') return {score:0,label:'48時間未満',warning:'月48時間未満は区分1の点数対象外です。保育の必要性の認定可否を岡山市へご確認ください。'};
      const s = findScore(rules.base.employment,val);
      return {score:s,label:document.querySelector(`#g${n}-detail .detail-value option:checked`).textContent.replace(/（.*$/,'').trim(),warning:null};
    }
    if (type === 'employment_planned') {
      if (!val) return {score:null,label:'時間区分未選択',warning:'保護者'+n+'の予定時間区分を選択してください。'};
      if (val === 'under48') return {score:0,label:'予定・48時間未満',warning:'予定時間が月48時間未満の場合は自動判定できません。'};
      const raw = findScore(rules.base.employment,val);
      return {score:Math.max(0,raw-1),label:'採用・起業・就学予定（区分1−1点）',warning:null};
    }
    if (type === 'homework') {
      if (!val) return {score:null,label:'内職時間未選択',warning:'保護者'+n+'の内職時間を選択してください。'};
      if (val === 'under48') return {score:0,label:'内職48時間未満',warning:'月48時間未満は内職の点数対象外です。'};
      return {score:findScore(rules.base.homework,val),label:'内職',warning:null};
    }
    if (type === 'illness' || type === 'disability' || type === 'social') {
      if (!val) return {score:null,label:'詳細未選択',warning:'保護者'+n+'の詳細区分を選択してください。'};
      return {score:fixed[val].score,label:fixed[val].label,warning:null};
    }
    if (type === 'other') return {score:null,label:'個別判定',warning:'「市長が特別に認める場合」は自動計算できません。岡山市へご確認ください。'};
    const keyMap = {pregnancy:'pregnancy',disaster:'disaster',job_search:'job_search',childcare_leave:'childcare_leave'};
    const k = keyMap[type];
    if (k) return {score:fixed[k].score,label:fixed[k].label,warning:null};
    return {score:null,label:'判定不能',warning:'入力内容を確認してください。'};
  }

  function renderGuardian(n) {
    const type = $(`g${n}-type`).value;
    $(`g${n}-detail`).innerHTML = detailHTML(type);
    $(`g${n}-detail`).querySelectorAll('select,input').forEach(el => el.addEventListener('change', () => updatePreview(n)));
    updatePreview(n);
  }

  function updatePreview(n) {
    const r = guardianScore(n);
    $(`g${n}-preview`).textContent = r.score === null ? '基礎点：—' : `基礎点：${r.score}点`;
  }

  function setSingleParent() {
    const on = $('single-parent').checked;
    $('g2-normal').hidden = on;
    $('g2-absence').hidden = !on;
    $('g2-help').textContent = on ? 'ひとり親として「不存在」10点を自動適用します。' : 'もう一方の保護者について選んでください。';
    updatePreview(2);
  }

  function selectedRule(group, id) {
    return (rules.adjustments[group] || []).find(x => x.id === id) || null;
  }

  function adjustmentScore() {
    const lines = [];
    let score = 0;
    if ($('single-parent').checked) { score += 3; lines.push(['A ひとり親世帯',3]); }
    if ($('adj-B').checked) { score += 1; lines.push(['B 生活保護',1]); }
    if ($('adj-C').checked) { score += 2; lines.push(['C 失業',2]); }
    if ($('adj-G').checked) { score += 3; lines.push(['G きょうだい',3]); }

    for (const group of ['D','E','F','H','J']) {
      const id = $(`adj-${group}`).value;
      if (!id) continue;
      const x = selectedRule(group,id);
      if (x) { score += x.score; lines.push([`${group} ${x.label}`,x.score]); }
    }

    const gp = Number($('grandparents').value || 0);
    if (gp) {
      const s = gp * rules.adjustments.I.score_each;
      score += s; lines.push([`I 同居祖父母 ${gp}人`,s]);
    }
    return {score,lines};
  }

  function calculate() {
    const g1 = guardianScore(1), g2 = guardianScore(2);
    const warnings = [g1.warning,g2.warning].filter(Boolean);
    if (g1.score === null || g2.score === null) {
      $('total-score').textContent = '—';
      $('base-score').textContent = '—';
      $('adjust-score').textContent = '—';
      $('result-message').textContent = '未入力または自動判定できない項目があります。';
      $('result-details').innerHTML = warnings.map(w => `<div class="result-warning">${esc(w)}</div>`).join('');
      $('score-result').scrollIntoView({behavior:'smooth',block:'nearest'});
      return;
    }

    // 岡山市の基礎点数は父母の点数を合算せず、低い方を採用する。
    // ひとり親は保護者2に「不存在」10点を適用した上で比較する。
    const base = Math.min(g1.score, g2.score);
    const adj = adjustmentScore();
    const normalTotal = base + adj.score;
    const k = $('adj-K').checked;
    const total = k ? 1 : normalTotal;

    $('total-score').textContent = total;
    $('base-score').textContent = base;
    $('adjust-score').textContent = (adj.score >= 0 ? '+' : '') + adj.score;
    $('result-message').innerHTML = k
      ? `通常計算は <strong>${normalTotal}点</strong>ですが、区分Kにより最終点を<strong>1点</strong>として試算しています。`
      : '令和8年度の公式基準に基づく試算です。';

    const lines = [
      ['保護者1：'+g1.label,g1.score],
      ['保護者2：'+g2.label,g2.score],
      ['基礎点数（2人のうち低い方を採用）',base],
      ...adj.lines
    ];
    let detail = lines.map(([label,s]) => `<div class="result-line"><span>${esc(label)}</span><strong>${label.startsWith('基礎点数（') ? '' : (s>0?'+':'')}${s}点</strong></div>`).join('');
    if (k) detail += `<div class="result-line"><span>K 合計1点まで減点</span><strong>→ 1点</strong></div>`;
    warnings.forEach(w => detail += `<div class="result-warning">${esc(w)}</div>`);
    detail += `<div class="result-warning">この点数だけで入園可否は判断できません。同点時基準や施設ごとの申込状況も影響します。</div>`;
    $('result-details').innerHTML = detail;
    $('score-result').scrollIntoView({behavior:'smooth',block:'nearest'});
  }

  function resetAll() {
    $('score-form').reset();
    ['1','2'].forEach(n => {
      $(`g${n}-detail`).innerHTML='';
      $(`g${n}-preview`).textContent='基礎点：—';
    });
    setSingleParent();
    $('total-score').textContent='—'; $('base-score').textContent='—'; $('adjust-score').textContent='—';
    $('result-message').textContent='入力後、「点数を計算する」を押してください。';
    $('result-details').innerHTML='';
    window.scrollTo({top:0,behavior:'smooth'});
  }

  async function init() {
    try {
      const res = await fetch('data/admission-score-rules-R8.json', {cache:'no-store'});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      rules = await res.json();

      document.querySelectorAll('.guardian-type').forEach(sel => {
        sel.addEventListener('change', () => renderGuardian(Number(sel.id[1])));
      });
      $('single-parent').addEventListener('change', setSingleParent);
      $('calculate').addEventListener('click', calculate);
      $('reset-score').addEventListener('click', resetAll);
      setSingleParent();
    } catch (e) {
      console.error(e);
      $('rules-error').hidden = false;
      $('calculate').disabled = true;
    }
  }
  window.addEventListener('DOMContentLoaded', init);
})();
