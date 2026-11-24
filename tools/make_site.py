"""Build the mg204-c6 patcher and options editor."""
from pathlib import Path
from string import Template
import argparse
import base64
import hashlib
import html,json,shutil
S=Path(__file__).resolve().parents[1];W=S/'web'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package-dir', type=Path, help='Also place the standalone editor at the root of this test package.')
package_dir = parser.parse_args().package_dir
# key, label, description, choices (or null for numeric/text input), default
fields=[('vsop',
  'Varispeed layout',
  'Classic (0) is the original bidirectional response with smooth braking around stop. V/oct (1) is the '
  'alternate bidirectional pitch response: with the input attenuverter carefully adjusted, CV can track '
  'volts per octave. Forward only (2) runs from stop at fully CCW to maximum forward speed. Extended range '
  'and Unity at noon reshape these responses; V/oct is not a promise of calibrated tracking in every '
  'modified layout. If an older build changed your layout to forward only, select your preferred layout here and save options.txt after upgrading.',
  ['0: Bidirectional — classic', '1: Bidirectional — V/oct', '2: Forward only'],
  '0'),
 ('vrng',
  'Extended range',
  'Off keeps stock ranges. On gives +/-4x in vsop 0/1, or stop to forward 8x in vsop 2.',
  ['0: Off', '1: On'],
  '0'),
 ('vuni',
  'Return to 1:1 with SHIFT',
  'Optional and off by default. Hold SHIFT alone for at least 0.5 seconds, then release to recall exact '
  'forward +1x. Varispeed holds there until the combined knob/CV input picks it up. Short taps still advance '
  'splices. Moving a knob, pressing another button or card activity cancels the reset. Keep the SHIFT input '
  'unpatched.',
  ['0: Off', '1: Hold / release recalls +1x'],
  '0'),
 ('vctr',
  '1:1 at Varispeed noon',
  'Optional and off by default. Places forward +1x at calibrated noon in every layout, range and scale, with '
  'an easy-to-find 48-52% notch. Bidirectional layouts fit stop and reverse into the left half. With this '
  'off, no extra flat zone is added to continuous Varispeed.',
  ['0: Original mapping', '1: +1x at noon with notch'],
  '0'),
 ('vpos',
  'Varispeed preset (%)',
  '0-100% of the calibrated control range, before layout, extended range and Unity at noon mapping. It is a '
  'knob position, not a playback-speed percentage. With vctr 1, 50% recalls forward +1x; otherwise speed '
  'depends on the selected layout and quantization. A later SHIFT unity recall replaces this hold.',
  None,
  '0'),
 ('vqnt',
  'Quantize normally',
  'Off: SHIFT + Varispeed locks to the scale. On: pitch is normally quantized; SHIFT + Varispeed temporarily '
  'becomes continuous. Release snaps back.',
  ['0: SHIFT to lock', '1: Quantized normally'],
  '0'),
 ('octl',
  'Varispeed scale',
  'Applies to both quantization modes. Off disables quantization.',
  ['0: Off', '1: Octaves', '2: Octaves + fifths', '3: Semitones', '4: Custom scale'],
  '1'),
 ('scal',
  'Custom semitones',
  'For octl 4: comma-separated 1-11, e.g. 3,5,7,10. Root and octaves are always included. 0 means '
  'root/octaves only.',
  None,
  '0'),
 ('mlop',
  'Morph Loop',
  'Always included in this firmware. On removes the silent gaps at minimum Morph. Higher overlap settings '
  'stay unchanged.',
  ['0: Off (stock gaps)', '1: On (seamless loop)'],
  '0'),
 ('mpos',
  'Morph preset (%)',
  '0-100% virtual knob position. For normal unclocked playback with independent density off, 10% selects the '
  'stock seamless-loop setting (9-11%). At 0%, Morph Loop Off leaves a scheduling gap; Morph Loop On removes '
  'it. Higher values add overlap, then pitch/pan variation. Clock and independent density can change Gene '
  'spacing.',
  None,
  '0'),
 *[(f'mcr{voice - 1}', f'Gene {voice} chord ratio',
    f'Sets the playback speed of Gene {voice} at high Morph. Use 1 for unison, '
    '2 for an octave up, or a negative ratio for reverse playback. '
    'The magnitude can range from 0.0625 to 16, with up to eight decimal places. An explicit zero selects the minimum forward ratio, 0.0625.',
    None, ratio) for voice, ratio in ((2, '2'), (3, '1.5'), (4, '1.33333'))],
 ('gnsm',
  'Gene smoothing',
  'Choose the original or smoother Gene envelope.',
  ['0: Original', '1: Smooth'],
  '0'),
 ('gpos',
  'Gene Size preset (%)',
  '0-100% virtual knob position, not a percentage of the splice length. 0% and 1% play the longest Genes '
  '(the full splice); turning up shortens them, and 100% gives the shortest Genes. The response is '
  'nonlinear; actual duration also depends on the reel, speed and clock.',
  None,
  '0'),
 ('spos',
  'Slide preset (%)',
  '0-100% virtual knob position: move the Gene window from the beginning toward the end of the selected '
  'splice. Gene Size affects which portion is heard. This is not an absolute timestamp.',
  None,
  '0'),
 ('jitp',
  'Jitter / spread preset (%)',
  'SHIFT + Slide position, 0-100%: 0% is no jitter, and increasing it widens Gene-start scatter. With sldm 1 '
  'this becomes repeating Turing spread. The response is nonlinear, not a percentage of reel length.',
  None,
  '0'),
 ('dens',
  'Independent Gene density',
  'With dens 1, dstr selects startup timing. Its default is 1 Gene/sec. Hold SHIFT and turn Gene Size to '
  'select stock timing at fully CCW. Turn slightly clockwise for 0.1 Genes/sec, through 8 at noon to 128 at fully CW. '
  'Pitch and Morph can change while the selected rate stays fixed. Unshifted Gene Size sets length. '
  'Panel edits last until another adjustment, an explicit dstr reload or '
  'power-off. The module keeps the configured value in options.txt. '
  'Overrides the Turing rate gesture; external clock takes priority.',
  ['0: Off', '1: On'],
  '0'),
 ('dstr',
  'Startup / reload Gene timing (Genes/sec)',
  'Enter 0 for stock Gene timing or 0.1–128 for a rate in Genes/sec, in steps of 0.1. The default is 1.0 Gene/sec. '
  'With dens 1, SHIFT + Gene Size remains available after either choice. If your card already says dstr 8.0, '
  'it will still start at 8 Genes/sec. Change it to 0 for stock timing or 1 for one Gene per second. An external clock takes priority.',
  None,
  '1'),
 ('ckop', 'Clock input',
  'In hybrid mode, Morph selects Gene shifting or time stretching. Choose a fixed mode to use the clock for one function across the Morph range.',
  ['0: Hybrid', '1: Gene shift only', '2: Time stretch only'], '0'),
 ('cvop', 'CV output',
  'Send the signal envelope or a ramp timed to the current Gene Size.',
  ['0: Envelope follower', '1: Gene ramp'], '0'),
 ('rsop', 'Record buttons',
  'Choose which button gesture starts a recording into the current splice and which creates a new splice.',
  ['0: REC current / REC + SPLICE new', '1: REC new / REC + SPLICE current'], '0'),
 ('inop', 'Recording source',
  'For ordinary recording, S.O.S. blends the input with Gene playback. Choose input only to capture the live input at any S.O.S. position. Dry kill modes 2 and 3 use their own recording sources.',
  ['0: S.O.S. mix', '1: Input only'], '0'),
 ('dryk',
  'Dry kill',
  'Mode 0 monitors the S.O.S. curve. Modes 1–3 monitor only Gene playback. Mode 1 keeps the ordinary '
  'recording source and SHIFT feedback controls. Mode 2 mixes with stored audio under the tape head on '
  'fixed overdubs. Mode 3 mixes with performed Gene playback, including Varispeed, Morph, Gene Size and Slide.',
  ['0: Normal monitoring', '1: Wet only, current recording controls', '2: Wet only, tape feedback',
   '3: Wet only, record Gene playback with S.O.S.'],
  '0'),
 ('sosc', 'S.O.S. curve',
  '0 fades in existing audio up to noon, then fades out incoming audio. Both are at full level at noon. '
  '1 keeps incoming audio full and fades in existing audio clockwise. 2 keeps existing audio full and '
  'fades out incoming audio clockwise. An omitted line selects 0 on startup or either card load. '
  'The first take on an empty reel always records full input. Choose sosc 1 with dryk 2 for the c4 full-input overdub.',
  ['0: Crossfade, both full at noon', '1: Keep incoming audio full', '2: Keep existing audio full'], '0'),
 ('dlen',
  'Overdub length at fully CCW',
  'Applies only to dryk 2. Fixed keeps the loop length and overdubs inside the Slide and Gene Size window. '
  'Extend works with sosc 0 or 1 and checks S.O.S. when REC starts. On the last or only splice, fully CCW (the lowest 4.5% of '
  'the effective knob/CV range, including a recalled S.O.S. preset) starts a replacement at the splice '
  'beginning. Input records forward at 1×, independent of Varispeed, Slide and Gene Size. Stop REC '
  'to set a longer end. A shorter take keeps the old length and tail. The selected recording mode lasts '
  'until REC stops. Earlier splices and takes started above the CCW zone use '
  'fixed-length overdubs with normal feedback.',
  ['0: Fixed (default)', '1: Extend the last splice at fully CCW'],
  '0'),
 ('tape',
  'SHIFT + S.O.S. mode',
  'Selects tape overdub or classic TLA feedback for SHIFT + S.O.S. and fbkp in dryk 0 and 1. '
  'Modes 2 and 3 use their dedicated recording paths and main S.O.S. knob.',
  ['0: Classic TLA feedback', '1: Tape mode'],
  '1'),
 ('fbkp',
  'Feedback preset (%)',
  'SHIFT + S.O.S. virtual knob position for dryk 0 and 1. With tape 1, this sets how much of the old '
  'pass is retained; with tape 0 and inop 0, it sets the Gene playback contribution. '
  'Modes 2 and 3 take their feedback setting from the main S.O.S. knob or its preset (sosp).',
  None,
  '0'),
 ('sosp',
  'S.O.S. mix preset (%)',
  'Primary S.O.S. virtual knob position on the selected sosc curve. At 50% in the default crossfade, '
  'both incoming and existing audio are at full level.',
  None,
  '0'),
 ('mcap',
  'Tape overdub Morph cap',
  'Limits overlap while tape-dubbing. 0 disables the cap; 1-9 means 0.1-0.9. Higher values can increase '
  'glitches.',
  ['0: No cap', '1: 0.1', '2: 0.2', '3: 0.3', '4: 0.4', '5: 0.5', '6: 0.6', '7: 0.7', '8: 0.8', '9: 0.9'],
  '3'),
 ('fxsl',
  'SHIFT + Morph effect',
  'Selects one playback effect: sample-rate reduction or warble; they cannot run together. srrp and wrbp '
  'retain separate recalled amounts. Without an amount preset, startup uses the existing reset behavior. '
  'Warble uses less CPU than sample-rate reduction.',
  ['0: Off', '1: Sample-rate reduction', '2: Tape warble'],
  '1'),
 ('srrp',
  'Sample-rate reduction preset (%)',
  'SHIFT + Morph position, 0-100%: 0% bypasses SRR; increasing it strengthens sample-rate reduction. Active '
  'with fxsl 1. This is the knob curve, not a bit-depth or sample-rate percentage. Stored separately from '
  'warble; fxsl 0 bypasses both effects.',
  None,
  '0'),
 ('wrbp',
  'Warble preset (%)',
  'SHIFT + Morph position, 0-100%: 0% is no warble; higher values add stronger wow/flutter. Active with fxsl '
  '2. This is the knob curve, not a pitch percentage. Stored separately from SRR; only the selected effect '
  'runs.',
  None,
  '0'),
 ('sldm',
  'Turing mode',
  'SHIFT + Organize: evolution; SHIFT + Slide: repeating scatter; SHIFT + Gene Size: Genes per step when '
  'dens is off.',
  ['0: Off', '1: On'],
  '0'),
 ('evop',
  'Turing evolution preset (%)',
  'SHIFT + Organize position, 0-100%, used with sldm 1. 0% locks the repeating pattern; 100% produces fresh '
  'randomness. Intermediate values follow the existing nonlinear knob curve, not a literal probability '
  'percentage.',
  None,
  '0'),
 ('trst',
  'Turing Genes per step',
  'Choose 1, 2, 3, 4, 6, 8, 12 or 16 Genes per step. Used with sldm 1; dens 1 takes priority over the Turing '
  'rate. An explicit zero recalls 1 Gene per step. Unchecked preserves the live Turing rate on reload.',
  ['1: 1 Gene per step',
   '2: 2 Genes per step',
   '3: 3 Genes per step',
   '4: 4 Genes per step',
   '6: 6 Genes per step',
   '8: 8 Genes per step',
   '12: 12 Genes per step',
   '16: 16 Genes per step'],
  '1'),
 ('tlen', 'Turing loop steps', 'Number of repeating random steps, 1–16. An explicit zero selects 1 step.', None, '8'),
 ('root',
  'Turing root chance (%)',
  'Chance of choosing the root rather than a chord ratio from mcr1-mcr3. 100 disables pitch changes.',
  None,
  '50'),
 ('pmod', 'Play input',
  'Classic checks the gate at the end of each Gene or splice. Momentary starts and stops with the gate. Trigger loop keeps playing and jumps to the start set by Slide and Organize on each rising edge.',
  ['0: Classic', '1: Momentary gate', '2: Trigger loop'], '0'),
 ('omod', 'Organize response',
  'Choose when a splice selected with Organize or SHIFT takes over.',
  ['0: At Gene or splice end', '1: Immediately'], '0'),
 ('splc',
  'Splice to recall',
  'Splice numbers run from 1 to 300. Both 0 and 1 recall the first splice. A number above the loaded reel count selects its '
  'last splice while keeping your configured number. Unchecked keeps normal startup selection and preserves '
  'the current splice on settings-only reload.',
  None,
  '1'),
 ('ingn',
  'Input gain',
  'Stock gain index, 0-3. REC held + SHIFT taps changes it on the module; the mod saves it after about 3 '
  'seconds.',
  ['0: Stock starting gain', '1: Gain step 1', '2: Gain step 2', '3: Gain step 3'],
  '0'),
 ('mono',
  'Mono input',
  'Always copies L to both channels and ignores R. Auto copies L only while R is quiet.',
  ['0: Stereo', '1: Always copy left', '2: Auto while right is quiet'],
  '0'),
 ('pmin', 'Right input phase modulation',
  'Enable this to use the right signal input to modulate playback position while the left input has no signal.',
  ['0: Normal audio input', '1: Phase modulation'], '0'),
 ('cpul',
  'CPU troubleshooting log',
  'Writes cpulog.txt periodically. Leave off for normal performance.',
  ['0: Off', '1: On'],
  '0')]
