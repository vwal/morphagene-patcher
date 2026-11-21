import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../web/app.js',import.meta.url),'utf8');
const elements={},handlers={};
const element=id=>elements[id]??={value:'',dataset:{},options:[],hidden:false,addEventListener:(event,fn)=>{handlers[id+':'+event]=fn},appendChild:()=>{}};
const context=vm.createContext({TextEncoder,window:{MGMOD_REMIXES:[]},document:{getElementById:element,addEventListener:(event,fn)=>{handlers[event]=fn},createElement:()=>({})}});
vm.runInContext(source,context);
handlers.DOMContentLoaded();
assert.match(elements['options-text'].value,/^\/\/ firmware version 204\+c2\n/);
assert.equal(elements['recall-dstr'].checked,true);
assert.equal(elements['opt-dstr'].disabled,false);
assert.match(elements['options-text'].value,/^dstr 8 /m);
const presetKeys=['mpos','gpos','spos','splc','srrp','jitp','wrbp','fbkp','evop','sosp','vpos'];
const allPresetKeys=[...presetKeys,'trst'];
for(const key of allPresetKeys) {
  assert.equal(elements['recall-'+key].checked,false);
  assert.equal(elements['opt-'+key].disabled,true);
  assert.equal(elements['opt-'+key].value,['splc','trst'].includes(key)?'1':'0');
  assert.doesNotMatch(elements['options-text'].value,new RegExp(`^${key}(?:[ \\t]|$)`,'m'));
}
assert.match(elements['options-text'].value,/^vuni 0 /m);
assert.match(elements['options-text'].value,/^vctr 0 /m);
async function load(text){await handlers['options-file:change']({target:{files:text===null?[]:[{text:async()=>text}]}});return elements['options-text'].value;}
let out=await load('6 46345 0\r\nroot 37 // retained\r\nvsop 1\r\nvrng 1\r\nmcr1 2.00000 // untouched\r\nunknown line\r\n');
assert.match(out,/^root 37 \/\/ retained$/m);
assert.match(out,/^vsop 1$/m);
assert.match(out,/^mcr1 2.00000 \/\/ untouched$/m);
assert.match(out,/^unknown line$/m);
assert.ok(out.startsWith('6 46345 0\n'));
assert.equal(elements['opt-vrng'].value,'1');
for(let n=0;n<=100;n++){out=await load(`6 0 0\nroot ${n}\n`);assert.match(out,new RegExp(`^root ${n}$`,'m'));}
await load('6 0 0\ntape 0\nvrng 1\nroot 93\n');
out=await load('6 0 0\nvsop 0\n');
assert.match(out,/^tape 1 /m);assert.match(out,/^vrng 0 /m);assert.match(out,/^root 50 /m);
assert.equal(elements['opt-gnsm'].value,'0');
out=await load('6 0 0\nroot 101\ntlen 0\nvrng 9\n');
assert.match(out,/^root 50$/m);assert.match(out,/^tlen 8$/m);assert.match(out,/^vrng 0$/m);
out=await load('6 0 0\ndens 1\nvsop 2\nvrng 1\n');assert.match(out,/^dens 1$/m);assert.match(out,/^vsop 2$/m);
assert.equal(elements['opt-dens'].value,'1');
out=await load('6 0 0\ndens 7\n');assert.match(out,/^dens 0$/m);
out=await load('6 0 0\nvqnt 1\noctl 4\nscal 3,5,7,10\n');
assert.equal(elements['opt-vqnt'].value,'1');assert.match(out,/^vqnt 1$/m);
assert.match(out,/^octl 4$/m);assert.match(out,/^scal 3,5,7,10$/m);
out=await load('6 0 0\nvqnt 2\n');assert.match(out,/^vqnt 0$/m);
await load('6 0 0\nvqnt 1\n');out=await load('6 0 0\n');assert.match(out,/^vqnt 0 /m);
await load(null);assert.equal(elements['opt-root'].value,'50');
out=await load('6 46345 0\n// firmware version 204\n// firmware version 155b\nvsop 1\n');
assert.ok(out.startsWith('6 46345 0\n// firmware version 204+c2\n'));
assert.equal((out.match(/^\/\/ firmware version /gm)||[]).length,1);
out=await load(out);assert.equal((out.match(/^\/\/ firmware version /gm)||[]).length,1);
assert.match(out,/^vsop 1$/m);
await load(null);
console.log('PASS web settings: all 101 root values, stock fields, missing/invalid defaults, successive loads');

