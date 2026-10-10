const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const root=require('path').resolve(__dirname,'..');
const read=p=>fs.readFileSync(root+'/'+p,'utf8');
class Clock extends Date {constructor(...args){super(...(args.length?args:['2026-10-10T22:30:00Z']));}}
async function run({offline=false,limit=0}={}){
 const list={dataset:{limit:String(limit)},innerHTML:'HTML fallback'};
 const buttons=['','園選び・保活','入園申込・手続き','入園準備・通園生活'].map(category=>({dataset:{bibourokuCategory:category},setAttribute(name,value){this[name]=value;}}));
 const filters={hidden:true,innerHTML:'',querySelectorAll:()=>buttons,contains:button=>buttons.includes(button),addEventListener(type,callback){this.click=callback;}};
 const count={textContent:''};
 const items=JSON.parse(read('data/bibouroku.json'));
 items.push({title:'FUTURE_DAY',published:'2026-10-12',category:'園選び・保活',url:'future.html'});
 items.push({title:'FUTURE_HOUR',published:'2026-10-11',publish_at:'2026-10-11T12:00:00+09:00',category:'入園準備・通園生活',url:'later.html'});
 const context=vm.createContext({Date:Clock,Intl,console:{warn(){}},document:{readyState:'complete',documentElement:{dataset:{}},querySelectorAll:()=>[list],querySelector:selector=>selector.includes('filters')?filters:count},fetch:async()=>({ok:!offline,status:503,json:async()=>items})});
 vm.runInContext(read('js/bibouroku.js'),context);
 await new Promise(resolve=>setImmediate(resolve));
 return {list,filters,count,buttons};
}
(async()=>{
 const e=await run();
 assert.equal(e.filters.hidden,false);assert.match(e.count.textContent,/13記事/);
 assert.doesNotMatch(e.list.innerHTML,/FUTURE_DAY|FUTURE_HOUR/);
 assert.match(e.list.innerHTML,/hoikuen-erabikata-part3/); // JST already reaches its publication day.
 for(const [index,total] of [[1,8],[2,4],[3,1],[0,13]]){
  const button=e.buttons[index];e.filters.click({target:{closest:()=>button}});
  assert.match(e.count.textContent,new RegExp(`${total}記事`));
  assert.equal((e.list.innerHTML.match(/class="bibouroku-card"/g)||[]).length,total);
  assert.equal(button['aria-pressed'],'true');
  assert.doesNotMatch(e.list.innerHTML,/FUTURE_DAY|FUTURE_HOUR/);
 }
 const limited=await run({limit:3});assert.equal((limited.list.innerHTML.match(/class="bibouroku-card"/g)||[]).length,3);assert.equal(limited.filters.hidden,true);
 const offline=await run({offline:true});assert.equal(offline.list.innerHTML,'HTML fallback');assert.equal(offline.filters.hidden,true);
 console.log('PASS: JST reserved dates/times, 3-category filtering/counts, home limit, offline fallback');
})().catch(error=>{console.error(error);process.exit(1);});
