const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const root=require('path').resolve(__dirname,'..');
const read=p=>fs.readFileSync(root+'/'+p,'utf8');
let now=Date.parse('2026-10-10T23:55:00+09:00');
class Clock extends Date {constructor(...a){super(...(a.length?a:[now]));}static now(){return now;}}
const monthly={availability_for:'令和8年11月',availability_as_of:'令和8年9月17日時点',by_facility_id:{one:{0:'×'}}};
const april={availability_for:'令和9年4月',availability_as_of:'令和8年10月14日時点',by_facility_id:{one:{0:'○'}}};
const master={facilities:[{id:'one',name:'園',lat:34.6,lon:133.9,services_source_as_of:'令和7年8月時点',services_source:'https://www.city.okayama.jp/service.pdf',services:{extended:true}}]};
function environment(data,url=''){
 const nodes=new Map();const get=s=>{if(!nodes.has(s))nodes.set(s,{textContent:'',innerHTML:'',hidden:false,href:''});return nodes.get(s);};
 const context=vm.createContext({Date:Clock,Intl,URLSearchParams,console,encodeURIComponent,setTimeout:()=>{},setInterval:()=>{},location:{search:url},window:{addEventListener:()=>{}},document:{querySelector:get,getElementById:s=>get('#'+s)},fetch:async path=>({ok:true,json:async()=>data[path.split('?')[0]]||null})});
 vm.runInContext(read('js/availability-status.js'),context);
 return {context,nodes,get};
}
(async()=>{
 for(const availableApril of [false,true])for(const query of ['', '?availability=monthly']){
  const e=environment({'data/facility_master.json':master,'data/availability_monthly.json':monthly,'data/availability_april.json':availableApril?april:null},query);
  vm.runInContext(read('js/facilities.js'),e.context);await vm.runInContext('loadData()',e.context);
  assert.equal(vm.runInContext('activeAvailabilityKey',e.context),availableApril&&!query?'april':'monthly');
  assert.equal(e.get('#availability-switcher').hidden,!availableApril);
  const content=vm.runInContext('servicesHtml(allFacilities[0])',e.context);
  assert.match(content,/令和7年8月時点/);assert.match(content,/岡山市の掲載資料/);
  const av=vm.runInContext('availabilityHtml(allFacilities[0])',e.context);
  assert.match(av,availableApril&&!query?/令和9年4月/:/令和8年11月/);
  assert.equal(vm.runInContext("aprilDatasetIsRelevant({availability_for:'令和8年4月',by_facility_id:{}})",e.context),false);
 }
 for(const availableApril of [false,true]){
  const e=environment({'data/facility_master.json':master,'data/availability_monthly.json':monthly,'data/availability_april.json':availableApril?april:null});
  const code=read('js/home-map.js').replace("window.addEventListener('DOMContentLoaded'", "window.testing={loadData,mode:()=>activeAvailabilityKey};window.addEventListener('DOMContentLoaded'");
  vm.runInContext(code,e.context);await e.context.window.testing.loadData();
  assert.equal(e.context.window.testing.mode(),availableApril?'april':'monthly');
  assert.equal(e.get('#home-map-availability-switcher').hidden,!availableApril);
 }
 const data={
  deadlines:[
   {target_year:2026,target_month:11,target_label:'令和8年11月',deadline_date:'2026-10-01',deadline_iso_jst:'2026-10-01T17:15:00+09:00'},
   {target_year:2026,target_month:12,target_label:'令和8年12月',deadline_date:'2026-11-02',deadline_iso_jst:'2026-11-02T17:15:00+09:00'},
   {target_year:2027,target_month:1,target_label:'令和9年1月',deadline_date:'2026-12-01',deadline_iso_jst:'2026-12-01T17:15:00+09:00'}
  ],availability_for:monthly.availability_for,availability_as_of:monthly.availability_as_of,
  checked_at:'2026-10-10T23:00:00+09:00',publications_checked_at:'2026-10-10T23:00:00+09:00',check_status:'verified',publication_check_status:'verified',availability_publications:[]
 };
 const e=environment({'data/midyear_admission.json':data});
 let init,tick;e.context.window.addEventListener=(type,fn)=>{init=fn;};e.context.setInterval=fn=>{tick=fn;};
 vm.runInContext(read('js/midyear-admission.js'),e.context);await init();
 assert.match(e.get('#midyear-target').textContent,/12月/);
 assert.match(e.get('#midyear-deadline').textContent,/11月2日/);
 assert.match(e.get('#midyear-availability-target').textContent,/11月/);
 assert.match(e.get('#midyear-availability-status').textContent,/終了/);
 assert.equal(e.get('#midyear-availability-link').href,'hoikuen.html?availability=monthly');
 assert.match(e.get('#midyear-next-availability').textContent,/12月.*未公開/);
 const status=e.context.window.OKNAvailability;
 const atAudit=Date.parse('2026-10-11T07:30:00+09:00');
 data.availability_publication_plans=[{target_year:2026,target_month:12,publish_date:'2026-10-26'}];
 let s=status.describe(monthly,'monthly',data,atAudit);
 assert.equal(s.closed,true);assert.match(s.title,/直近に公表された参考資料/);
 assert.match(s.nextText,/11月2日/);assert.match(s.nextText,/10月26日/);
 assert.match(s.nextText,/未公開/);assert.equal(s.warning,'');
 const failed={...data,publication_check_status:'failed'};
 s=status.describe(monthly,'monthly',failed,atAudit);
 assert.match(s.warning,/失敗/);assert.doesNotMatch(s.nextText,/未公開/);
 const stale={...data,publications_checked_at:'2026-10-01T00:00:00+09:00'};
 assert.doesNotMatch(status.describe(monthly,'monthly',stale,atAudit).nextText,/未公開/);
 const newMonthly={...monthly,availability_for:'令和8年12月'};
 const published={...data,availability_publications:[{target_year:2026,target_month:12,url:'https://example.test/monthly.pdf'}]};
 assert.match(status.describe(monthly,'monthly',published,atAudit).nextText,/反映を確認中/);
 assert.match(status.describe(newMonthly,'monthly',published,atAudit).nextText,/公表資料を表示/);
 assert.equal(status.describe(april,'april',data,atAudit).closed,false);
 assert.equal(status.describe(april,'april',data,atAudit).nextText,'');
 // A missing monthly file must not prevent valid April data or explicit monthly mode.
 for(const query of ['', '?availability=monthly']){
  const env=environment({'data/facility_master.json':master,'data/availability_april.json':april,'data/midyear_admission.json':failed},query);
  vm.runInContext(read('js/facilities.js'),env.context);await vm.runInContext('loadData()',env.context);
  assert.equal(vm.runInContext('activeAvailabilityKey',env.context),query?'monthly':'april');
  assert.match(env.get('#availability-summary').innerHTML,query?/表示できません/:/令和9年4月/);
  if(query)assert.match(env.get('#availability-summary').innerHTML,/読込みに失敗/);
 }
 // The same state wording is rendered by both home and full MAP.
 const pageData={'data/facility_master.json':master,'data/availability_monthly.json':monthly,'data/midyear_admission.json':data};
 const full=environment(pageData);
 vm.runInContext(read('js/facilities.js'),full.context);await vm.runInContext('loadData()',full.context);
 const home=environment(pageData);
 const code=read('js/home-map.js').replace("window.addEventListener('DOMContentLoaded'", "window.testing={loadData};window.addEventListener('DOMContentLoaded'");
 vm.runInContext(code,home.context);await home.context.window.testing.loadData();
 assert.equal(home.get('#home-map-summary').innerHTML,full.get('#availability-summary').innerHTML);
 // A search returning no rows closes any previous popup and provides a recovery hint.
 let closed=0;full.context.closePopup=()=>{closed++;};
 vm.runInContext('map={closePopup, invalidateSize(){}}',full.context);
 full.get('#q').value='存在しない施設';vm.runInContext('render()',full.context);
 assert.equal(closed,1);assert.equal(full.get('#count').textContent,0);
 assert.match(full.get('#facility-list').innerHTML,/条件に合う施設が見つかりません/);
 now=Date.parse('2026-11-02T17:15:00+09:00');tick();assert.match(e.get('#midyear-target').textContent,/12月/);
 now+=1000;tick();assert.match(e.get('#midyear-target').textContent,/令和9年1月/);
 data.check_status='failed';tick();assert.equal(e.get('#midyear-update-warning').hidden,false);
 assert.match(e.get('#midyear-update-warning').textContent,/最後に確認/);
 console.log('PASS: monthly rollover, publication/failure distinction, common summaries, zero-results popup, April-only/default/manual-mode regressions');
})().catch(e=>{console.error(e);process.exit(1)});