features=[('New in mg204-c6', 'Recall Gene timing',
  'Set <code>dens 1</code> and <code>dstr 0</code> to boot with stock Gene timing and keep SHIFT + Gene Size available. '
  'On a settings-only reload, include <code>dstr</code> to recall stock timing or a rate from 0.1 to 128 Genes/sec. '
  'Omit it to keep the live timing. A fresh boot with no <code>dstr</code> line uses 1 Gene/sec. '
  'An existing <code>dstr 8.0</code> still selects 8 Genes/sec. External clock takes priority, and available voices limit the overlap of long Genes.'),
 ('New in mg204+c5', 'Record the Gene performance',
  'Choose the S.O.S. recording curve with <code>sosc</code>. Its default gives full incoming and existing audio at noon. With <code>dryk 3</code>, existing audio is the performed Gene playback. Record into a new splice to keep your source, or overdub the current splice.'),
 ('New in mg204+c4', 'Wet-only mixer returns',
  'Set <code>dryk 1</code> to hear only Gene playback while keeping your usual recording controls. With <code>dryk 2</code>, the knob mixes incoming audio with the existing samples under the tape head. <code>dryk 0</code> monitors the selected curve.'),
 ('New in mg204+c4', 'Fixed or growing overdubs',
  'Keep a beat loop at its original length with <code>dlen 0</code>. With <code>dryk 2</code> and <code>dlen 1</code>, select <code>sosc 0</code> or <code>sosc 1</code> and start REC fully counterclockwise on S.O.S. to replace the last or only splice from its start. A longer take extends it. A shorter take keeps its old end.'),
 ('New in mg204+c2',
  'Return to 1:1',
  'Enable <code>vuni 1</code>, hold SHIFT alone for at least half a second, then release to return to exact '
  'forward +1x from any Varispeed position. Soft pickup holds the speed until the combined knob/CV input '
  'reaches or crosses it. Short SHIFT taps retain ordinary splice navigation.'),
 ('New in mg204+c2',
  '1:1 at noon',
  'Enable <code>vctr 1</code> to place forward +1x at calibrated noon in full-range and bidirectional '
  'layouts, with every quantized scale. The 48-52% notch makes it easy to find in continuous mode too. Stop '
  'and reverse fit into the left half in bidirectional modes. Both unity options default to off.'),
 ('New in mg204+c2',
  'Recall the controls you choose',
  'All dialable values can now be included in prepared options: Morph, Gene Size, Slide, Varispeed, S.O.S. '
  'mix, feedback, effects, Turing evolution and Genes per step, alongside density and gain. Select a splice '
  'too. Each new recall is optional; unchecked values stay live during settings-only reload. Included '
  'controls resume from their recalled positions through soft pickup.'),
 ('New in mg204+c2',
  'Prepared effects and splices',
  'SRR and warble retain separate amounts; <code>fxsl</code> selects one or bypasses both. <code>splc</code> '
  'selects a numbered splice; a number above the reel count selects the last while retaining your configured '
  'number. Normal saves preserve configured presets, not subsequent knob movements.'),
 ('Pitch & timing',
  'Expanded Varispeed',
  'Enable <code>vrng 1</code> for +/-4x, or combine it with <code>vsop 2</code> for stop to forward 8x. '
  'Choose octaves, fifths, semitones or a custom scale. <code>vqnt 1</code> keeps pitch quantized normally; '
  'SHIFT + Varispeed temporarily frees it. Default <code>vqnt 0</code> retains SHIFT-to-lock.'),
 ('Sound & movement',
  'Morph Loop and playback effects',
  '<code>mlop 1</code> removes the gaps at minimum Morph; default <code>mlop 0</code> retains them. The '
  'stock seamless-loop setting is also available with <code>mpos 10</code> under normal unclocked '
  'scheduling. SHIFT + Morph controls SRR or warble, and SHIFT + Slide controls start jitter.'),
 ('Sound & movement',
  'Feedback and Turing patterns',
  'SHIFT + S.O.S. controls tape overdub or classic TLA feedback. With <code>sldm 1</code>, SHIFT + Organize '
  'controls evolution, SHIFT + Slide controls repeating spread, and SHIFT + Gene Size sets Genes per step '
  'when independent density is off.'),
 ('Live workflow',
  'Swap settings and keep playing',
  'Remove the idle card, hold SHIFT alone for one second, then insert a prepared matching card while still '
  'holding SHIFT. The live reel stays loaded and the card remains mounted for recording and saving. Explicit '
  'presets recall; omitted ones preserve their live state. An explicit splice recall intentionally changes '
  'selection.'),
 ('Everyday use',
  'Small conveniences',
  'Input gain is remembered. Mono input can copy L onto both channels. Updates can be installed from SD '
  'after the first audio install. Includes Briskcat’s splice-overdub fix and flash prefetch.')]