out=await load('6 0 0\nmlop 1\nmlop 0\nvsop 2\n');
assert.equal((out.match(/^mlop /gm)||[]).length,1);assert.match(out,/^mlop 0$/m);
assert.equal(elements['opt-mlop'].value,'0');assert.equal(elements['opt-vsop'].value,'2');
out=await load('6 0 0\nmlop 1\n');assert.match(out,/^mlop 1$/m);
out=await load('6 0 0\nmlop 9\n');assert.match(out,/^mlop 0$/m);
out=await load('6 0 0\nscal 3,banana\n');assert.match(out,/^scal 0$/m);
out=await load('6 0 0\n\tmlop\t1 // hello\n');assert.match(out,/^mlop 1 \/\/ hello$/m);
console.log('PASS Morph Loop, forward layout, duplicate keys, tabs and invalid scale handling');

for (let n=1;n<=1280;n++) {
  out=await load(`6 0 0\ndstr ${(n/10).toFixed(1)}\n`);
  assert.equal(elements['opt-dstr'].value,String(n/10));
  assert.ok(out.includes(`dstr ${n/10}\n`));
}
for(const bad of ['0','0.0','0.01','0.09','128.1','129','-1','+8','.5','8.','8.00','1e1','nan','0008','8junk']) {
  out=await load(`6 0 0\ndstr ${bad}\n`);assert.match(out,/^dstr 8$/m);
}
out=await load('6 0 0\ndstr 4\ndstr 16\n');assert.equal((out.match(/^dstr /gm)||[]).length,1);assert.match(out,/^dstr 16$/m);
out=await load('6 0 0\n');assert.equal(elements['opt-dstr'].value,'8');
console.log('PASS startup density: all 1280 tenth-step values, invalid fallback, duplicates and missing default');

// Checkbox round trips: no implicit recall when an imported file omits dstr.
function recall(checked) {
  elements['recall-dstr'].checked=checked;
  handlers['recall-dstr:change']();
  return elements['options-text'].value;
}
const activeDensity=text=>text.split(/\r?\n/).filter(line=>/^\s*dstr(?:[ \t]|$)/.test(line));
out=await load('6 46345 0\r\n\tdstr\t2.5 // custom\r\ndstr 16\r\ndens 1\r\nmcr1 2.00000 // stock\r\nunknown line\r\n');
assert.equal(elements['recall-dstr'].checked,true);
assert.equal(elements['opt-dstr'].disabled,false);
assert.equal(elements['opt-dstr'].value,'16');
out=recall(false);
assert.deepEqual(activeDensity(out),[]);
assert.equal(elements['opt-dstr'].disabled,true);
assert.equal(elements['opt-dstr'].value,'16');
assert.match(out,/^dens 1$/m);
assert.match(out,/^mcr1 2\.00000 \/\/ stock$/m);
assert.match(out,/^unknown line$/m);
assert.ok(out.startsWith('6 46345 0\n'));
elements['opt-mlop'].value='1';handlers['opt-mlop:change']();
assert.deepEqual(activeDensity(elements['options-text'].value),[]);
assert.match(elements['options-note'].textContent,/preserves the current density/);
// The actual save action uses the same omitted-key output.
context.saved=[];
vm.runInContext('download = (name, bytes, type) => saved.push({name, bytes, type})',context);
handlers['options-save:click']();
assert.equal(context.saved[0].name,'options.txt');
assert.equal(context.saved[0].type,'text/plain');
assert.equal(new TextDecoder().decode(context.saved[0].bytes),elements['options-text'].value);
const preserved=new TextDecoder().decode(context.saved[0].bytes);
out=recall(true);
assert.equal(activeDensity(out).length,1);
assert.match(out,/^dstr 16 \/\/ custom$/m);
assert.equal(elements['opt-dstr'].disabled,false);
// A saved preserve file remains unchecked when imported again.
out=await load(preserved);
assert.equal(elements['recall-dstr'].checked,false);
assert.equal(elements['opt-dstr'].disabled,true);
assert.deepEqual(activeDensity(out),[]);
out=recall(true);assert.equal(activeDensity(out).length,1);assert.match(out,/^dstr 8 /m);
// Comments and the state line never enable recall; recognized bad values do.
for(const text of ['6 0 0\n//dstr 128\n', 'dstr 128\n//state line is ignored\n', '6 0 0\n']) {
 out=await load(text);assert.equal(elements['recall-dstr'].checked,false);
 assert.equal(elements['opt-dstr'].disabled,true);
 assert.deepEqual(activeDensity(out).slice(text.startsWith('dstr')?1:0),[]);
}
for(const text of ['dstr','dstr 0','dstr 8junk','  dstr\t0.1 // low']) {
 out=await load('6 0 0\n'+text+'\n');assert.equal(elements['recall-dstr'].checked,true);
 assert.equal(activeDensity(out).length,1);
 assert.equal(elements['opt-dstr'].disabled,false);
}
// Fresh snippet/reset restores the default; toggle retains the chosen rate.
out=await load(null);assert.equal(elements['recall-dstr'].checked,true);
assert.match(out,/^dstr 8 /m);
elements['opt-dstr'].value='0.1';handlers['opt-dstr:change']();
out=recall(false);assert.deepEqual(activeDensity(out),[]);
assert.match(elements['options-note'].textContent,/removed automatically/);
out=recall(true);assert.match(out,/^dstr 0\.1 /m);
assert.equal(elements['opt-dstr'].value,'0.1');
console.log('PASS density checkbox: imports, duplicates, omission, saved-file round trips, value retention, snippets and defaults');

