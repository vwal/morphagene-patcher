// Morphagene options editor. Both the website and the single-file editor use this script.
'use strict';

// ---------- options.txt ----------
const VERSION_HEADER = '// firmware version 204-c6';
const MOD_HEADER = '//Morphagene extended mods';
// In older builds this comment put "vsop 2" at the start of a 63-byte read.
const OBSOLETE_COMMENTS = {
  dens: ['//Independent Gene density: 0 off, 1 on: startup rate from dstr (default 8 Genes/sec); hold SHIFT and turn Gene Size for 0.1-128 Genes/sec; knob rate remains until adjusted again, recalled by dstr reload or powered off, not saved across power cycles; overrides Turing rate; external clock takes priority', '//Independent Gene density: 0 off, 1 SHIFT+Gene Size = 0.1-128 Genes/sec (takes priority over Turing rate); startup rate from dstr; bypassed with clock'],
  dstr: ['//Startup/reload Gene density: 0.1-128 Genes/sec, at most one decimal, default 8. Explicit dstr recalls on settings-only reload; omit to preserve live rate. Knob changes are temporary.',
         '//Startup/reload density in Genes/sec: 0.1-128, at most one decimal; default 8. Explicit dstr recalls on settings-only reload. Knob changes are not saved.'],
  vrng: ['//Varispeed range: 0 stock, 1 extended: vsop 0/1 +/-4x; vsop 2 forward stop to 8x with scale lock'],
  dryk: ['//0 normal, 1 wet only, 2 wet with S.O.S. feedback.'],
  sosp: ['//S.O.S. mode 2 tape retention, mode 3 Gene level.', '//Primary S.O.S. 0-100%. In mode 2 this sets retention.',
         '//Primary S.O.S. 0-100. In mode 2 this sets retention.']
};
// Extended option keys and explanatory comments for generated files.
const KEYS = {
  mpos: '//Morph virtual knob preset: 0-100 percent. 10 selects the stock seamless loop (unclocked/dens 0); 0 gaps with mlop 0. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  gpos: '//Gene Size virtual knob preset: 0-100 percent. 0 and 1 = longest/full splice; 100 = shortest, not a length percentage. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  spos: '//Slide virtual knob preset: integer 0-100 percent. Omit to use the panel at startup and preserve the live position on settings-only reload.',
  vpos: '//Varispeed virtual knob preset: integer 0-100 percent before vsop/vrng/vctr mapping, not a speed ratio. vuni remains the +1x recall gesture.',
  sosp: '//Primary S.O.S. position for the selected sosc curve.',
  splc: '//Splice recall: integer 1-300, 1 is the first splice. Above the reel count selects its last splice; the configured number is retained. Omit to preserve selection on settings-only reload.',
  srrp: '//Sample-rate reduction virtual knob preset: integer 0-100 percent. Used with fxsl 1; retained separately from warble. SRR and warble cannot run together.',
  jitp: '//Jitter / Turing spread virtual knob preset: integer 0-100 percent for SHIFT+Slide.',
  wrbp: '//Warble virtual knob preset: integer 0-100 percent. Used with fxsl 2; retained separately from SRR. SRR and warble cannot run together.',
  fbkp: '//SHIFT+S.O.S. 0-100%. Used in dry-kill modes 0 and 1.',
  evop: '//Turing evolution virtual knob preset: integer 0-100 percent. Used with sldm 1.',
  trst: '//Turing Genes per step preset: 1,2,3,4,6,8,12,16. Used with sldm 1; dens 1 takes priority over the Turing rate.',
  vuni: '//Unity recall: 0 off, 1 hold SHIFT alone >=0.5 seconds and release for forward +1x with pickup. Use with SHIFT jack unpatched.',
  vctr: '//Noon unity mapping: 0 original mapping, 1 +1x at calibrated noon with a 48-52 percent unity notch. The notch is enabled only with vctr 1.',
  mlop: '//Morph Loop: 0 stock gaps (default), 1 seamless loop at minimum Morph',
  dstr: '//0 stock timing, 0.1-128 Genes/sec. Default 1.0. Omit on settings-only reload to keep live timing.',
  dens: '//SHIFT+Gene Size: CCW stock timing, then 0.1-128 Hz.',
  vrng: '//0 stock, 1 +/-4x bidirectional or 0-8x forward',
  vqnt: '//Varispeed quantization: 0 SHIFT+Varispeed locks, 1 quantized normally and SHIFT+Varispeed temporarily free; release snaps back; scale from octl/scal',
  dryk: '//0 normal, 1 wet, 2 tape feedback, 3 Gene feedback.',
  sosc: '//0 crossfade, 1 full input, 2 full existing.',
  dlen: '//0 fixed, 1 extend last splice at CCW in dryk 2.',
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
// Stock mg204 card settings, in the order used by the module's options writer.
const STOCK_KEYS = {
  vsop: '//Varispeed layout', inop: '//Recording source', pmin: '//Right input phase modulation',
  omod: '//Organize response', gnsm: '//Gene smoothing', rsop: '//Record buttons',
  pmod: '//Play input', ckop: '//Clock input', cvop: '//CV output',
  mcr1: '//Gene 2 chord ratio', mcr2: '//Gene 3 chord ratio', mcr3: '//Gene 4 chord ratio',
};
const CHORD_KEYS = ['mcr1', 'mcr2', 'mcr3'];
const FIELDS = [...Object.keys(STOCK_KEYS), ...Object.keys(KEYS)];
const PRESET_KEYS = Object.freeze(['mpos', 'gpos', 'spos', 'vpos', 'sosp', 'splc', 'srrp', 'jitp', 'wrbp', 'fbkp', 'evop', 'trst']);
const TURING_STEPS = Object.freeze([1,2,3,4,6,8,12,16]);
const DEFAULTS = Object.freeze({mpos:'0', gpos:'0', spos:'0', vpos:'0', sosp:'0', splc:'1', srrp:'0', jitp:'0', wrbp:'0', fbkp:'0', evop:'0', trst:'1', vuni:'0', vctr:'0', dstr:'1', mlop:'0', vsop:'0', vqnt:'0', dens:'0', vrng:'0', dryk:'0', sosc:'0', dlen:'0', tape:'1', octl:'1', scal:'0', fxsl:'1', cpul:'0',
  mcap:'3', sldm:'0', root:'50', tlen:'8', ingn:'0', mono:'0', gnsm:'0',
  inop:'0', pmin:'0', omod:'0', rsop:'0', pmod:'0', ckop:'0', cvop:'0',
  mcr1:'2', mcr2:'1.5', mcr3:'1.33333'});
const LIMITS = {mpos:[0,100], gpos:[0,100], spos:[0,100], vpos:[0,100], sosp:[0,100], splc:[1,300], srrp:[0,100], jitp:[0,100], wrbp:[0,100], fbkp:[0,100], evop:[0,100], vuni:[0,1], vctr:[0,1], mlop:[0,1], vsop:[0,2], vqnt:[0,1], dens:[0,1], vrng:[0,1], dryk:[0,3], sosc:[0,2], dlen:[0,1], tape:[0,1], octl:[0,4], fxsl:[0,2], cpul:[0,1],
  mcap:[0,9], sldm:[0,1], root:[0,100], tlen:[1,16], ingn:[0,3], mono:[0,2], gnsm:[0,1],
  inop:[0,1], pmin:[0,1], omod:[0,1], rsop:[0,1], pmod:[0,2], ckop:[0,2], cvop:[0,1]};
function optionValue(key, raw) {
  if (CHORD_KEYS.includes(key)) {
    const token = raw.trim();
    if (!/^[+-]?\d{1,8}(?:\.\d{1,8})?$/.test(token)) return null;
    const magnitude = Math.abs(Number(token));
    if (magnitude === 0) return '0.0625';
    return magnitude >= 0.0625 && magnitude <= 16 ? token : null;
  }
  if (key === 'dryk' || key === 'dlen' || key === 'sosc') return /^\d$/.test(raw) && Number(raw) <= LIMITS[key][1] ? raw : null;
  if (key === 'dstr') return /^\d{1,3}(?:\.\d)?$/.test(raw) && Number(raw)<=128 ? String(Number(raw)) : null;
  // A zero written for a positive-only count recalls its smallest count.
  if ((key === 'splc' || key === 'trst') && /^0{1,3}$/.test(raw)) return '1';
  if (key === 'tlen' && /^0{1,4}$/.test(raw)) return '1';
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
function scaleList(text) {
  if (text.trim()==='0') return '0';
  if (!/^\s*(?:[1-9]|1[01])(?:[ ,]+(?:[1-9]|1[01]))*\s*$/.test(text)) return null;
  return [...new Set(text.trim().split(/[ ,]+/).map(Number))].sort((a,b)=>a-b).join(',');
}

function omittedStock(key) {
  return missingStockKeys.has(key) && $('opt-'+key).value === '';
}

function showChordRatio(field, token) {
  // Keep the card's exact spelling for export. Trim only fractional padding in the field.
  field.dataset.ratioToken = token;
  field.value = token.includes('.') ? token.replace(/0+$/, '').replace(/\.$/, '') : token;
}

function chosenOptions() {
  const values = {};
  for (const k of FIELDS) {
    if (omittedStock(k)) continue;
    const el = $('opt-' + k);
    const value = optionValue(k, el.value) ?? DEFAULTS[k];
    if (CHORD_KEYS.includes(k)) {
      values[k] = el.dataset.ratioToken ?? value;
    } else {
      el.value = value;
      values[k] = value;
    }
  }
  for (const k of ['dstr', ...PRESET_KEYS]) {
    if (!$('recall-'+k).checked) delete values[k];
  }
  return values;
}

function settingLines(comments, values, seen) {
  return Object.keys(comments).filter(k => k in values && !seen.has(k))
    .map(k => `${k} ${values[k]} ${comments[k]}`);
}

let loadedOptions = null;
const missingStockKeys = new Set();

function renderOptions() {
  const recallDensity = $('recall-dstr').checked;
  for (const k of ['dstr', ...PRESET_KEYS]) $('opt-'+k).disabled = !$('recall-'+k).checked;
  const invalidRatios = CHORD_KEYS.filter(k => !omittedStock(k) && optionValue(k, $('opt-'+k).value) === null);
  for (const k of CHORD_KEYS) {
    const invalid = invalidRatios.includes(k);
    $('error-'+k).hidden = !invalid;
    $('opt-'+k).ariaInvalid = String(invalid);
  }
  $('options-save-row').hidden = !loadedOptions;
  $('options-save').disabled = invalidRatios.length > 0;
  if (invalidRatios.length) {
    $('options-text').value = '';
    $('options-note').textContent = 'Check the chord ratio for ' + invalidRatios.join(', ') + ' to generate your settings.';
    return;
  }
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
        const comment = OBSOLETE_COMMENTS[m.key]?.includes(m.comment.trim())
          ? ' ' + KEYS[m.key] : m.comment;
        return [m.key+' '+values[m.key]+comment];
      }
      return [line];
    });
    // Preserve the numeric first state line verbatim; version identification is a comment.
    out.splice(1, 0, VERSION_HEADER);
    while (out.length && out[out.length - 1] === '') out.pop();
    const missingStock = settingLines(STOCK_KEYS, values, seen);
    const modHeader = line => /^\s*\/\/\s*Morphagene (?:extended|Study) mods\s*$/i.test(line);
    if (missingStock.length) {
      const firstMod = out.findIndex((line, i) => i > 0 && (modHeader(line) || Object.hasOwn(KEYS, parsedLine(line)?.key)));
      out.splice(firstMod < 0 ? out.length : firstMod, 0, ...missingStock);
    }
    const missingMods = settingLines(KEYS, values, seen);
    if (missingMods.length) {
      if (!out.some(modHeader)) out.push('//', MOD_HEADER);
      out.push(...missingMods);
    }
    text = out.join('\n') + '\n';
    $('options-note').textContent = 'Your options.txt with these values. Copy it back to the card root. ' +
      (recallDensity ? 'Settings-only reload recalls the selected Gene timing.' : 'Settings-only reload keeps the live Gene timing because dstr is omitted.');
  } else {
    const seen = new Set();
    text = [VERSION_HEADER, '//Stock Morphagene settings', ...settingLines(STOCK_KEYS, values, seen),
      MOD_HEADER, ...settingLines(KEYS, values, seen)].join('\n') + '\n';
    $('options-note').textContent = 'This snippet contains stock and enhancement settings. Replace matching lines in your existing options.txt and keep its first numeric line. ' +
      (recallDensity ? 'Or load your options.txt above to get a complete file.' :
        'Load your options.txt above to create a complete file with dstr removed automatically.');
  }
  $('options-note').textContent += ' Unchecked preset recalls are omitted; checked presets apply at startup and settings-only reload. Effect and Turing presets use their selected modes.';
  $('options-text').value = text;
}

