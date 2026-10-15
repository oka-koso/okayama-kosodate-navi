// Run the actual calculator and its registered handlers with a minimal DOM.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.resolve(__dirname,'..');
const rules=JSON.parse(fs.readFileSync(path.join(root,'data/admission-score-rules-R9.json'),'utf8'));
const nodes=new Map();
function get(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,hidden:false,textContent:'',innerHTML:'',handlers:{},addEventListener(t,fn){this.handlers[t]=fn;},querySelectorAll(){return [];},scrollIntoView(){}});return nodes.get(id);}
const document={getElementById:get,querySelectorAll(){return [get('g1-type'),get('g2-type')];},querySelector(sel){const n=sel.match(/#g(\d)-detail/)[1];const detail=get('detail-'+n);return sel.includes('option:checked')?{textContent:detail.value}:detail;}};
get('g1-type').id='g1-type';get('g2-type').id='g2-type';
let init;
const ctx=vm.createContext({document,window:{addEventListener(t,fn){init=fn;},scrollTo(){}},console,fetch:async()=>({ok:true,json:async()=>rules})});
vm.runInContext(fs.readFileSync(path.join(root,'js/score-calculator.js'),'utf8'),ctx);
function reset(){for(const n of nodes.values()){n.value='';n.checked=false;}get('score-form').reset=()=>{for(const n of nodes.values()){n.value='';n.checked=false;}};get('reset-score').handlers.click();}
function guardian(n,type,value=''){get(`g${n}-type`).value=type;get(`detail-${n}`).value=value;get(`g${n}-type`).handlers.change();}
function check(base,total){get('calculate').handlers.click();assert.equal(String(get('base-score').textContent),String(base));assert.equal(String(get('total-score').textContent),String(total));}
(async()=>{await init();
for(const [other,expected] of [['emp140',20],['emp120',19],['emp48',14]]){reset();guardian(1,'employment','emp140');guardian(2,'employment',other);check(expected,expected);assert.match(get('result-details').innerHTML,/保護者2人の合算・最大20点/);}
reset();guardian(1,'employment','emp120');get('single-parent').checked=true;get('single-parent').handlers.change();check(19,22);
get('single-parent').checked=false;get('single-parent').handlers.change();guardian(2,'employment','emp48');check(13,13);
get('adj-G').checked=true;check(13,16);get('grandparents').value='2';check(13,10);get('adj-K').checked=true;check(13,1);assert.match(get('result-message').innerHTML,/10点/);
reset();guardian(1,'employment','emp140');check('—','—');guardian(2,'other');check('—','—');guardian(2,'employment','emp140');get('adj-D').checked=true;check('—','—');
reset();assert.equal(get('total-score').textContent,'—');assert.equal(get('result-details').innerHTML,'');
console.log('PASS: guardian sum 20/19/14, single parent, toggle, adjustments, K, incomplete/individual cases, reset');
})().catch(e=>{console.error(e);process.exit(1);});