const activeKey=(text,key)=>text.split(/\r?\n/).slice(1).filter(line=>new RegExp(`^\\s*${key}(?:[ \\t]|$)`).test(line));
function presetRecall(key,checked) {
  elements['recall-'+key].checked=checked;
  handlers['recall-'+key+':change']();
  return elements['options-text'].value;
}
// All valid integer positions and splice numbers import as explicit recalls.
for(const key of presetKeys) {
  const lo=key==='splc'?1:0, hi=key==='splc'?300:100;
  for(let n=lo;n<=hi;n++) {
    out=await load(`6 0 0\n${key} ${n}\n`);
    assert.equal(elements['recall-'+key].checked,true);
    assert.equal(elements['opt-'+key].disabled,false);
    assert.equal(elements['opt-'+key].value,String(n));
    assert.deepEqual(activeKey(out,key),[`${key} ${n}`]);
  }
  // A missing or invalid last occurrence must not create an implicit preset.
  await load(`6 0 0\n${key} 43\n`);
  for(const bad of ['', '-1', String(hi+1), '1.0', '0.5', '+8', '1e1', 'nan', '8junk', ...(key==='splc'?['0']:[])]) {
    out=await load(`6 0 0\n${key} ${bad}\n`);
    assert.equal(elements['recall-'+key].checked,false);
    assert.equal(elements['opt-'+key].disabled,true);
    assert.equal(elements['opt-'+key].value,'43');
    assert.deepEqual(activeKey(out,key),[]);
  }
  out=await load(`6 0 0\n${key} 12\n\t${key}\t54 // last value\n`);
  assert.equal(elements['opt-'+key].value,'54');
  assert.deepEqual(activeKey(out,key),[`${key} 54`]);
  out=await load(`6 0 0\n${key} 12\n${key} invalid\n`);
  assert.equal(elements['recall-'+key].checked,false);
  assert.equal(elements['opt-'+key].value,'54');
  assert.deepEqual(activeKey(out,key),[]);
  out=await load(`6 0 0\n${key} invalid\n${key} 17\n`);
  assert.equal(elements['recall-'+key].checked,true);
  assert.deepEqual(activeKey(out,key),[`${key} 17`]);
  // The checkbox removes every active duplicate and retains its numeric choice.
  out=presetRecall(key,false);
  assert.deepEqual(activeKey(out,key),[]);
  assert.equal(elements['opt-'+key].value,'17');
  out=presetRecall(key,true);
  assert.deepEqual(activeKey(out,key),[`${key} 17`]);
  out=await load('6 0 0\n');
  assert.equal(elements['recall-'+key].checked,false);
  assert.equal(elements['opt-'+key].value,'17');
  assert.deepEqual(activeKey(out,key),[]);
  // First state line and commented-out keys are preserved and never activate recall.
  const first=`${key} 23`;
  out=await load(`${first}\n//${key} 91\n// ${key} 82\n`);
  assert.ok(out.startsWith(first+'\n'));
  assert.equal(elements['recall-'+key].checked,false);
  assert.deepEqual(activeKey(out,key),[]);
}
console.log('PASS mg204+c2 presets: all 1310 percentage/splice values, invalid/missing omission, duplicates, headers and retained values');

