import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../web/app.js',import.meta.url),'utf8');
const elements={},handlers={};
const element=id=>elements[id]??={value:'',dataset:{},options:[],hidden:false,addEventListener:(event,fn)=>{handlers[id+':'+event]=fn},appendChild:()=>{}};
const context=vm.createContext({TextEncoder,window:{MGMOD_REMIXES:[]},document:{getElementById:element,addEventListener:(event,fn)=>{handlers[event]=fn},createElement:()=>({})}});
vm.runInContext(source,context);
handlers.DOMContentLoaded();
assert.equal(elements['recall-dstr'].checked,true);
assert.equal(elements['opt-dstr'].disabled,false);
assert.match(elements['options-text'].value,/^dstr 8 /m);
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