(W/'site-content.json').write_text(json.dumps({'fields':fields,'features':features},indent=2)+'\n')
preset_names={'mpos':'Morph position','gpos':'Gene Size position','spos':'Slide position',
 'vpos':'Varispeed position','sosp':'S.O.S. mix','splc':'splice',
 'srrp':'SRR amount','jitp':'jitter / spread','wrbp':'warble amount',
 'fbkp':'feedback amount','evop':'Turing evolution','trst':'Turing Genes per step'}
stock_keys = {'vsop', 'inop', 'pmin', 'omod', 'gnsm', 'rsop', 'pmod', 'ckop', 'cvop', 'mcr1', 'mcr2', 'mcr3'}
groups={'vsop':'Varispeed and return to 1:1','mlop':'Morph, loops and chord ratios',
 'gnsm':'Genes, Slide and density','ckop':'Clock and CV output','rsop':'Recording, S.O.S. and feedback','fxsl':'Playback effects',
 'sldm':'Turing patterns','pmod':'Playback and splice selection','ingn':'Input and diagnostics'}
controls=[]
for k,label,desc,choices,default in fields:
 if k in groups: controls.append(f'<h3 class="option-group" id="group-{k}">{groups[k]}</h3>')
 if choices:
  options=''.join(f'<option value="{html.escape(c.split(":")[0])}"'+(' selected' if c.split(':')[0]==default else '')+f'>{html.escape(c)}</option>' for c in choices)
  if k in stock_keys and k not in ('vsop', 'gnsm'):
   options = f'<option value="" disabled hidden>Omitted (stock default {default})</option>'+options
  control=f'<select id="opt-{k}" aria-describedby="help-{k}">{options}</select>'
 elif k in ('mcr1', 'mcr2', 'mcr3'):
  control=f'<input id="opt-{k}" type="text" spellcheck="false" value="{default}" aria-describedby="help-{k} error-{k}"><p class="field-error" id="error-{k}" role="alert" hidden>Enter a signed or unsigned decimal with magnitude 0.0625 to 16 and up to eight decimal places. Zero selects 0.0625.</p>'
 else:
  limits=' type="number" min="0" max="128" step="0.1"' if k=='dstr' else ' type="number" min="1" max="300" step="1"' if k=='splc' else ' type="number" min="0" max="100" step="1"' if k in ('mpos','gpos','spos') else ' type="text"' if k=='scal' else f' type="number" min="{1 if k=="tlen" else 0}" max="{16 if k=="tlen" else 100}" step="1"'
  control=f'<input id="opt-{k}"{limits} value="{default}" aria-describedby="help-{k}">'
 if k in preset_names:
  control=control.replace(' aria-describedby=', ' disabled aria-describedby=')
  preset_name=preset_names[k]
  control+=f'<label class="density-recall" for="recall-{k}"><input id="recall-{k}" type="checkbox" aria-describedby="help-{k}"><span>Recall {preset_name}</span></label>'
 if k=='dstr':
  control+='<label class="density-recall" for="recall-dstr"><input id="recall-dstr" type="checkbox" checked aria-describedby="help-recall-dstr"><span>Recall density on settings-only reload</span></label><p id="help-recall-dstr">Check to recall the timing above on settings-only reload, including stock timing at 0. Uncheck to keep the live timing on reload and use 1.0 Gene/sec at startup. The module adds dstr back when it rewrites options.txt, so check the file again after a normal mount or options save.</p>'
 optional = '<span class="optional-marker">OPTIONAL:</span> ' if k in preset_names or k == 'dstr' else ''
 origin = 'Stock' if k in stock_keys else 'Enhancement'
 controls.append(f'<div class="option-field"><label class="option-header" for="opt-{k}"><span>{optional}{html.escape(label)}</span><code>{k}</code><small class="option-origin">{origin}</small></label>{control}<p id="help-{k}">{html.escape(desc)}</p></div>')