for(const n of [1,2,3,4,6,8,12,16]) {
  out=await load(`6 0 0\ntrst ${n}\n`);
  assert.equal(elements['recall-trst'].checked,true);
  assert.equal(elements['opt-trst'].disabled,false);
  assert.equal(elements['opt-trst'].value,String(n));
  assert.deepEqual(activeKey(out,'trst'),[`trst ${n}`]);
}
for(const bad of ['', '-1','0','5','7','9','10','11','13','14','15','17','1.0','0.5','1e1','8junk']) {
  out=await load(`6 0 0\ntrst ${bad}\n`);
  assert.equal(elements['recall-trst'].checked,false);
  assert.equal(elements['opt-trst'].disabled,true);
  assert.equal(elements['opt-trst'].value,'16');
  assert.deepEqual(activeKey(out,'trst'),[]);
}
out=await load('6 0 0\ntrst 3\n\ttrst\t12 // duplicate\n');
assert.deepEqual(activeKey(out,'trst'),['trst 12']);
out=presetRecall('trst',false);
assert.deepEqual(activeKey(out,'trst'),[]);
assert.equal(elements['opt-trst'].value,'12');
out=presetRecall('trst',true);
assert.deepEqual(activeKey(out,'trst'),['trst 12']);
out=await load('6 0 0\n');
assert.equal(elements['recall-trst'].checked,false);
assert.equal(elements['opt-trst'].value,'12');
out=await load('6 0 0\ntrst 4\ntrst 5\n');
assert.equal(elements['recall-trst'].checked,false);
assert.deepEqual(activeKey(out,'trst'),[]);
out=await load('trst 8\n//trst 6\n');
assert.ok(out.startsWith('trst 8\n'));
assert.equal(elements['recall-trst'].checked,false);
assert.deepEqual(activeKey(out,'trst'),[]);
console.log('PASS Turing step recall: eight allowed values, excluded integers, duplicate removal, omission and retained choice');

// Each preset is independent; only selected keys reach the actual saved file.
out=await load('6 46345 0\r\nmpos 10 // preserve comment\r\nmpos 20\r\ngpos 30\r\ngpos 40\r\nspos 50\r\nsplc 6\r\nmcr1 2.00000 // stock\r\nunknown line\r\n');
presetRecall('gpos',false);
presetRecall('splc',false);
elements['opt-mlop'].value='1';handlers['opt-mlop:change']();
out=elements['options-text'].value;
assert.deepEqual(activeKey(out,'mpos'),['mpos 20 // preserve comment']);
assert.deepEqual(activeKey(out,'spos'),['spos 50']);
assert.deepEqual(activeKey(out,'gpos'),[]);
assert.deepEqual(activeKey(out,'splc'),[]);
assert.ok(out.startsWith('6 46345 0\n'));
assert.match(out,/^mcr1 2\.00000 \/\/ stock$/m);
assert.match(out,/^unknown line$/m);
handlers['options-save:click']();
const presetSave=context.saved.at(-1);
assert.equal(presetSave.name,'options.txt');
assert.equal(presetSave.type,'text/plain');
assert.equal(new TextDecoder().decode(presetSave.bytes),out);
out=await load(new TextDecoder().decode(presetSave.bytes));
for(const key of allPresetKeys) assert.equal(elements['recall-'+key].checked,['mpos','spos'].includes(key));
assert.equal(elements['opt-gpos'].value,'40');
assert.equal(elements['opt-splc'].value,'6');
out=presetRecall('gpos',true);
assert.equal(activeKey(out,'gpos').length,1);
assert.match(out,/^gpos 40 /m);
out=await load(null);
for(const key of allPresetKeys) {
  assert.equal(elements['recall-'+key].checked,false);
  assert.equal(elements['opt-'+key].disabled,true);
  assert.equal(elements['opt-'+key].value,['splc','trst'].includes(key)?'1':'0');
  assert.deepEqual(activeKey(out,key),[]);
}
console.log('PASS mg204+c2 preset selection: independent checkboxes, saved-file round trip, absent keys stay omitted and reset defaults');