// A null source supplies factory settings to the form. The loaded card remains
// the template for export when the user explicitly resets its options.
function populateEditor(text) {
  const entries = new Map();
  if (text) {
    for (const line of text.split(/\r?\n/).slice(1)) {
      const entry = parsedLine(line);
      if (entry) entries.set(entry.key, entry.raw);
    }
  }
  missingStockKeys.clear();
  $('recall-dstr').checked = !text || entries.has('dstr');
  for (const k of FIELDS) {
    const field = $('opt-'+k);
    const parsed = entries.has(k) ? optionValue(k, entries.get(k)) : null;
    let value = parsed ?? DEFAULTS[k];
    if (PRESET_KEYS.includes(k)) {
      $('recall-'+k).checked = parsed !== null;
      // A partial card keeps the visible choice for an explicit later recall.
      if (text && parsed === null) value = optionValue(k, field.value) ?? DEFAULTS[k];
    }
    // Earlier editors always supplied vsop and gnsm. Other missing stock
    // keys stay absent on a partial card until edited or explicitly reset.
    if (text && Object.hasOwn(STOCK_KEYS, k) && k !== 'vsop' && k !== 'gnsm' && !entries.has(k)) {
      missingStockKeys.add(k);
      value = '';
    }
    if (CHORD_KEYS.includes(k)) {
      showChordRatio(field, value);
      field.placeholder = missingStockKeys.has(k) ? 'Omitted (stock default '+DEFAULTS[k]+')' : '';
    } else {
      field.value = value;
    }
  }
}

