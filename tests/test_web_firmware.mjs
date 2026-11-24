import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {webcrypto} from 'node:crypto';
const root=path.resolve(import.meta.dirname,'..');
const buildDir = process.env.MGMOD_BUILD_DIR || path.join(root, 'build', 'release');
const release = JSON.parse(fs.readFileSync(path.join(root, 'web', 'release.json'), 'utf8'));
const elements={},handlers={};
const element=id=>elements[id]??={value:'',dataset:{},hidden:false,
 addEventListener:(event,fn)=>{handlers[id+':'+event]=fn},
 appendChild(node){if(id==='remix'&&!this.value)this.value=node.value;}};
const ctx=vm.createContext({TextEncoder,Uint8Array,Int16Array,DataView,ArrayBuffer,crypto:webcrypto,setTimeout,
 window:{},document:{addEventListener:(event,fn)=>{handlers[event]=fn},getElementById:element,createElement:()=>({})}});
for (const name of ['remixes.js', 'page.js', 'app.js']) {
  vm.runInContext(fs.readFileSync(path.join(root,'web',name),'utf8'),ctx);
}
assert.ok(process.env.MGMOD_FIRMWARE && process.env.MGMOD_WAV,
 'Set MGMOD_FIRMWARE to the official decoded raw image and MGMOD_WAV to the official mg204.wav. Build full into MGMOD_BUILD_DIR or build/release first.');
const raw=fs.readFileSync(process.env.MGMOD_FIRMWARE);
const official=fs.readFileSync(process.env.MGMOD_WAV);
ctx.file={name:'mg204.wav',arrayBuffer:async()=>official.buffer.slice(official.byteOffset,official.byteOffset+official.byteLength)};
ctx.expected=raw;
const decoded=await vm.runInContext('readFirmware(file)',ctx);
assert.deepEqual(Buffer.from(decoded),raw);
ctx.decoded=decoded;vm.runInContext('stockImage=decoded',ctx);
const image=await vm.runInContext('buildRemix(window.MGMOD_REMIXES[0])',ctx);
assert.deepEqual(Buffer.from(image),fs.readFileSync(path.join(buildDir, 'mg204-full.bin')));
assert.equal(release.release, 'mg204+c6');
assert.equal(release.raw_image_bytes, image.length);
assert.equal(release.raw_image_sha256, Buffer.from(await webcrypto.subtle.digest('SHA-256',image)).toString('hex'));
ctx.built=image;
assert.deepEqual(Buffer.from(vm.runInContext('cardFile(built)',ctx)),fs.readFileSync(path.join(buildDir, 'mgmod.bin')));
// Exercise the actual download handlers, including the public release filename.
ctx.saved=[];
vm.runInContext('download = (name, bytes, type) => saved.push({name, bytes, type})',ctx);
handlers.DOMContentLoaded();
await handlers['build-card:click']();
await handlers['build-wav:click']();
assert.equal(ctx.saved.length,2);
assert.equal(ctx.saved[0].name,'mgmod.bin');
assert.equal(ctx.saved[0].name,release.sd_download);
assert.deepEqual(Buffer.from(ctx.saved[0].bytes),fs.readFileSync(path.join(buildDir, 'mgmod.bin')));
assert.equal(ctx.saved[1].name,'mg204+c6.wav');
assert.equal(ctx.saved[1].name,release.wav_download);
assert.equal(ctx.saved[1].type,'audio/wav');
fs.writeFileSync(path.join(buildDir, 'browser.wav'),Buffer.from(ctx.saved[1].bytes));
const corrupted=Buffer.from(official);corrupted.fill(0,0,12);
ctx.file={name:'mg204.wav',arrayBuffer:async()=>corrupted.buffer.slice(corrupted.byteOffset,corrupted.byteOffset+corrupted.byteLength)};
await assert.rejects(()=>vm.runInContext('readFirmware(file)',ctx));
// Selecting another file while a card reader is busy must leave the newest validation in control.
const pickFirmware = file => handlers['firmware:change']({target:{files:[file]}});
const pending = Promise.withResolvers();
const stale = pickFirmware({name:'older.wav', arrayBuffer:() => pending.promise});
await pickFirmware(ctx.file);
assert.equal(elements['firmware-status'].dataset.kind, 'error');
pending.resolve(official.buffer.slice(official.byteOffset,official.byteOffset+official.byteLength));
await stale;
assert.equal(elements['build-buttons'].hidden, true);
assert.equal(vm.runInContext('stockImage',ctx), null);
const bad=Buffer.from(raw);bad[1234]^=1;ctx.bad=bad;
vm.runInContext('stockImage=bad',ctx);
await assert.rejects(()=>vm.runInContext('buildRemix(window.MGMOD_REMIXES[0])',ctx));
console.log('PASS official WAV decode, patched raw/SD equivalence, mg204+c6 download handlers, audio encoding, corrupted input rejection');