// Mode changes retain separate effect amounts and primary/secondary controls.
out=await load('6 46345 0\nsrrp 12\nwrbp 34\njitp 56\nfbkp 78\nevop 90\ntrst 6\nsosp 43\nvpos 65\nsplc 300\n');
for(const [key,n] of [['fxsl','1'],['fxsl','2'],['fxsl','0'],['tape','0'],['tape','1'],['sldm','1'],['dens','1']]) {
  elements['opt-'+key].value=n;handlers['opt-'+key+':change']();
  out=elements['options-text'].value;
  for(const [preset,value] of [['srrp',12],['wrbp',34],['fbkp',78],['sosp',43],['trst',6],['vpos',65],['splc',300]])
    assert.deepEqual(activeKey(out,preset),[`${preset} ${value}`]);
}
out=presetRecall('fbkp',false);
assert.deepEqual(activeKey(out,'fbkp'),[]);
assert.deepEqual(activeKey(out,'sosp'),['sosp 43']);
out=presetRecall('srrp',false);
assert.deepEqual(activeKey(out,'srrp'),[]);
assert.deepEqual(activeKey(out,'wrbp'),['wrbp 34']);
handlers['options-save:click']();
out=await load(new TextDecoder().decode(context.saved.at(-1).bytes));
for(const key of ['fbkp','srrp']) {
  assert.equal(elements['recall-'+key].checked,false);
  assert.deepEqual(activeKey(out,key),[]);
}
for(const key of ['wrbp','jitp','evop','trst','sosp','vpos','splc'])
  assert.equal(elements['recall-'+key].checked,true);
assert.deepEqual(activeKey(out,'splc'),['splc 300']);
console.log('PASS mg204+c2 independent recalls: effect modes, feedback versus main mix, Turing priority and unchanged configured splice number');

for(const key of ['vuni','vctr']) {
  for(const n of [0,1]) {
    out=await load(`6 0 0\n${key} ${n}\n`);
    assert.equal(elements['opt-'+key].value,String(n));
    assert.deepEqual(activeKey(out,key),[`${key} ${n}`]);
  }
  for(const bad of ['-1','2','0.5','1.0','text','']) {
    out=await load(`6 0 0\n${key} ${bad}\n`);
    assert.equal(elements['opt-'+key].value,'0');
    assert.deepEqual(activeKey(out,key),[`${key} 0`]);
  }
  out=await load(`6 0 0\n${key} 1\n${key} 0\n`);
  assert.deepEqual(activeKey(out,key),[`${key} 0`]);
}

// An older normal mount dispatches each 63-byte FatFs chunk independently.
const legacyRangeComment = '//Varispeed range: 0 stock, 1 extended: vsop 0/1 +/-4x; vsop 2 forward stop to 8x with scale lock';
const shortRangeComment = '//0 stock, 1 +/-4x bidirectional or 0-8x forward';
const stockKeys = new Set('vsop pmod omod rmod cvop ckop rsop pmin inop gnsm mcr1 mcr2 mcr3 step'.split(' '));
const editorKeys = new Set(vm.runInContext('FIELDS',context));
for (const range of [0, 1]) {
  const legacyLine = `vrng ${range} ${legacyRangeComment}`;
  assert.ok(legacyLine.slice(63).startsWith('vsop 2'));
  await load(`6 46345 0\r\nvsop 2\r\n${legacyLine}\r\n`);
  for (const key of ['dstr', ...allPresetKeys]) elements['recall-'+key].checked = true;
  elements['opt-vsop'].value = '1';
  handlers['opt-vsop:change']();
  handlers['options-save:click']();
  const saved = new TextDecoder().decode(context.saved.at(-1).bytes);
  assert.deepEqual(activeKey(saved,'vsop'), ['vsop 1']);
  assert.deepEqual(activeKey(saved,'vrng'), [`vrng ${range} ${shortRangeComment}`]);
  for (const line of saved.split('\n')) {
    for (let i = 63; i < line.length; i += 63) {
      const chunk = line.slice(i);
      assert.ok(!stockKeys.has(chunk.slice(0,4)), line);
      assert.ok(!(editorKeys.has(chunk.slice(0,4)) && /^....[ \t]\d/.test(chunk)), line);
    }
  }
  assert.equal(await load(saved), saved);
}
out = await load('6 0 0\nvrng 1 // my performance note\n');
assert.deepEqual(activeKey(out,'vrng'), ['vrng 1 // my performance note']);
out = await load(null);
assert.match(out, /^vrng 0 \/\/0 stock, 1 \+\/-4x bidirectional or 0-8x forward$/m);
console.log('PASS older firmware compatibility: correct range comments on import, export and fresh snippets');