function initOptionsEditor() {
  for (const k of ['dstr', ...PRESET_KEYS]) $('recall-'+k).addEventListener('change', renderOptions);
  for (const k of FIELDS) {
    const field = $('opt-'+k);
    if (CHORD_KEYS.includes(k)) {
      field.addEventListener('input', () => {
        delete field.dataset.ratioToken;
        renderOptions();
      });
      field.addEventListener('change', () => {
        const token = optionValue(k, field.value);
        if (token !== null) showChordRatio(field, token);
        renderOptions();
      });
    } else {
      field.addEventListener('change', renderOptions);
    }
  }
  let importSequence = 0;
  async function importOptionsFile(file) {
    const sequence = ++importSequence;
    if (file) {
      loadedOptions = null;
      $('options-reset').disabled = true;
      renderOptions();
      status('options-status', 'Reading options.txt…');
    }
    try {
      if (file && file.size>16384) throw new Error('options.txt must be no larger than 16 KiB.');
      const text=file ? await file.text() : null;
      if (sequence !== importSequence) return;
      if (file && (/[^\x09\x0a\x0d\x20-\x7e]/.test(text) || !text.includes('\n')))
        throw new Error('Choose a plain-text options.txt created by your Morphagene, including its first state line.');
      loadedOptions=text;
      populateEditor(text);
      status('options-status', file ? 'Loaded '+(file.name || 'options.txt')+'. Review the settings before saving.' : 'No file loaded; showing a settings snippet.');
      renderOptions();
    } catch(err) {
      if (sequence !== importSequence) return;
      loadedOptions=null;
      renderOptions();
      status('options-status',err.message,'error');
    } finally {
      if (sequence === importSequence) $('options-reset').disabled = false;
    }
  }
  bindFileDrop('options-file', 'options-drop', importOptionsFile, () => {
    ++importSequence;
    $('options-reset').disabled = false;
    status('options-status', 'Drop a single options.txt file here.', 'error');
  });
  const resetDialog = $('options-reset-dialog');
  $('options-reset').addEventListener('click', () => resetDialog.showModal());
  $('reset-cancel').addEventListener('click', () => resetDialog.close());
  $('reset-confirm').addEventListener('click', () => {
    populateEditor(null);
    renderOptions();
    resetDialog.close();
    status('options-status', loadedOptions
      ? 'Defaults restored in the editor. Review and download options.txt to use them.'
      : 'Defaults restored in the settings snippet.');
  });
  $('options-save').addEventListener('click', () => {
    if (loadedOptions && !$('options-save').disabled) download('options.txt', new TextEncoder().encode($('options-text').value), 'text/plain');
  });
  populateEditor(null);
  renderOptions();
}

document.addEventListener('DOMContentLoaded', initOptionsEditor);
