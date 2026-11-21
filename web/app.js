// morphagene-mods web builder. Everything runs in this page: the firmware you
// choose is read locally and never uploaded.
'use strict';

const STOCK_SHA256 = '44037eb2cf24b5fc411135e487a6fa226498a8478db981659bb53341cb967609';
const $ = (id) => document.getElementById(id);
let stockImage = null;

// ---------- helpers ----------
async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function hex(s) {
  const out = new Uint8Array(s.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(s.substr(i * 2, 2), 16);
  return out;
}

function download(name, bytes, type) {
  const url = URL.createObjectURL(new Blob([bytes], { type: type || 'application/octet-stream' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function status(id, text, kind) {
  const el = $(id);
  el.textContent = text;
  el.dataset.kind = kind || '';
}

// ---------- read the official firmware ----------
function wavSamples(buffer) {
  const v = new DataView(buffer);
  const tag = (o) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));
  if (tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('not a WAV file');
  let o = 12, fmt = null;
  while (o + 8 <= buffer.byteLength) {
    const id = tag(o), size = v.getUint32(o + 4, true);
    if (id === 'fmt ') {
      fmt = { format: v.getUint16(o + 8, true), channels: v.getUint16(o + 10, true),
              rate: v.getUint32(o + 12, true), bits: v.getUint16(o + 22, true) };
    } else if (id === 'data') {
      if (!fmt || fmt.format !== 1 || fmt.channels !== 1 || fmt.rate !== 48000 || fmt.bits !== 16) {
        throw new Error('expected a mono 16-bit 48 kHz WAV');
      }
      return new Int16Array(buffer.slice(o + 8, o + 8 + size));
    }
    o += 8 + size + (size & 1);
  }
  throw new Error('no audio data in the WAV');
}

function decodeUpdateWav(samples) {
  // stm-audio-bootloader QPSK: 6 kHz carrier, 8 samples per symbol, 2 bits per symbol.
  const symbols = [];
  for (let o = 48000; o + 7 < samples.length; o += 8) {
    symbols.push((samples[o + 2] > 0 ? 1 : 0) + 2 * (samples[o] > 0 ? 1 : 0));
  }
  const stream = new Uint8Array(symbols.length >> 2);
  for (let j = 0; j < stream.length; j++) {
    stream[j] = (symbols[4 * j] << 6) | (symbols[4 * j + 1] << 4) | (symbols[4 * j + 2] << 2) | symbols[4 * j + 3];
  }
  const out = [];
  for (let i = 0; i + 16 + 256 + 4 <= stream.length; i++) {
    let header = true;
    for (let k = 0; k < 16 && header; k++) header = stream[i + k] === (k < 8 ? 0 : k < 12 ? 0x99 : 0xcc);
    if (!header) continue;
    const data = stream.slice(i + 16, i + 16 + 256);
    const crc = ((stream[i + 272] << 24) | (stream[i + 273] << 16) | (stream[i + 274] << 8) | stream[i + 275]) >>> 0;
    if (crc32(data) !== crc) throw new Error('a packet failed its CRC check');
    out.push(data);
    i += 16 + 256 + 4 - 1;
  }
  const image = new Uint8Array(out.length * 256);
  out.forEach((p, n) => image.set(p, n * 256));
  return image;
}

async function readFirmware(file) {
  const buffer = await file.arrayBuffer();
  const head = new Uint8Array(buffer, 0, 4);
  const isWav = String.fromCharCode(...head) === 'RIFF';
  const image = isWav ? decodeUpdateWav(wavSamples(buffer)) : new Uint8Array(buffer);
  const digest = await sha256(image);
  if (digest !== STOCK_SHA256) {
    throw new Error('This is not the unmodified official mg204 firmware (fingerprint ' + digest.slice(0, 12) + '…).');
  }
  return image;
}

// ---------- build ----------
async function buildRemix(remix) {
  const image = new Uint8Array(remix.size).fill(0xff);
  image.set(stockImage.subarray(0, Math.min(stockImage.length, remix.size)));
  for (const [offset, bytes] of remix.runs) image.set(hex(bytes), offset);
  const digest = await sha256(image);
  if (digest !== remix.sha256) throw new Error('build check failed: the result does not match the reference build');
  return image;
}

function cardFile(image) {
  const out = new Uint8Array(image.length + 12);
  out.set(image);
  out.set([0x4d, 0x47, 0x4d, 0x44], image.length);        // "MGMD"
  const v = new DataView(out.buffer);
  v.setUint32(image.length + 4, image.length, true);
  v.setUint32(image.length + 8, crc32(image), true);
  return out;
}

function updateWav(image) {
  // Same framing as the official update: 1 s silence, 1 s blank, 256-byte
  // packets + CRC32, 10 ms after every 1,024 bytes, 1 s blank.
  const PAGE = 1024, PACKET = 256, RATE = 48000, RATIO = 8;
  let data = image;
  if (data.length % PAGE) {
    data = new Uint8Array(data.length + PAGE - (data.length % PAGE)).fill(0xff);
    data.set(image);
  }
  const symbols = [];
  const blank = (n) => { for (let i = 0; i < n; i++) symbols.push(0); };
  blank(6000);
  for (let o = 0; o < data.length; o += PACKET) {
    const packet = data.subarray(o, o + PACKET);
    const crc = crc32(packet);
    const bytes = [0, 0, 0, 0, 0, 0, 0, 0, 0x99, 0x99, 0x99, 0x99, 0xcc, 0xcc, 0xcc, 0xcc, ...packet,
                   crc >>> 24, (crc >>> 16) & 0xff, (crc >>> 8) & 0xff, crc & 0xff];
    for (const b of bytes) symbols.push((b >> 6) & 3, (b >> 4) & 3, (b >> 2) & 3, b & 3);
    if ((o / PACKET + 1) % (PAGE / PACKET) === 0) blank(60);
  }
  blank(6000);
  const n = RATE + symbols.length * RATIO;
  const out = new Uint8Array(44 + n * 2);
  const v = new DataView(out.buffer);
  const text = (o, s) => { for (let i = 0; i < s.length; i++) out[o + i] = s.charCodeAt(i); };
  text(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); text(8, 'WAVE');
  text(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, RATE, true); v.setUint32(28, RATE * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  text(36, 'data'); v.setUint32(40, n * 2, true);
  const w = (2 * Math.PI * 6000) / RATE, s = Math.SQRT1_2;
  let k = 0, p = 44 + RATE * 2;
  for (const sym of symbols) {
    const even = (2 * (sym & 1) - 1) * s, odd = (2 * (sym >> 1) - 1) * s;
    for (let r = 0; r < RATIO; r++, k++, p += 2) {
      const x = even * Math.sin(w * k) + odd * Math.cos(w * k);
      v.setInt16(p, Math.trunc(Math.max(-1, Math.min(1, x)) * 32767), true);
    }
  }
  return out;
}

// ---------- options.txt ----------
const VERSION_HEADER = '// firmware version 204+c2';
const MOD_HEADER = '//Morphagene extended mods';
// In older builds this comment put "vsop 2" at the start of a 63-byte read.
const LEGACY_RANGE_COMMENT = '//Varispeed range: 0 stock, 1 extended: vsop 0/1 +/-4x; vsop 2 forward stop to 8x with scale lock';
// Extended option keys and explanatory comments for generated files.
const KEYS = {
  mpos: '//Morph virtual knob preset: 0-100 percent. 10 selects the stock seamless loop (unclocked/dens 0); 0 gaps with mlop 0. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  gpos: '//Gene Size virtual knob preset: 0-100 percent. 0 and 1 = longest/full splice; 100 = shortest, not a length percentage. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  spos: '//Slide virtual knob preset: integer 0-100 percent. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  vpos: '//Varispeed virtual knob preset: integer 0-100 percent before vsop/vrng/vctr mapping, not a speed ratio. vuni remains the +1x recall gesture.',
  sosp: '//Primary S.O.S. mix virtual knob preset: integer 0-100 percent. Separate from the SHIFT+S.O.S. feedback preset fbkp.',
  splc: '//Splice recall: integer 1-300, 1 is the first splice. Above the reel count selects its last splice; the configured number is retained. Omit to preserve selection on settings-only reload.',
  srrp: '//Sample-rate reduction virtual knob preset: integer 0-100 percent. Used with fxsl 1; retained separately from warble. SRR and warble cannot run together.',
  jitp: '//Jitter / Turing spread virtual knob preset: integer 0-100 percent for SHIFT+Slide.',
  wrbp: '//Warble virtual knob preset: integer 0-100 percent. Used with fxsl 2; retained separately from SRR. SRR and warble cannot run together.',
  fbkp: '//SHIFT+S.O.S. feedback virtual knob preset: integer 0-100 percent. tape selects feedback mode; separate from primary S.O.S. mix sosp.',
  evop: '//Turing evolution virtual knob preset: integer 0-100 percent. Used with sldm 1.',
  trst: '//Turing Genes per step preset: 1,2,3,4,6,8,12,16. Used with sldm 1; dens 1 takes priority over the Turing rate.',
  vuni: '//Unity recall: 0 off, 1 hold SHIFT alone >=0.5 seconds and release for forward +1x with pickup. Use with SHIFT jack unpatched.',
  vctr: '//Noon unity mapping: 0 original mapping, 1 +1x at calibrated noon with a 48-52 percent unity notch. The notch is enabled only with vctr 1.',
  mlop: '//Morph Loop: 0 stock gaps (default), 1 seamless loop at minimum Morph',
  dstr: '//Startup/reload Gene density: 0.1-128 Genes/sec, at most one decimal, default 8. Explicit dstr recalls on settings-only reload; omit to preserve live rate. Knob changes are temporary.',
  dens: '//Independent Gene density: 0 off, 1 on: startup rate from dstr (default 8 Genes/sec); hold SHIFT and turn Gene Size for 0.1-128 Genes/sec; knob rate remains until adjusted again, recalled by dstr reload or powered off, not saved across power cycles; overrides Turing rate; external clock takes priority',
  vrng: '//0 stock, 1 +/-4x bidirectional or 0-8x forward',
  vqnt: '//Varispeed quantization: 0 SHIFT+Varispeed locks, 1 quantized normally and SHIFT+Varispeed temporarily free; release snaps back; scale from octl/scal',
  tape: '//SHIFT+S.O.S.: 0 classic TLA feedback (input + feedback x Gene playback), 1 tape mode (Varispeed tape head in the Slide/Gene Size window)',
  octl: '//Varispeed scale: 0 off, 1 octaves, 2 octaves + fifths, 3 semitones, 4 custom scale (scal); vqnt selects gesture behavior',
  scal: '//Custom scale for octl 4: semitones 1-11 above the root, e.g. 3,5,7,10 = minor pentatonic (root and octaves always on)',
  fxsl: '//SHIFT+Morph effect: 0 off (Morph stays stock), 1 SRR (sample-rate reduction), 2 warble (tape wow and flutter on the Gene playback)',
  cpul: '//CPU log, for troubleshooting only: 0 off, 1 on (writes cpulog.txt every 10 s; turn it off again afterwards)',
  mcap: '//Morph cap while tape-dubbing: 0 none, 1-9 = Morph limited to 0.1-0.9 (CPU safety; 3 = 0.3)',
  sldm: "//Turing mode: 0 off, 1 on: a loop of random seeds decides each Gene's chord ratio, scatter and stereo. SHIFT+Organize = evolution (left = locked loop, right = normal randomness), SHIFT+Gene Size = Genes per step (1-16), SHIFT+Slide = spread (start jitter, repeats when locked)",
  root: '//Turing: chance in percent that a step plays the root rather than a chord ratio (mcr1-mcr3)',
  tlen: '//Turing loop length in steps, 1-16',
  ingn: '//Input gain 0-3 (REC held + SHIFT taps); saved automatically a few seconds after a change',
  mono: '//Mono input: 0 off (stereo), 1 left input copied to the right (heard and recorded on both channels; R in is ignored), 2 auto: only while nothing is playing into R in',
};
const FIELDS = [...Object.keys(KEYS), 'gnsm', 'vsop'];
const PRESET_KEYS = Object.freeze(['mpos', 'gpos', 'spos', 'vpos', 'sosp', 'splc', 'srrp', 'jitp', 'wrbp', 'fbkp', 'evop', 'trst']);
const TURING_STEPS = Object.freeze([1,2,3,4,6,8,12,16]);
const DEFAULTS = Object.freeze({mpos:'0', gpos:'0', spos:'0', vpos:'0', sosp:'0', splc:'1', srrp:'0', jitp:'0', wrbp:'0', fbkp:'0', evop:'0', trst:'1', vuni:'0', vctr:'0', dstr:'8', mlop:'0', vsop:'0', vqnt:'0', dens:'0', vrng:'0', tape:'1', octl:'1', scal:'0', fxsl:'1', cpul:'0',
  mcap:'3', sldm:'0', root:'50', tlen:'8', ingn:'0', mono:'0', gnsm:'0'});
const LIMITS = {mpos:[0,100], gpos:[0,100], spos:[0,100], vpos:[0,100], sosp:[0,100], splc:[1,300], srrp:[0,100], jitp:[0,100], wrbp:[0,100], fbkp:[0,100], evop:[0,100], vuni:[0,1], vctr:[0,1], mlop:[0,1], vsop:[0,2], vqnt:[0,1], dens:[0,1], vrng:[0,1], tape:[0,1], octl:[0,4], fxsl:[0,2], cpul:[0,1],
  mcap:[0,9], sldm:[0,1], root:[0,100], tlen:[1,16], ingn:[0,3], mono:[0,2], gnsm:[0,1]};
function optionValue(key, raw) {
  if (key === 'dstr') return /^\d{1,3}(?:\.\d)?$/.test(raw) && Number(raw)>=0.1 && Number(raw)<=128 ? String(Number(raw)) : null;
  if (key === 'trst') return /^\d+$/.test(raw) && TURING_STEPS.includes(Number(raw)) ? String(Number(raw)) : null;
  if (key === 'scal') return scaleList(raw);
  const n = Number(raw), [lo, hi] = LIMITS[key];
  return /^\d+$/.test(raw) && Number.isInteger(n) && n >= lo && n <= hi ? String(n) : null;
}
const LINE = /^\s*([a-z0-9]{4})(?:[ \t]+(.*))?$/;
function parsedLine(line) {
  const m = line.match(LINE);
  if (!m) return null;
  const body = m[2] || '', index = body.indexOf('//');
  return {key:m[1], raw:(index<0?body:body.slice(0,index)).trim(),
    comment:index<0?'':' //'+body.slice(index+2)};
}
function parseOptions(text) {
  const values = {...DEFAULTS};
  for (const line of text.split(/\r?\n/).slice(1)) {
    const m=parsedLine(line);
    if (!m || !FIELDS.includes(m.key)) continue;
    values[m.key] = optionValue(m.key,m.raw) ?? DEFAULTS[m.key];
  }
  return values;
}
function scaleList(text) {
  if (text.trim()==='0') return '0';
  if (!/^\s*(?:[1-9]|1[01])(?:[ ,]+(?:[1-9]|1[01]))*\s*$/.test(text)) return null;
  return [...new Set(text.trim().split(/[ ,]+/).map(Number))].sort((a,b)=>a-b).join(',');
}

function chosenOptions() {
  const values = Object.fromEntries(FIELDS.map((k) => {
    const el = $('opt-' + k);
    const value = optionValue(k, el.value) ?? DEFAULTS[k];
    el.value = value;
    return [k, value];
  }));
  for (const k of ['dstr', ...PRESET_KEYS]) {
    if (!$('recall-'+k).checked) delete values[k];
  }
  return values;
}

function modLines(values) {
  return [VERSION_HEADER, MOD_HEADER, ...Object.keys(KEYS).filter((k) => k in values).map((k) => `${k} ${values[k]} ${KEYS[k]}`)];
}

let loadedOptions = null;

function renderOptions() {
  const recallDensity = $('recall-dstr').checked;
  for (const k of ['dstr', ...PRESET_KEYS]) $('opt-'+k).disabled = !$('recall-'+k).checked;
  const values = chosenOptions();
  let text;
  if (loadedOptions) {
    const lines = loadedOptions.split(/\r?\n/);
    const seen = new Set();
    const out = lines.flatMap((line, i) => {
      if (i>0 && /^\s*\/\/\s*firmware version\b/i.test(line)) return [];
      const m=parsedLine(line);
      if (i>0 && m && FIELDS.includes(m.key)) {
        if (!(m.key in values) || seen.has(m.key)) return [];
        seen.add(m.key);
        const comment = m.key === 'vrng' && m.comment.trim() === LEGACY_RANGE_COMMENT
          ? ' ' + KEYS.vrng : m.comment;
        return [m.key+' '+values[m.key]+comment];
      }
      return [line];
    });
    // Preserve the numeric first state line verbatim; version identification is a comment.
    out.splice(1, 0, VERSION_HEADER);
    while (out.length && out[out.length - 1] === '') out.pop();
    const missing = Object.keys(values).filter((k) => !seen.has(k));
    if (missing.length) {
      if (!out.includes(MOD_HEADER)) out.push('//', MOD_HEADER);
      for (const k of missing) out.push(`${k} ${values[k]} ${KEYS[k] || "//Stock setting"}`);
    }
    text = out.join('\n') + '\n';
    $('options-save-row').hidden = false;
    $('options-note').textContent = 'Your options.txt with these values. Copy it back to the card root. ' +
      (recallDensity ? 'Settings-only reload recalls the selected density.' : 'Settings-only reload preserves the current density; dstr is omitted.');
  } else {
    text = [...modLines(values), `vsop ${values.vsop} //Replace the existing stock vsop line`, `gnsm ${values.gnsm} //Replace the existing stock gnsm line`].join('\n') + '\n';
    $('options-save-row').hidden = true;
    $('options-note').textContent = `Add the mod lines to your existing options.txt; replace its vsop/gnsm lines with the values below. Do not duplicate keys. Load the file above to remove unchecked preset keys automatically. ` +
      (recallDensity ? 'Or load your options.txt above to get a complete file.' :
        'Load your options.txt above to create a complete file with dstr removed automatically.');
  }
  $('options-note').textContent += ' Unchecked preset recalls are omitted; checked presets apply at startup and settings-only reload. Effect and Turing presets use their selected modes.';
  $('options-text').value = text;
}

// ---------- page ----------
function init() {
  const remixes = (window.MGMOD_REMIXES || []).filter(r=>r.name==='full');
  const select = $('remix');
  for (const r of remixes) {
    const o = document.createElement('option');
    o.value = r.name;
    o.textContent = r.title;
    select.appendChild(o);
  }
  const describe = () => {
    const r = remixes.find((x) => x.name === select.value);
    if (!r) return;
    $('remix-description').textContent = r.description;
    $('remix-modules').innerHTML = '';
    r.modules.forEach((m, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="num">${String(i + 1).padStart(2, '0')}</span><span class="t">${m.title}</span><span class="badge">${m.status}</span>`;
      $('remix-modules').appendChild(li);
    });
  };
  select.addEventListener('change', describe);
  describe();

  $('firmware').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    stockImage = null;
    $('build-buttons').hidden = true;
    status('firmware-status', 'Reading ' + file.name + '…');
    try {
      stockImage = await readFirmware(file);
      status('firmware-status', 'Official mg204 firmware recognised.', 'ok');
      $('build-buttons').hidden = false;
    } catch (err) {
      status('firmware-status', err.message, 'error');
    }
  });

  const build = async (kind) => {
    const r = remixes.find((x) => x.name === select.value);
    status('build-status', 'Building…');
    try {
      const image = await buildRemix(r);
      if (kind === 'card') {
        download('mgmod.bin', cardFile(image));
        status('build-status', 'mgmod.bin saved. Copy it to the root of the Morphagene card and power on.', 'ok');
      } else {
        status('build-status', 'Encoding the audio update…');
        await new Promise((res) => setTimeout(res, 20));
        download('mg204+c2.wav', updateWav(image), 'audio/wav');
        status('build-status', 'mg204+c2.wav saved. Follow the first-time audio installation steps above.', 'ok');
      }
    } catch (err) {
      status('build-status', err.message, 'error');
    }
  };
  $('build-card').addEventListener('click', () => build('card'));
  $('build-wav').addEventListener('click', () => build('wav'));

  $('recall-dstr').checked = true;
  $('recall-dstr').addEventListener('change', renderOptions);
  for (const k of PRESET_KEYS) {
    $('recall-'+k).checked = false;
    $('recall-'+k).addEventListener('change', renderOptions);
  }
  for (const k of FIELDS) {
    $('opt-'+k).value=DEFAULTS[k];
    $('opt-'+k).addEventListener('change', renderOptions);
  }
  $('options-file').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    try {
      if (file && file.size>16384) throw new Error('options.txt must be no larger than 16 KiB.');
      const text=file ? await file.text() : null;
      if (text && (/[^\x09\x0a\x0d\x20-\x7e]/.test(text) || !text.includes('\n')))
        throw new Error('Choose a plain-text options.txt created by your Morphagene, including its first state line.');
      loadedOptions=text;
      $('recall-dstr').checked = !loadedOptions || loadedOptions.split(/\r?\n/).slice(1)
        .some((line) => parsedLine(line)?.key === 'dstr');
      const values=loadedOptions ? parseOptions(loadedOptions) : {...DEFAULTS};
      const lines = loadedOptions ? loadedOptions.split(/\r?\n/).slice(1).map(parsedLine).filter(Boolean) : [];
      for (const k of PRESET_KEYS) {
        const entry = lines.filter((line) => line.key === k).at(-1);
        const value = entry ? optionValue(k, entry.raw) : null;
        $('recall-'+k).checked = value !== null;
        // Missing/invalid optional recalls must not silently become presets.
        // Keep the visible numeric choice for a later explicit re-enable.
        if (loadedOptions && value === null) values[k] = optionValue(k, $('opt-'+k).value) ?? DEFAULTS[k];
      }
      for (const k of FIELDS) $('opt-'+k).value=values[k];
      status('options-status', text?'Loaded. Review the values and generated file before saving.':'No file loaded; showing a settings snippet.');
      renderOptions();
    } catch(err) {
      loadedOptions=null;
      renderOptions();
      status('options-status',err.message,'error');
    }
  });
  $('options-save').addEventListener('click', () => download('options.txt', new TextEncoder().encode($('options-text').value), 'text/plain'));
  renderOptions();
}

document.addEventListener('DOMContentLoaded', init);