// Generated markup exposes native, labelled controls with firmware bounds.
const html=fs.readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
const htmlIds=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(htmlIds).size,htmlIds.length);
for(const key of presetKeys) {
  const checkbox=html.match(new RegExp(`<input id="recall-${key}"[^>]*>`))?.[0];
  const input=html.match(new RegExp(`<input id="opt-${key}"[^>]*>`))?.[0];
  assert.ok(checkbox);
  assert.match(checkbox,/type="checkbox"/);
  assert.match(checkbox,new RegExp(`aria-describedby="help-${key}"`));
  assert.doesNotMatch(checkbox,/\bchecked\b/);
  assert.match(input,/type="number"/);
  assert.match(input,new RegExp(`min="${key==='splc'?1:0}" max="${key==='splc'?300:100}" step="1"`));
  assert.match(input,/\bdisabled\b/);
  assert.ok(html.includes(`for="recall-${key}"`));
  assert.ok(html.includes(`id="help-${key}"`));
}
for(const key of ['vuni','vctr']) {
  assert.ok(html.includes(`<select id="opt-${key}" aria-describedby="help-${key}">`));
  assert.ok(html.includes(`for="opt-${key}"`));
}
const stepSelect=html.match(/<select id="opt-trst"[^>]*>(.*?)<\/select>/)?.[0];
assert.ok(stepSelect);
assert.match(stepSelect,/\bdisabled\b/);
assert.match(stepSelect,/aria-describedby="help-trst"/);
assert.deepEqual([...stepSelect.matchAll(/<option value="(\d+)"/g)].map(m=>Number(m[1])),[1,2,3,4,6,8,12,16]);
assert.match(html,/<label[^>]*for="recall-trst"/);
assert.match(html,/<input id="recall-trst" type="checkbox" aria-describedby="help-trst">/);
assert.match(html,/A number above the loaded reel count selects its last splice while keeping your configured number/);
assert.match(html,/a knob position, not a playback-speed percentage/);
assert.match(html,/they cannot run together/);
assert.match(html,/dens 1 takes priority over the Turing rate/);
const content=JSON.parse(fs.readFileSync(new URL('../web/site-content.json',import.meta.url),'utf8'));
assert.deepEqual(content.fields.map(field=>field[0]).sort(),Array.from(vm.runInContext('FIELDS',context)).sort());
assert.match(html,/no extra flat zone is added/);
assert.match(html,/Morphagene mg204\+c2/);
assert.doesNotMatch(html,/PRIVATE|EXPERIMENTAL|upcoming|await.*hardware/);
for(const id of ['firmware','remix','build-card','build-wav']) assert.ok(htmlIds.includes(id));
assert.match(html,/mg204\+c2\.wav/);
assert.match(html,/<details><summary>Version by version<\/summary>/);
assert.doesNotMatch(html,/<details[^>]*\bopen\b/);
assert.match(html,/This project contains carefully tested AI-generated code\./);
assert.match(html,/Independent customization\. Not an official Make Noise release\./);
const order=content.fields.map(field=>field[0]);
assert.equal(order.indexOf('mpos'),order.indexOf('mlop')+1);
assert.equal(order.indexOf('gpos'),order.indexOf('gnsm')+1);
assert.equal(order.indexOf('fbkp'),order.indexOf('tape')+1);
assert.equal(order.indexOf('wrbp'),order.indexOf('srrp')+1);
assert.match(html,/0% = fully counterclockwise, 50% = noon, 100% = fully clockwise/);
assert.match(html,/10% selects the stock seamless-loop setting \(9-11%\)/);
assert.match(html,/0% and 1% play the longest Genes/);
assert.match(html,/100% gives the shortest Genes/);
assert.match(html,/Bidirectional — classic/);
assert.match(html,/Bidirectional — V\/oct/);
assert.match(html,/attenuverter carefully adjusted/);
console.log('PASS mg204+c2 editor: grouped controls, percentage guidance, version history, disclosures and patcher');