offline_filename = 'morphagene-options-editor.html'
brand_mark = '''<span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>'''
theme_toggle = '''<button class="theme-toggle" id="theme-toggle" type="button" role="switch" aria-label="Night mode" aria-checked="false" title="Switch to night mode" hidden><svg class="theme-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg><svg class="theme-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M20.7 13.2A8.8 8.8 0 0 1 10.8 3.3a8.8 8.8 0 1 0 9.9 9.9Z"/></svg><span id="theme-label">Day</span></button>'''
preset_help_body = '''<p><strong>0% = fully counterclockwise, 50% = noon, 100% = fully clockwise.</strong> These are virtual control positions, following each control’s existing curve; they are not percentages of duration, speed or effect strength. Gene Size runs from longest on the left to shortest on the right. Varispeed uses its calibrated range.</p><p>Check a recall to apply it at startup and settings-only reload. After recall, <strong>soft pickup continues from the preset position</strong>: turn the matching control near or across that position to take over. Effects use their matching SHIFT + knob gesture. Knob and CV are summed, so CV can trigger pickup. Unchecked presets preserve their live values on reload; saves retain configured numbers rather than later knob movements.</p>'''
preset_help = f'<div class="preset-explainer"><h3>What do preset percentages mean?</h3>{preset_help_body}</div>'
def file_drop(zone_id, input_id, prompt, accept):
 return f'''<label id="{zone_id}" class="file-zone file-drop" for="{input_id}">
  <strong>{prompt}</strong>
  <span class="choose-button">Choose file</span>
  <input id="{input_id}" class="visually-hidden" type="file" accept="{accept}">
</label>'''

firmware_picker = file_drop('firmware-drop', 'firmware', 'Drop the official <code>mg204.wav</code> here', '.wav,audio/wav')
file_picker = file_drop('options-drop', 'options-file', 'Drop <code>options.txt</code> here', '.txt,text/plain')+'''
<p id="options-status" role="status" aria-live="polite"></p>
<button type="button" class="secondary-button" id="options-reset" aria-haspopup="dialog">Reset to defaults</button>
<dialog id="options-reset-dialog" aria-labelledby="reset-title" aria-describedby="reset-description">
  <h2 id="reset-title">Reset all editor settings?</h2>
  <p id="reset-description">Restore the stock settings and enhancement defaults. This clears knob and splice recalls and sets startup density to 1.0 Gene/sec. Your card changes only when you replace its options.txt.</p>
  <div class="reset-actions"><button type="button" id="reset-cancel" class="secondary-button" autofocus>Cancel</button><button type="button" id="reset-confirm" class="primary-button">Reset to defaults</button></div>
</dialog>'''
fields_and_save = '''<div class="options-grid">'''+''.join(controls)+'''</div><p id="options-note" tabindex="-1"></p><label for="options-text">Generated file / settings snippet</label><textarea id="options-text" readonly rows="12" spellcheck="false"></textarea><div id="options-save-row" hidden><button id="options-save" class="primary-button">Download options.txt</button></div>'''
download_editor = f'''<p class="offline-download"><a href="{offline_filename}" download="{offline_filename}">Download the offline options editor</a> · Keep this HTML file on your SD card and open it in a browser anywhere.</p>'''
articles=''.join(f'<article><p class="control-path">{group}</p><h3>{title}</h3><p>{body}</p></article>' for group,title,body in features)
(W/'index.html').write_text('''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Morphagene mg204-c6 firmware patcher and offline options editor.">
<meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>Morphagene mg204-c6 / firmware patcher</title><script src="theme.js"></script><link rel="stylesheet" href="styles.css"><script defer src="remixes.js"></script><script defer src="page.js"></script><script defer src="options.js"></script><script defer src="app.js"></script></head>
<body><a class="skip-link" href="#patcher">Skip to patcher</a><div class="page-shell">
<header class="site-header"><a class="brand" href="./">'''+brand_mark+'''<span>Morphagene <span class="brand-subtitle">/ mg204-c6</span></span></a><div class="header-actions"><span class="local-badge">Browser-local</span>'''+theme_toggle+'''</div></header>
<main><section class="intro"><p class="eyebrow">MORPHAGENE / CUSTOM FIRMWARE</p><h1>Gene timing<br>at startup.</h1><p class="intro-copy">Start with stock Gene timing and bring in overlapping Genes when you want them. Includes expanded Varispeed, switchable Morph Loop, wet-only overdubs and live settings reload. Built on <a href="https://briskcat.github.io/morphagene-mods/">Briskcat’s Morphagene mods</a>.</p><nav class="intro-links" aria-label="On this page"><a href="#installation">First install</a><a href="#patcher">Patch firmware</a><a href="#features">Features</a><a href="#options">Options editor</a><a href="#guides">PDF guides</a></nav><div class="version-path"><span><small>OFFICIAL</small><strong>mg204</strong></span><span aria-hidden="true">→</span><span><small>CUSTOM FIRMWARE</small><strong>mg204-c6</strong></span></div></section>
<section class="installation-note first-install" id="installation" aria-labelledby="first-install-title">
<div class="card-heading first-install-heading"><span class="section-number">01</span><h2 id="first-install-title">The first time</h2><span class="install-required">Required</span></div>
<div class="first-install-copy"><p>The first time, install your mod build using <strong><a href="https://www.makenoisemusic.com/modules/morphagene/">Make Noise’s official audio update procedure</a></strong>, just as you would an official firmware update.</p><p><em>The SD-card updater is itself one of the mods. It becomes available after this first audio install; subsequent updates can come from the card.</em></p><p>Follow the instructions supplied with Make Noise’s official update and <a href="https://briskcat.github.io/morphagene-mods/#first-time">Briskcat’s first-install guide</a>.</p><p class="filename-note"><strong>Recovery:</strong> use the same audio procedure with the original official <code>mg204.wav</code>. The mods do not replace the bootloader.</p></div>
<ol class="install-steps">
<li><a href="#patcher">Build below</a> and download the <strong>update WAV</strong>, <code>mg204-c6.wav</code>.</li>
<li>Remove the SD card. Connect your computer or phone to <strong>Left Signal IN</strong>, at about 80% player volume. Disable effects, EQ, notifications and other sounds.</li>
<li>Power on while holding <strong>REC</strong>. Only the SPLICE window lights green. Release REC.</li>
<li>Play the update WAV from start to finish. The windows flash while it loads, then all lights flash when it is done.<p class="install-aside"><em>Do not touch the module or interrupt playback. If the update fails, power off and start again from step 3.</em></p></li>
<li>Finish with Make Noise’s Varispeed calibration: power off, then power on holding <strong>SPLICE</strong>. Release SPLICE when its window lights green. Turn Varispeed fully counterclockwise and clockwise, press SPLICE, then power-cycle.</li>
<li>After this first audio install, put <code>mgmod.bin</code> at the root of the card and power on for later updates. A successful update renames it <code>mgmod.ok</code>.</li>
</ol></section>
<div class="workspace"><section class="patch-card" id="patcher"><div class="card-heading"><span class="section-number">02</span><h2>Make your firmware</h2></div><p>Download <a href="https://www.makenoisemusic.com/modules/morphagene/">official Morphagene mg204 firmware</a>, extract it, then drop <code>mg204.wav</code> into the area below or choose the file. The file is verified and patched locally; nothing is uploaded.</p><p class="backup-reminder">Back up the entire card and keep the original Make Noise update for recovery. If your Morphagene already has the SD updater, download <code>mgmod.bin</code> for the SD update.</p>'''+firmware_picker+'''<p id="firmware-status" role="status" aria-live="polite"></p><select id="remix" aria-label="Firmware build" hidden></select><p id="remix-description" hidden></p><ul id="remix-modules" hidden></ul><div id="build-buttons" hidden><button id="build-wav" class="primary-button">Download update WAV</button><button id="build-card" class="secondary-button">Download mgmod.bin</button></div><p id="build-status" role="status" aria-live="polite"></p><p class="small-copy">This patcher builds mg204-c6 from your official update WAV. Dry kill defaults to off. Morph Loop defaults to off; enable it with <code>mlop 1</code>. No separate Morph Loop firmware is needed.</p><noscript><p>Enable JavaScript to patch firmware and edit options. The guides remain available below.</p></noscript></section>
<aside class="sidebar" id="guides"><h2>Keep a guide nearby.</h2><p>For mixer sends and looping, see pages 12–13 of the guide. The one-page quick card lists recording modes and panel gestures.</p><div class="paper-choices"><h3>mg204-c6 guide</h3><div><a href="morphagene-manual-letter.pdf">US Letter</a><a href="morphagene-manual-a4.pdf">A4</a></div></div><div class="paper-choices"><h3>mg204-c6 quick card</h3><div><a href="morphagene-quick-card-letter.pdf">US Letter</a><a href="morphagene-quick-card-a4.pdf">A4</a></div></div><p class="playback-note">The website contains patch data only. Keep your generated firmware files for personal use; share the patcher rather than Make Noise’s firmware.</p>
<section class="support-note" aria-labelledby="support-title">
            <h2 id="support-title">Enjoying the extra control?</h2>
            <p>This modification is offered free of charge, but if you find it useful, a tip would make my day!</p>
            <a class="coffee-button" href="https://www.buymeacoffee.com/vwal" target="_blank" rel="noopener noreferrer" aria-label="Buy me a coffee — support vwal (opens in a new tab)">
              <svg class="coffee-cup" viewBox="0 0 36 44" aria-hidden="true" focusable="false">
                <path d="M7 12h22l-3 27H10z" fill="#ffffff" stroke="#000000" stroke-width="2.4" stroke-linejoin="round"/>
                <path d="M8 7h20l2 5H6z" fill="#ffffff" stroke="#000000" stroke-width="2.4" stroke-linejoin="round"/>
                <path d="M12 3h12l3 4H9z" fill="#000000"/>
                <path d="M9 21h18l-1 10H10z" fill="#FFDD00" stroke="#000000" stroke-width="2" stroke-linejoin="round"/>
              </svg>
              <span>Buy me a coffee</span>
            </a>
          </section>
</aside></div>
<section class="feature-catalog" id="features"><p class="eyebrow">THE EXTENDED VERSION</p><h2>From pitch to performance.</h2><p class="catalog-intro">A single build, with options for the way you play. All extended range, density, normal quantization and Morph Loop switches default to off.</p><div class="feature-grid">'''+articles+'''</div></section>
<section class="feature-catalog" id="options"><p class="eyebrow">OPTIONS.TXT</p><h2>Set up your starting point.</h2><p>Load the <code>options.txt</code> created by your Morphagene. Edit stock and enhancement settings together. The editor keeps the first state line and unrecognized lines. Recognized duplicates are reduced to one entry. Zero selects the minimum for Turing loop length, Genes per step, splice number and the three chord ratios. Other invalid ordinary values reset to their documented defaults. Optional recalls are unchecked when missing or invalid, and their numeric choices stay available for re-enabling. Only checked presets are included; module options saves preserve omitted preset keys. Review the generated file before saving.</p>'''+download_editor+preset_help+file_picker+fields_and_save+'''</section>
<section class="installation-note" id="reload"><div><p class="eyebrow">ADVANCED LIVE WORKFLOW</p><h2>Swap settings. Keep playing.</h2><p><strong>Trusted cards only: no reel-content verification.</strong> Prepare cards with identical reel names, WAV contents and splice files; change only options.txt. Same card capacity alone is not enough. A mismatched card can cause wrong saves or overwrite audio.</p><p>Recording, splice edits or reel changes make other copies stale. Synchronize them again before the next settings-only swap. Do not record or edit while the card is out.</p></div><ol class="install-steps"><li>With the card mounted and ordinary card activity finished, stop recording and remove the card. Wait for the mounted SHIFT light to go out.</li><li>Hold <strong>SHIFT alone for one second</strong>, until its LED is steady. Arming is unavailable while a card is mounted. Avoid knob movement or other buttons.</li><li>Keep SHIFT held and insert the prepared matching card. Two short flashes mean success; three mean failure. Keep the card inserted through confirmation, then release SHIFT.</li><li>Success keeps the live reel and card mounted for recording/saving. Omitted presets preserve live parameters; an explicit splice preset intentionally changes the selected splice. Failure leaves playback settings unchanged and the card unmounted. Remove it and mount normally to recover.</li><li>To load a different reel, use normal mounting without the armed hold. That retains the usual playback interruption.</li></ol></section>

<section class="version-history" id="versions"><details><summary>Version by version</summary><div class="version-entries"><article><h3>mg204-c6 — Recall stock Gene timing</h3><p>With <code>dens 1</code>, set <code>dstr 0</code> to recall stock Gene timing on power-up or a settings-only reload. SHIFT + Gene Size still lets you choose an independent rate. Omitting <code>dstr</code> starts at 1.0 Gene/sec on power-up and preserves live timing on a settings-only reload. Cards that already specify 8 keep that rate until you edit them.</p><p>Both firmware readers and both editors now give explicit zeros consistent meanings across all 45 settings. Zero selects 1 for <code>tlen</code>, <code>splc</code> and <code>trst</code>, and +0.0625 for the three Morph chord ratios. To skip an optional recall, uncheck its box. The module and editors write <code>// firmware version 204-c6</code>.</p></article><article><h3>mg204+c5 — Performance overdubs and Gene timing</h3><p><code>dryk 3</code> records incoming audio together with the performed Gene playback on a wet-only return. The main S.O.S. knob now offers three curves. The default gives full input and playback at noon. Choose <code>sosc 1</code> with <code>dryk 2</code> to keep the full-input tape overdub from c4. The first take on an empty reel always records full input.</p><p>With <code>dens 1</code>, hold SHIFT and turn Gene Size fully CCW for stock timing, or just clockwise for independent density starting at 0.1 Genes/sec. Card removal is recognized after erasing the last splice on a single-sector reel. Both editors include the new curve, and the module and editors write <code>// firmware version 204+c5</code>.</p></article><article><h3>mg204+c4 — Wet-only recording and overdub length</h3><p>Optional dry kill for mixer sends, S.O.S. feedback on overdubs, and fixed or extending takes. The website accepts dropped WAV and settings files. The downloadable offline editor includes all 44 stock and enhancement settings, optional recalls, and reset with confirmation. The guide and quick card cover the new recording modes. The module and editor write <code>// firmware version 204+c4</code>.</p></article><article><h3>mg204+c3 — Varispeed layout on card mount</h3><p>On startup or a normal mount, earlier releases could read <code>vsop 2</code> in a long <code>vrng</code> comment as a setting and switch to forward-only playback. The reader now skips wrapped text, including on cards written by earlier builds. The firmware and editor write a shorter range comment and label rewritten files <code>// firmware version 204+c3</code>.</p><p>If an older build saved <code>vsop 2</code> over your choice, select your preferred bidirectional layout once and save <code>options.txt</code>.</p></article><article><h3>mg204+c2 — Return to 1:1 and prepared presets</h3><p>Optional half-second SHIFT hold/release recalls exact forward +1x without changing short-tap splice navigation. Optional +1x at calibrated noon works across layouts, ranges and scales, with a 48-52% notch.</p><p>All dialable values can be included in presets, with independent recall checkboxes, live reload and soft pickup. Adds splice recall with last-splice fallback, separate SRR/warble amounts, reliable effects-off behavior, clearer editor guidance, reorganized controls and updated manuals/quick cards. Rewritten options identify firmware version 204+c2.</p></article><article><h3>mg204+c — Initial release</h3><p>Extended +/-4x or forward 8x Varispeed, normal/SHIFT quantization and custom scales, independent 0.1-128 Genes/sec density with startup/live recall, switchable Morph Loop, and trusted-card settings-only reload that preserves the live reel and leaves the card mounted. Built on Briskcat’s feedback, effects, jitter/Turing, gain, mono and SD-updater mods.</p></article></div></details></section>
<section class="use-note"><h2>Performance &amp; credits</h2><p>The trusted-card reload removes full-reel scanning; SD mount, options reads and file reconnection still take time. Earlier hardware testing confirmed armed insertion and ordinary options applying without an audible playback interruption. The c5 dry-kill modes and stock-timing gesture were tested on a Morphagene. Automated checks cover playback, overdubs, saved reels, card removal and settings recall. Exact latency and every performance combination have not been measured. High Morph, short Genes, dense scheduling and overdubbing can exhaust CPU headroom. Try lower density/overlap, the tape Morph cap, or warble instead of SRR.</p><p>Upstream firmware mods, browser patcher and audio encoder: <a href="https://github.com/briskcat/morphagene-mods">Briskcat / morphagene-mods</a> (MIT). Extended version: <a href="https://github.com/vwal/morphagene-patcher/tree/mg204-c6">vwal / mg204-c6 source</a>. Bootloader encoding derives from <a href="https://github.com/pichenettes/stm-audio-bootloader">Émilie Gillet’s stm-audio-bootloader</a>. <a href="Briskcat-MIT.txt">Upstream MIT license</a>. Morphagene and Make Noise are trademarks of Make Noise; this project is unofficial and not endorsed by Make Noise.</p><h2>Free to use and share. Not for sale.</h2><p><strong>Copyright &copy; 2026 vwal</strong> for our original additions. Use, modify and share them for free with copyright, attribution and license notices retained. Selling them, including in paid bundles, products containing them or paid firmware services, is prohibited except under the Make Noise exception or separate written permission. <strong>Make Noise may include our additions in its official firmware and products, including commercial distribution, with notices retained.</strong> This also covers authorized distribution and resale of those official products. Paid performances, recordings and other musical output remain allowed.</p><p>Upstream copyright &copy; 2026 the morphagene-mods contributors remains under MIT. Our no-sale terms do not restrict the upstream work alone. <a href="LICENSE.txt">Read the complete Attribution - No Sale license and upstream notice</a>. This extended release is source available; it is not MIT or OSI open source.</p></section></main><footer class="site-footer"><p>vwal / Morphagene extended firmware</p><p>mg204-c6 · Public release</p><p>This project contains carefully tested AI-generated code.</p><p>Independent customization. Not an official Make Noise release.</p></footer></div></body></html>\n''')
shutil.copy2(S/'tools/bitbox-style.css',W/'styles.css')
with (W/'styles.css').open('a') as f:f.write('''\n/* Morphagene form additions. */
.option-group{grid-column:1/-1;margin:18px 0 -8px;font-size:22px;color:var(--green)}
.preset-explainer{margin:24px 0;padding:24px;border-left:4px solid var(--green);background:var(--card)}
.preset-explainer h3{margin:0 0 12px}.preset-explainer p:last-child{margin-bottom:0}
.version-history{margin:40px 0;padding:24px;border:1px solid var(--line);border-radius:8px;background:var(--card)}
.version-history summary{font-size:21px;font-weight:650;cursor:pointer;color:var(--green)}
.version-history summary:focus-visible{outline:3px solid var(--orange);outline-offset:5px}
.version-entries{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:32px;margin-top:20px}
.version-entries h3{font-size:18px}.version-entries p{font-size:14px;line-height:1.6}
.site-footer{flex-wrap:wrap}.site-footer p:nth-child(n+3){flex-basis:100%;margin:0}
@media(max-width:650px){.version-entries{grid-template-columns:1fr;gap:10px}}
/* First installation appears before the firmware builder. */
.first-install{margin:0 0 32px;gap:22px 36px}
.first-install-heading{grid-column:1/-1;margin:0;flex-wrap:wrap}
.first-install .section-number{display:inline}
.install-required{padding:3px 8px;border:1px solid #aebeb0;border-radius:4px;background:var(--card);color:var(--green);font-size:10px;font-weight:700}
.first-install p:not(.eyebrow),.first-install .install-steps{font-size:13px}
.first-install-copy>p:first-child{margin-top:0}
.first-install .install-aside{margin-top:6px}
.secondary-button{padding:12px 18px;margin-top:12px;border:1px solid var(--green);border-radius:5px;background:var(--card);color:var(--green)}
.options-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin:26px 0}.option-field{padding:20px;background:var(--card);border:1px solid var(--line);border-radius:8px}
.option-field label{display:block;font-weight:650;margin-bottom:10px}.option-field code{color:var(--orange)}
.option-field .option-header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 12px;align-items:baseline}
.option-origin,.optional-marker{font-size:.75rem;color:var(--muted);font-weight:500}
.option-origin{grid-column:1/-1}.optional-marker{letter-spacing:.03em}
.option-field .field-error{color:var(--red)}
.option-field p{font-size:13px;color:var(--muted);margin-bottom:0}select,.option-field input,textarea{font:inherit;width:100%;padding:10px;border:1px solid #aab7a9;border-radius:5px;background:white;color:var(--ink)}
.option-field .density-recall{display:flex;align-items:flex-start;gap:10px;margin:16px 0 0;line-height:1.4;cursor:pointer}
.option-field input[type=checkbox]{width:18px;height:18px;flex:0 0 18px;padding:0;margin:2px 0 0;accent-color:var(--green);cursor:pointer}
.option-field input:disabled,.option-field select:disabled{background:var(--card);color:var(--muted);opacity:.7}
textarea{font:12px/1.6 ui-monospace,monospace;resize:vertical;margin:12px 0}input[type=file]{display:block;max-width:100%;margin:12px 0}.feature-grid h3{margin:0;font-size:20px}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid var(--orange);outline-offset:3px}
[data-kind=error]{color:var(--red)}[data-kind=ok]{color:var(--green)}
@media(max-width:650px){.options-grid{grid-template-columns:1fr}.intro{padding-right:0}.feature-grid h3{font-size:19px}}
/* Day/night mode shares the same layout and accessible controls. */
:root{--input-bg:#ffffff;--field-wash:#f5f7f1;--control-line:#aab7a9}
:root[data-theme="dark"]{
  color-scheme:dark;
  --paper:#141c19;--card:#1d2823;--ink:#e5ece5;--muted:#aebdb2;
  --line:#3b4d42;--green:#9bceb0;--green-light:#24372c;
  --orange:#eeab83;--orange-light:#3c2b23;--red:#f3aaa0;--red-light:#442824;
  --input-bg:#141f19;--field-wash:#1c2e23;--control-line:#687e6d;
}
.header-actions{display:flex;align-items:center;gap:16px;flex-shrink:0}
.theme-toggle{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:44px;min-width:84px;padding:8px 12px;border:1px solid var(--control-line);border-radius:24px;background:var(--card);color:var(--ink);font-size:12px;font-weight:600}
.theme-toggle:hover{background:var(--green-light);border-color:var(--green)}
.theme-toggle svg{width:17px;height:17px;flex:none}
.theme-moon{display:none}
[data-theme="dark"] .theme-sun{display:none}
[data-theme="dark"] .theme-moon{display:block}
.backup-reminder,.file-zone{background:var(--field-wash);border-color:var(--control-line)}
.file-zone.is-dragging{background:var(--orange-light);border-color:var(--orange)}
.file-drop{position:relative;gap:10px;cursor:pointer;text-align:center}
.file-drop:focus-within{outline:3px solid var(--orange);outline-offset:3px}
#options-status,#firmware-status{overflow-wrap:anywhere}
#options-reset-dialog{box-sizing:border-box;width:min(28rem,calc(100% - 32px));padding:24px;background:var(--card);color:var(--ink);border:1px solid var(--control-line);border-radius:10px}
#options-reset-dialog::backdrop{background:rgb(0 0 0 / .5)}
#options-reset-dialog p{margin:12px 0 20px}
.reset-actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:10px}
.reset-actions button{width:auto;margin:0}
select,.option-field input,textarea{background:var(--input-bg);border-color:var(--control-line)}
.option-field input:disabled,.option-field select:disabled{background:var(--card)}
.paper-choices a,.install-required,.installation-note .filename-note{border-color:var(--control-line)}
.skip-link{color:var(--paper)}
[data-theme="dark"] .primary-button,[data-theme="dark"] .download-button{color:var(--paper)}
[data-theme="dark"] .primary-button:hover:not(:disabled),[data-theme="dark"] .download-button:hover{background:#b7e2c7;border-color:#b7e2c7}
[data-theme="dark"] .primary-button:disabled{background:var(--line);border-color:var(--line);color:var(--muted)}
@media(max-width:460px){.site-header{gap:12px}.brand{font-size:14px;gap:8px}.header-actions{gap:10px}.theme-toggle{min-width:74px;padding:8px}}
@media(max-width:340px){.site-header{flex-wrap:wrap;padding:16px 0;gap:12px}.header-actions{margin-left:auto}}

.offline-download a{font-weight:650}
.offline-editor main{padding:40px 0}
.offline-instructions{max-width:66ch;color:var(--muted)}
.offline-file{max-width:42rem;margin:24px 0 16px}
.offline-file p:empty{display:none}
.offline-file p{margin:8px 0 0}
.offline-shortcuts{display:flex;align-items:baseline;flex-wrap:wrap;gap:12px 26px}
.offline-editor summary{cursor:pointer;color:var(--green);font-weight:600}
.offline-shortcuts nav{display:grid;gap:5px;margin:9px 0 4px 16px}
.offline-help{margin-top:12px;max-width:76ch}
.offline-editor h1{font-size:clamp(32px,5vw,48px);margin-bottom:12px}
.offline-editor .option-group{margin-top:12px;scroll-margin-top:14px}
.offline-editor footer{padding:20px 0 32px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
.offline-editor footer p{margin:0 0 8px}
.offline-license pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;max-width:85ch}

''')
shutil.copy2(S/'LICENSE',W/'LICENSE.txt')
shutil.copy2(S/'LICENSES/Briskcat-MIT.txt',W/'Briskcat-MIT.txt')


def csp_hash(text):
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    return "'sha256-" + base64.b64encode(digest).decode('ascii') + "'"


# A copy on the card has no sibling assets. Embed the same classic scripts,
# controls and styles as the online editor, plus the full redistribution notice.
styles = (W/'styles.css').read_text(encoding='utf-8')
scripts = [(W/name).read_text(encoding='utf-8') for name in ('theme.js', 'page.js', 'options.js')]
if '</style' in styles.lower() or any('</script' in script.lower() for script in scripts):
    raise ValueError('An inline asset contains an HTML end tag')
policy = "default-src 'none'; base-uri 'none'; form-action 'none'; script-src " + ' '.join(map(csp_hash, scripts)) + '; style-src ' + csp_hash(styles)
group_links = '\n'.join(f'<a href="#group-{key}">{html.escape(name)}</a>' for key, name in groups.items())
template = Template((S/'tools/offline_editor.html.in').read_text(encoding='utf-8'))
standalone = template.substitute(
    policy=policy, styles=styles, scripts='\n'.join(f'<script>{script}</script>' for script in scripts),
    version=html.escape(json.loads((W/'release.json').read_text())['release']),
    brand_mark=brand_mark, theme_toggle=theme_toggle, file_picker=file_picker,
    group_links=group_links, preset_help_body=preset_help_body, fields_and_save=fields_and_save,
    license_text=html.escape((S/'LICENSE').read_text(encoding='utf-8')),
)
outputs = [W/offline_filename, S/'tools/offline_editor.html']
if package_dir is not None:
    outputs.append(package_dir/offline_filename)
for path in outputs:
    path.write_bytes(standalone.encode('utf-8'))
