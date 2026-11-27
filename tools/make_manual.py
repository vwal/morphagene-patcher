#!/usr/bin/env python3
"""Build the mg204+c7 guide and quick card."""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--card', required=True, type=Path)
parser.add_argument('--font-dir', required=True, type=Path)
parser.add_argument('--target-sha', default='')
parser.add_argument('--target-size', default='')
parser.add_argument('--paper', choices=['letter','a4'], default='letter')
parser.add_argument('--draft', action='store_true', help='Mark unpublished documents as awaiting hardware testing')
args = parser.parse_args()
paper = A4 if args.paper=='a4' else letter
paper_name = 'A4' if args.paper=='a4' else 'US Letter'
width, height = paper
right = width-44
content_width = right-44
top_shift = height-letter[1]
os.environ.setdefault('SOURCE_DATE_EPOCH', str(int(datetime(2026,11,26,tzinfo=timezone.utc).timestamp())))
for name, file in [('Guide','Regular'),('GuideB','Bold')]:
    pdfmetrics.registerFont(TTFont(name,str(args.font_dir/f'LiberationSans-{file}.ttf')))
pdfmetrics.registerFontFamily('Guide',normal='Guide',bold='GuideB',italic='Guide',boldItalic='GuideB')
ink,green,muted,rust,rule,pale = [colors.HexColor(c) for c in
    ('#20322c','#285843','#45594f','#91431f','#cdd8cf','#eaf2eb')]
GUIDE_BUILD = 'mg204+c7'
GUIDE_PAGES = 15
SITE='https://briskcat.github.io/morphagene-mods/'
MANUAL='https://www.makenoisemusic.com/modules/morphagene/'
def link(url,label):
    return '<link href="%s" color="#285843"><u>%s</u></link>'%(url,label)
class Guide:
    def __init__(self,path,card=False):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.c=canvas.Canvas(str(path),pagesize=paper,pageCompression=1,invariant=1)
        self.c.setCreator('vwal | Morphagene firmware reference');self.c.setAuthor('vwal');self.c.setTitle('Morphagene '+GUIDE_BUILD+' | '+('Quick reference card' if card else 'Firmware reference guide')+' | '+paper_name+' | Extended firmware'+(' | DRAFT' if args.draft else ''))
        self.card=card;self.n=0
    def text(self,txt,x,y,size=11,font='Guide',color=ink):
        c=self.c;c.setFont(font,size);c.setFillColor(color);c.drawString(x,y,txt)
    def para(self,txt,x,y,width,size=11,leading=16,color=ink):
        paragraph=Paragraph(txt,ParagraphStyle('t',fontName='Guide',fontSize=size,leading=leading,textColor=color))
        _,h=paragraph.wrap(width,680);paragraph.drawOn(self.c,x,y-h);return h
    def start(self,title,tag,sub,title_size=30):
        self.n+=1;c=self.c
        c.translate(0,top_shift)
        self.text('MORPHAGENE   /   CUSTOM FIRMWARE',44,751,9,'GuideB',green)
        badge = GUIDE_BUILD
        badge_width = 86 if self.card else 118
        c.setFillColor(green);c.roundRect(right-badge_width,743,badge_width,20,5,fill=1,stroke=0)
        badge_x = right-(badge_width+pdfmetrics.stringWidth(badge,'GuideB',10))/2
        self.text(badge,badge_x,749,10,'GuideB',colors.white)
        c.setStrokeColor(rule);c.line(44,731,right,731)
        self.text(tag.upper(),44,706,9,'GuideB',rust)
        self.text(title,44,669,title_size,'GuideB')
        self.y=651-self.para(sub,44,651,content_width,11,15,muted)-15
        c.bookmarkPage('p'+str(self.n));c.addOutlineEntry(title,'p'+str(self.n),0)
    def section(self,title):
        self.y-=6;self.text(title,44,self.y-15,15,'GuideB',green);self.y-=27
    def body(self,txt):
        self.y-=self.para(txt,44,self.y,content_width)+10
    def rows(self,rows,left=124,size=10.5,leading=14.7,pad=7):
        c=self.c
        for label,detail in rows:
            y=self.y
            h1=self.para('<b>'+label+'</b>',47,y-pad,left-12,size,leading)
            h2=self.para(detail,44+left,y-pad,content_width-left-2,size,leading)
            self.y-=max(h1,h2)+2*pad
            c.setStrokeColor(rule);c.line(44,self.y,right,self.y)
        self.y-=6
    def note(self,txt):
        width=content_width-24;h=self.para_height(txt,width)
        self.c.setFillColor(pale);self.c.roundRect(44,self.y-h-18,content_width,h+18,5,fill=1,stroke=0)
        self.para(txt,56,self.y-9,width,10.5,15,green);self.y-=h+30
    def para_height(self,txt,width):
        return Paragraph(txt,ParagraphStyle('m',fontName='Guide',fontSize=10.5,leading=15)).wrap(width,700)[1]
    def finish(self):
        assert self.y+top_shift>=46,('page overflow',self.n,self.y)
        c=self.c;c.translate(0,-top_shift);c.setStrokeColor(rule);c.line(44,42,right,42)
        self.text('(c) 2026 vwal / Morphagene',44,26,8,'GuideB',green)
        self.text('DRAFT / hardware test pending' if args.draft else ('Quick reference card' if self.card else 'Custom firmware reference'),155,26,8.5,'Guide',muted)
        c.setFont('Guide',9);c.setFillColor(muted);c.drawRightString(right,26,paper_name+'    |    '+('1 / 1' if self.card else f'{self.n} / {GUIDE_PAGES}'))
        c.showPage()


g=Guide(args.output)
g.start('Return to your sound','mg204+c7 / firmware guide','Organize reels into banks, audition splices on the card or switch on a Gene boundary while your current patch keeps playing. Independent customization built on Briskcat’s Morphagene mods.')
g.section('One build, selectable features')
g.body('Use <b>bank 1</b> to start browsing from the card root, or leave <b>bank 0</b> for the ordinary reel browser. With <b>thru 2</b>, turning Organize fully clockwise steps through the playing reel in the direction set by Varispeed.')
g.rows([('Return to 1:1 / 3','A half-second SHIFT hold/release resets to original forward playback speed, with soft pickup. Place +1x at noon and choose a wider notch for forward unity, reverse unity or both.'),('Pitch and timing / 4','Expanded +/-4x or forward 8x Varispeed, quantization, independent density and Morph Loop.'),('Sound and motion / 5','Tape/TLA feedback, SRR, warble, jitter and Turing patterns.'),('Live settings / 6','Matching-card settings reload keeps the live reel and card mounted. Included presets apply; omitted values stay live.'),('Presets / 7-8','All dialable values can be included in prepared options. Understand percentages, pickup, splice selection and saving.'),('Reference / 9-11','Options tables, testing, credits and release history. Installation and recovery are on page 2.'),('Overdubbing / 12-13','Choose what reaches the outputs and what goes on the reel. Set up a clean loop, print overlapping Genes or fade layers on a mixer send.'),('Banks and splices / 14-15','Prepare a bank, find a splice by ear, queue a change during a performance or step through a reel automatically.')],left=130,pad=5)

g.note('<b>Defaults.</b> Expanded range, independent density, normal quantization, Turing mode, Morph Loop, unity controls and preset recalls are optional. Tape mode and SRR are selected. Set their amounts with a gesture or an explicit preset.')
g.finish()

g.start('Install and recover','Audio first / SD thereafter','Back up the entire SD card before installing. Keep your original Make Noise update WAV for recovery.')
g.section('Build your update')
g.body('Drop the official Make Noise <b>mg204.wav</b> into the '+link('https://vwal.github.io/morphagene-patcher/','firmware patcher')+' or use Choose file. Download <b>mg204+c7.wav</b> for the first audio installation or <b>mgmod.bin</b> to update a module that already has the SD updater.')
g.section('First installation by audio')
g.rows([('1 / Prepare','Remove the SD card. Connect the player to <b>Left Signal IN</b>, starting at about 80% volume. Disable effects, EQ, sound enhancements and notifications.'),('2 / Bootloader','Power on holding <b>REC</b>. Only the SPLICE window lights green. Release REC.'),('3 / Play the WAV','Play the generated update WAV without interruption. Windows flash during loading; all lights flash on completion. Keep power stable.'),('4 / Calibrate','Follow Make Noise’s update instructions: power on holding <b>SPLICE</b>, turn Varispeed fully both ways, press SPLICE, then power-cycle.')],left=100,pad=5)
g.section('Later SD updates and stock recovery')
g.body('Place <b>mgmod.bin</b> in the card root and power on. The installed SD updater handles it automatically; successful installation renames it <b>mgmod.ok</b>. For stock recovery, use the audio procedure with the original official <b>mg204.wav</b>. The mods do not replace the bootloader.')
g.body('If audio loading fails, adjust player level and retry with an unprocessed playback path. If SD updating does not start, verify the exact filename and that the SD updater was installed previously.')
g.note('Installation procedure follows '+link(SITE,'Briskcat’s upstream guide')+' and '+link(MANUAL,'Make Noise’s official instructions')+'. Generated firmware contains Make Noise code; keep it for personal use.')
g.finish()

g.start('Return to 1:1','Varispeed / gesture, center and notches','Exact +1x plays at recorded speed forward. Exact -1x plays at recorded speed in reverse.')
g.section('Recall forward unity with SHIFT')
g.body('Set <b>vuni 1</b>. Hold <b>SHIFT alone for at least 0.5 seconds</b> with the knobs still, then release. Playback goes to +1x from any knob position. It stays there until the combined Varispeed knob/CV input reaches or crosses the pickup point.')
g.body('A short SHIFT tap still advances a splice immediately. Moving a knob, pressing another button, or starting a card operation cancels the reset. Keep the SHIFT jack unpatched for manual recall. The knob and CV share a reading, so changing CV can pick up the held speed or cancel a gesture.')
g.section('Set the center and choose the notches')
g.rows([
    ('vctr / center', '<b>1</b> puts +1x at calibrated noon with zero CV in every layout, range and scale. On bidirectional layouts, stop and reverse fit in the left half. <b>0</b> keeps the layout’s usual unity position.'),
    ('ntch / notches', '<b>0</b> adds no notch. <b>1</b> widens forward +1x, <b>2</b> widens reverse -1x, and <b>3</b> widens both. Each spans about 4% of the calibrated knob travel. Reverse requires a bidirectional layout.'),
    ('Omitting ntch', 'At boot or normal mount, vctr 1 gives the familiar 48-52% forward notch and vctr 0 adds none. On settings-only reload, omission keeps the live notch choice.'),
], left=110, size=10.5, leading=14, pad=4)
g.section('Varispeed layouts')
g.rows([('vsop 0 / classic','Original bidirectional response with smooth braking around stop.'),
        ('vsop 1 / V/oct','Alternate bidirectional pitch response. With a carefully adjusted input attenuverter, CV supports V/oct tracking.'),
        ('vsop 2 / forward','Forward only, stop fully CCW and finer low-speed control. Extended range reaches 8x.')],left=115,size=10.4,leading=14,pad=4)
g.note('For a continuous slide through noon, use <b>vctr 1, ntch 0, octl 0</b>. Quantization still holds scale steps. Extended or centered mapping changes V/oct tracking. A recalled <b>vpos 50</b> gives +1x with vctr 1.')
g.finish()

g.start('Pitch, density and loops','Varispeed / Gene timing / Morph','A SHIFT gesture consumes that hold: releasing it does not advance the splice. After a gesture, most knobs use pickup at their previous effective position, including a recalled preset.')
g.rows([('Expanded range','<b>vrng 1</b>: stock vsop 0/1 layouts extend to +/-4x; <b>vsop 2</b> gives forward-only stop to 8x. <b>vrng 0</b> retains stock ranges.'),('SHIFT-to-lock','<b>vqnt 0</b> (default): SHIFT + Varispeed locks to the selected scale. The lock stays after release; turn about half an octave away to release it.'),('Quantize normally','<b>vqnt 1</b>: normal Varispeed is quantized. SHIFT + Varispeed temporarily adjusts continuously; release snaps back. Other SHIFT gestures keep pitch quantized. <b>octl 0</b> disables quantization in either mode.'),('Choose a scale','<b>octl 1</b> octaves; <b>2</b> octaves and fifths; <b>3</b> semitones; <b>4</b> custom. For custom, use <b>scal 3,5,7,10</b> for minor pentatonic, for example. Root and octaves are always included.'),('Independent density','Set <b>dens 1, dstr 0</b> to start with stock Gene timing. Hold SHIFT and turn Gene Size just above fully CCW for <b>0.1 Genes/sec</b>, to noon for 8 or fully CW for 128. Fully CCW recalls stock timing. If already there, move slightly right and back while holding SHIFT. Unshifted Gene Size sets length. With dstr omitted, startup uses <b>1.0 Gene/sec</b> and settings-only reload keeps live timing. An explicit dstr recalls the saved timing. Knob edits last until power-off or another recall. External clock takes priority.'),('Gesture priority','Independent density takes priority over Turing’s SHIFT + Gene Size rate control. Set <b>dens 0</b> to use that Turing gesture again.'),('Morph Loop','<b>mlop 1</b> changes the bottom three Morph presets to the seamless-loop behavior normally reached near 8 o’clock. Higher overlap settings stay unchanged. <b>mlop 0</b> restores the original gaps. Settings can be applied at startup or by trusted-card reload.')],left=115,size=10.5,pad=6)
g.note('Morph Loop is included but <b>disabled by default</b>. With Morph Loop off, <b>mpos 10</b> (9-11%) selects the stock seamless-loop setting. <b>mpos 0</b> leaves a scheduling gap. These positions assume stock timing and an unpatched clock. Clock pulses and independent density change Gene spacing.')
g.finish()

g.start('Feedback and motion','Tape / effects / scatter / Turing','Hold SHIFT and turn a knob to perform. A plain SHIFT tap still advances the splice. Moving CV can be interpreted as knob movement while SHIFT is held.')
g.rows([('SHIFT + S.O.S.','In <b>dryk 0 or 1</b> with <b>tape 1</b>, a gesture or explicit <b>fbkp</b> recall activates feedback control. During overdub, a Varispeed tape head writes inside the Slide / Gene Size window; the gesture sets retained feedback. Plain S.O.S. controls the listening mix in mode 0. Mode 1 keeps the return wet only. <b>tape 0</b> selects classic TLA: input plus feedback-scaled Gene playback.'),('SHIFT + Morph','<b>fxsl 1</b>: sample-rate reduction; <b>fxsl 2</b>: tape wow/flutter; <b>fxsl 0</b>: disabled. Effects act on Gene playback, not the direct input. Optional <b>srrp</b>/<b>wrbp</b> recall separate amounts. Off bypasses both while retaining their levels.'),('SHIFT + Slide','Gene start jitter: fully left is off; turning right widens scatter. In Turing mode, scatter repeats with the stored random steps.'),('Turing setup','Set <b>sldm 1</b>. Start with short Genes and low Morph for a melody; higher Morph gives overlap. Stock chord ratios <b>mcr1-mcr3</b> supply pitch choices.'),('Turing controls','SHIFT + <b>Organize</b>: evolution, left locked / right fresh randomness. SHIFT + <b>Gene Size</b>: 1, 2, 3, 4, 6, 8, 12 or 16 Genes per step (dens must be off). SHIFT + <b>Slide</b>: spread. To make a new pattern, turn evolution fully right, then left.'),('Pattern options','<b>tlen</b> sets 1-16 steps, default 8. <b>root</b> sets root-pitch probability, default 50%; 100 means no chord-pitch changes.'),('Gain and mono','Hold REC and tap SHIFT for stock input gain changes; saved after about 3 seconds. <b>mono 1</b> always copies L to both channels; <b>mono 2</b> does so while R is quiet; <b>mono 0</b> stays stereo.')],left=110,size=10.4,leading=14.4,pad=5)
g.note('Tape overdub Morph cap: <b>mcap 3</b> limits Morph to 0.3 while dubbing. Higher values or no cap can glitch under heavy load. Try warble instead of SRR to reduce CPU use.')
g.finish()

g.start('Change settings live','Advanced / trusted matching cards','The dedicated reload preserves the live reel and playback continuity, leaving the card mounted for recording and saving. Included presets deliberately update their controls; an explicit splice recall changes selection.')
g.note('<b>No reel-content verification.</b> You must keep the same bank folders, reel names, WAV contents and splice sidecars on every copy. Same capacity or file size does not establish a match. A mismatch can cause incorrect saves or overwrite audio.')
g.section('Prepare and swap')
g.rows([('1 / Prepare copies','Copy the complete card. Change only options.txt on each copy. Preserve its first state line. Back up the source separately. Ordinary supported card formats still apply; equal capacities are not required.'),('2 / Remove idle card','Finish recording and wait for normal card writes to complete. Remove the card and wait for its mounted SHIFT light to go out. Do not record, edit splices or change reels while it is disconnected.'),('3 / Arm','Hold <b>SHIFT alone for one second</b>, until its LED is steady. No arming while a card is mounted. Moving a knob or pressing another button cancels arming.'),('4 / Insert','Keep SHIFT held and insert the prepared matching card. <b>Two short flashes</b>: success. <b>Three short flashes</b>: failure. Keep the card inserted through confirmation, then release SHIFT.'),('5 / Continue','After success, recording and saving use the newly mounted card. Any recording, splice edit, save or reel-list change can make other copies stale. Synchronize copies again before reusing them.')],left=108,size=10.5,pad=5)
g.section('Failure and normal mounting')
g.body('Missing or differently sized current-reel files, invalid recognized settings, card errors, offline edits or concurrent recording/card work can reject the reload. Failure keeps settings unchanged and leaves the card unmounted. Remove it and mount normally to recover. For an ordinary mount, insert the card and tap SHIFT. It can load the saved bank and reel with the usual brief interruption. A settings-only reload keeps the current bank.')
g.body('During idle playback the module also checks for card removal even when a cached reel still appears readable. Give SHIFT a few seconds to go dark after a pull. A new one-second hold can arm from the reel browser or after a previous settings-only swap. Card and SD load times vary.')
g.finish()

g.start('Presets: main controls','Introduced in mg204+c2 / all recalls optional','Check only the values you want in the browser editor. Explicit keys apply after startup/reel load and on settings-only reload; omitted keys keep their live values during reload.')
g.section('Percentages are virtual knob positions')
g.body('<b>0% is fully counterclockwise, 50% is noon, 100% is fully clockwise.</b> Whole percentages follow the existing control curves. They are not percentages of duration, speed or effect strength. Varispeed uses its calibrated range; physical pointer alignment may vary slightly.')
g.rows([('mpos / Morph','<b>0-100.</b> With Morph Loop off, <b>10%</b> selects the stock seamless-loop setting (9-11%); <b>0%</b> leaves a scheduling gap. Higher values add overlap and eventually pitch/pan variation. Clock and independent density can change spacing.'),('gpos / Gene Size','<b>0-100.</b> <b>0% and 1%</b> play the full splice, the longest Genes. Turning up shortens Genes; <b>100%</b> gives the shortest. This is nonlinear, not a percentage of splice length.'),('spos / Slide','<b>0-100.</b> Positions the Gene window from the beginning toward the end of the splice. Gene Size affects which portion is heard; this is not an absolute timestamp.'),('vpos / Varispeed','<b>0-100.</b> Position before vsop/vrng/vctr mapping. <b>50%</b> gives forward +1x with <b>vctr 1</b>; otherwise it depends on layout and quantization. Explicit vpos replaces an active unity hold; a later vuni gesture replaces the preset hold.'),('sosp / S.O.S.','<b>0-100.</b> Recalls the main knob on the selected <b>sosc</b> curve. In dryk 0 you also hear that mix at the outputs. See pages 12-13.'),('splc / Splice','<b>1-300.</b> Entering 0 recalls splice 1. Above the reel count selects the last splice while retaining the configured number: splc 300 is a useful last-splice preset. omod 0 switches at a normal boundary; omod 1 switches immediately.')],left=112,size=10.3,leading=14.2,pad=5)
g.note('Preset values are applied only when explicitly present. Missing or invalid optional keys are unchecked by the editor. On dedicated live reload, an invalid or duplicated recognized key rejects the whole transaction. Selecting a splice intentionally changes playback location; it does not load another reel.')
g.finish()

g.start('Presets: effects and pickup','Introduced in mg204+c2 / continue from the recalled value','Each key below is optional. Amounts use the existing SHIFT control curves, and the corresponding mode switch still determines which feature is active.')
g.rows([('srrp / SRR','<b>0-100.</b> 0% bypasses; increasing strengthens sample-rate reduction. Active with fxsl 1. Not a bit-depth or sample-rate percentage.'),('wrbp / Warble','<b>0-100.</b> 0% is no warble; higher values add wow/flutter. Active with fxsl 2. Separate amount from SRR; only the selected effect runs, and fxsl 0 bypasses both.'),('jitp / Jitter','<b>0-100.</b> 0% is no jitter; higher values widen start scatter. With sldm 1 this is repeating Turing spread.'),('fbkp / Feedback','<b>0-100.</b> In dryk 0/1 this activates SHIFT feedback. 0% retains none and 100% gives maximum retention. tape selects tape overdub or classic TLA.'),('evop / Evolution','<b>0-100.</b> 0% locks the Turing pattern; 100% gives fresh randomness. Intermediate values follow the nonlinear knob curve. Requires sldm 1.'),('trst / Genes per step','<b>1, 2, 3, 4, 6, 8, 12, 16.</b> Entering 0 recalls 1 Gene per step. With dens 1, SHIFT + Gene Size adjusts density.')],left=118,size=10.3,leading=14,pad=4)
g.section('Soft pickup, reload and saving')
g.body('A recalled main control holds until its combined knob/CV input comes near or crosses the preset position. Secondary effects use the same pickup idea during their matching <b>SHIFT + knob</b> gesture. The primary control stays at its effective value during that gesture. Organize picks up at the selected splice, and ordinary SHIFT navigation remains available.')
g.body('An explicit value recalls again even when identical to the previous file. Omitted keys preserve live values and pickup. Saves retain the <b>configured numbers, not later knob movements</b>; omitted preset keys remain omitted. No gesture captures the live knobs into options.txt.')
g.note('Density and input gain were already configurable with <b>dstr</b> and <b>ingn</b>. The module adds dstr back on a normal options rewrite. Uncheck its Recall box again when preparing an omission for live reload. The editors and module write <b>// firmware version 204+c7</b>. Keep the first numeric state line.')
g.finish()

g.start('Options: pitch and timing','Reference / file format','Use the browser editor to load the module’s options.txt, choose values and save it back to the card root. Keep the first line unchanged; it stores the module’s own state.')
g.body('Boot parsing retains defaults for invalid mod values. Dedicated live reload rejects the whole transaction for an invalid or duplicated recognized key. Omitting dstr on reload keeps the live timing. Omitting sosc selects its default crossfade. The editor normalizes editable duplicates and replaces invalid editable values with defaults; review its generated preview.')
g.rows([('vrng / 0','0 stock; 1 extended +/-4x in vsop 0/1, or forward stop-to-8x in vsop 2.'),('vqnt / 0','0 SHIFT-to-lock; 1 normally quantized with SHIFT + Varispeed temporarily continuous.'),('vuni / 0','1 enables SHIFT alone for at least 0.5 seconds, then release for exact forward +1x with pickup; see page 3.'),('vctr / 0','1 puts +1x at calibrated noon across layouts, ranges and scales. See ntch below for the optional flat zones.'),('ntch / omit','0 no added notch, 1 forward, 2 reverse, 3 both. Omit at boot to follow vctr and on live reload to keep the active choice. See page 3.'),('octl / 1','0 off; 1 octaves; 2 octaves + fifths; 3 semitones; 4 custom.'),('scal / 0','Custom semitones 1-11, separated by commas or spaces. 0 means no added intervals. Root and octaves remain.'),('dens / 0','0 off; 1 on. SHIFT + Gene Size fully CCW selects stock timing. Above it, adjust 0.1–128 Genes/sec. Knob changes are <b>not saved across power cycles</b>; startup uses dstr.'),('dstr / 1.0','<b>0</b> recalls stock Gene timing. <b>0.1-128.0</b> selects Genes/sec in 0.1 steps. On live reload, include the value to recall it or omit it to keep live timing. Sounding Genes finish. An existing <b>dstr 8.0</b> still recalls 8 Genes/sec.'),('mlop / 0','0 original Morph gaps; 1 seamless loop at minimum Morph. Included since the original mg204+c.'),('vsop / stock','0 classic bidirectional; 1 alternate bidirectional V/oct; 2 forward-only. See page 3 for tracking and modified-map limits.'),('gnsm / stock','Stock envelope: 0 original, 1 smooth. Preserve your existing preference.')],left=100,size=10.3,leading=14,pad=4)
g.note('Example: <b>vsop 2</b>, <b>vrng 1</b>, <b>vqnt 1</b>, <b>octl 3</b> gives forward 8x with normal semitone quantization. Add <b>mlop 1</b> if you also want the bottom of Morph to loop seamlessly.')
g.finish()

g.start('Options: sound and workflow','Reference / key followed by default','Feature switches and recalled control values are separate. Use these mode options with the optional presets on pages 7-8.')
g.rows([('dryk / 0','0 monitors the mix. 1–3 monitor Gene playback. 1 uses ordinary recording, 2 overdubs stored samples, 3 records the performed Genes.'),('sosc / 0','0 crossfade, both full at noon. 1 keeps incoming audio full. 2 keeps existing audio full. See page 12.'),('dlen / 0','0 fixed length. In dryk 2, use 1 for a growing replacement on the last splice when REC starts fully CCW with sosc 0 or 1.'),('tape / 1','0 classic TLA feedback; 1 tape mode selected for SHIFT + S.O.S.'),('fxsl / 1','0 off; 1 sample-rate reduction; 2 tape warble.'),('mcap / 3','0 no cap; 1-9 = Morph cap 0.1-0.9 while tape-dubbing.'),('sldm / 0','0 Turing mode off; 1 on.'),('root / 50','Turing root probability, 0-100 percent.'),('tlen / 8','Turing loop length, 1-16 steps. Entering 0 selects 1.'),('ingn / 0','Saved input gain index, 0-3; follows REC + SHIFT taps.'),('mono / 0','0 stereo; 1 always copy left to right; 2 copy left while right is quiet.'),('cpul / 0','0 logging off; 1 CPU troubleshooting log in cpulog.txt. Writes periodically; disable again after troubleshooting.')],left=100,size=10.3,leading=14,pad=4)
g.section('Entering zero')
g.body('Both editors label options Stock, Stock+ (extended) or Enhancement. Zero selects <b>1</b> for <b>tlen, splc, trst</b>. For <b>mcr1, mcr2, mcr3</b>, zero selects <b>+0.0625</b>, the slowest forward ratio. A negative ratio from -0.0625 to -16 plays in reverse. To skip a preset recall, uncheck Recall or omit its line.')
g.note('Drop the card’s <b>options.txt</b> into either editor or choose the file. Check Recall to include an optional preset. <b>Reset to defaults</b> asks for confirmation. Download the edited file to replace the card copy. Save the standalone HTML from the patcher to edit offline.')
g.finish()

g.start('Testing, limits and credits','Read before performance use','Hardware checks covered bank selection, audition, play-through, unity notches, card reload and overdubbing. Timing depends on the card and patch.')
g.section('Version by version')
g.rows([('mg204+c7','Reel banks, splice audition and performance switching, directional play-through, forward/reverse unity notches and more reliable card removal.'),
        ('mg204+c6','Recall stock Gene timing with dstr 0. Startup defaults to 1.0 Gene/sec. Zero selects 1 for counts and +0.0625 for chord ratios.'),
        ('mg204+c5','Wet-only performance recording, three S.O.S. curves, stock timing at minimum density and card removal after erasing the last splice.'),
        ('mg204+c4','Wet-only returns, S.O.S. overdub feedback, fixed or growing takes, and downloadable offline settings editor.'),
        ('mg204+c3','Fixes Varispeed reverting to forward only. Restore a previously overwritten vsop once.'),
        ('mg204+c2','SHIFT return to +1x, unity at noon, optional control and splice recalls with pickup.'),
        ('mg204+c','Extended Varispeed, quantization, independent density, Morph Loop and live options reload.')],left=74,size=10.2,leading=13,pad=2)
g.body('For performance, allow CPU headroom when combining dense Genes, Morph, overdubs and SRR. Use the tape Morph cap or reduce density. Back up matching cards and synchronize after edits. Use at your own risk.')
g.section('Credits and license')
g.body('<b>Copyright (c) 2026 vwal</b> for our original additions. Briskcat created the upstream mods and patcher. '+link('https://github.com/carlosedp/morphagene-mods','Carlos de Paula’s fork')+' contributed bank and splice play-through work and inspired the reverse notch. Upstream MIT portions are <b>(c) 2026 the morphagene-mods contributors</b>. Audio encoding follows Emilie Gillet’s '+link('https://github.com/pichenettes/stm-audio-bootloader','stm-audio-bootloader')+'.')
g.body('<b>Attribution - No Sale License 1.0:</b> free use, modification and sharing with notices retained. No sales, paid bundles, paid products containing our additions or paid firmware services without separate permission. Paid music-making, recordings and performances are allowed. Upstream MIT rights remain unchanged.')
g.body('<b>Make Noise exception:</b> Make Noise may integrate and commercially distribute our additions in official firmware and products, with notices retained. This exception does not permit general third-party sales or imply endorsement.')
g.note('Include the attached <b>LICENSE.txt</b> with copies. Make Noise retains its firmware rights. This project contains carefully tested AI-generated code. Independent customization. Not an official Make Noise release.')
g.finish()

g.start('What goes on the reel?', 'Overdubbing / signal routing',
        'The first take on an empty reel always captures full live input from REC start to stop. '
        'On subsequent takes, dryk selects the recording and monitoring paths. The main S.O.S. knob sets the balance.')
g.section('Choose the recording path')
g.rows([
    ('dryk 0', 'Hear incoming audio and Gene playback at the selected balance. Ordinary recording with <b>inop 0</b> writes that mix. Choose <b>inop 1</b> to record input alone.'),
    ('dryk 1', 'Hear only Gene playback. Recording follows the same controls as mode 0, including inop.'),
    ('dryk 2', 'Hear only Gene playback. A fixed overdub mixes input with samples under the Varispeed tape head. Slide and Gene Size choose the write window. A new splice has no stored samples at its destination.'),
    ('dryk 3', 'Hear only Gene playback. Record real-time stereo input mixed with performed Genes, including their Varispeed, Morph, Gene Size and Slide changes. A new splice keeps the source. On a current-splice overdub, the heads can play newly written sound before the loop ends.'),
], left=76, size=10.5, leading=14, pad=4)
g.section('Set the main S.O.S. curve')
g.body('Pairs below give <b>incoming / existing</b> audio, in order from fully CCW through noon to fully CW. In modes 0, 1 and 3 the existing source is Gene playback during an ordinary mix. Mode 2 uses stored samples.')
g.rows([
    ('sosc 0 · Crossfade', 'Full / off  →  full / full  →  off / full. Default when omitted, including on settings-only reload.'),
    ('sosc 1 · Full input', 'Full / off  →  full / half  →  full / full. Use this with dryk 2 for the full-input overdub from c4.'),
    ('sosc 2 · Full existing', 'Full / full  →  half / full  →  off / full. Turn clockwise to reduce incoming audio.'),
], left=137, size=10.5, leading=14, pad=4)
g.note('In <b>dryk 0/1</b>, SHIFT + S.O.S. or an explicit <b>fbkp</b> activates the separate tape or classic TLA recording path (page 5). Normal monitoring still follows the main curve in mode 0. Modes 2 and 3 use the main curve independently of <b>inop</b> and SHIFT feedback.')
g.finish()

g.start('Three ways to record a loop', 'Overdubbing / patch examples',
        'With rsop 0, tap REC to overdub the current splice. To give a take its own splice and length, hold REC and press SPLICE. Tap REC again to finish.')
g.section('1   Hear a whole phrase, then overlap the Genes')
g.body('Start at forward +1x with Slide and Gene Size fully CCW, Morph near 9 o’clock and clock unpatched. '
       'Set <b>dens 1, dstr 0</b>. The phrase plays with stock timing, including after reboot. '
       'Hold SHIFT and turn Gene Size just above fully CCW to launch every ten seconds. A 15-second phrase can now overlap itself. '
       'To restore stock timing in performance, reload <b>dstr 0</b> or turn the shifted knob fully CCW. Allow sounding Genes to finish. The unshifted knob still sets length.')
g.section('2   Record a vocal over a moving texture')
g.body('Use <b>dryk 3, sosc 1</b>. Start with S.O.S. near noon for full incoming vocal and roughly half-level Gene playback. '
       'Record into a new splice while slowing Varispeed or sweeping Slide on the source. '
       'Play the new splice at +1x with whole-phrase settings. The vocal keeps its original timing and the texture retains your gestures. '
       'For successive, destructive passes, overdub the current splice instead. Material written on an earlier pass can feed back through the Gene controls.')
g.section('3   Fade layers and keep a beat loop in time')
g.body('Use <b>dryk 2, sosc 1, dlen 0</b>. Turn S.O.S. fully CCW to replace samples, to noon to keep about half of the old layer on each pass, or fully CW to retain it at full level. '
       'Incoming audio stays full in all three positions. For a full-splice pass use forward +1x with Slide and Gene Size fully CCW. Shorter Genes confine writes to the selected window.')
g.note('<b>For a longer pad</b>, set <b>dryk 2, dlen 1</b> with <b>sosc 0 or 1</b>. Start REC fully CCW on the last or only splice. A 15-second take over ten seconds records all 15 seconds forward at +1x. A shorter take keeps the old tail. With sosc 2, existing audio is always full and the overdub keeps its fixed window.')
g.finish()

g.start('Choose a bank, reel and splice', 'Reel banks / card setup and panel gestures',
        'Each bank holds up to 32 reels. Enable banks on a normal card mount, then use the same Organize knob to choose a bank, a reel and a splice.')
g.section('Prepare the card')
g.body('<b>bank 0</b> (or omitted) uses the card root and ordinary reel browser. '
       '<b>bank 1</b> enables the long picker and starts at the root. <b>bank 2-8</b> starts in the corresponding folder. '
       'Create <b>bank2</b> through <b>bank8</b> at the root as needed. Existing folders appear even when empty. '
       'Keep each reel WAV and its matching splice text file, if present, in the same folder. Leave <b>options.txt</b> and <b>mgmod.bin</b> at the root.')
g.section('Choose a recorded splice')
g.rows([
    ('Open the picker', 'With the card mounted and recording stopped, hold <b>SPLICE first</b>, add <b>REC</b>, and hold both for about three seconds until <b>REEL blinks</b>. Release both.'),
    ('1 / Bank', 'Turn Organize to the bank. To confirm at each step, hold SPLICE, tap REC and release both buttons.'),
    ('2 / Reel', 'Turn Organize to a recorded reel and confirm. A single recorded reel double-flashes. The far clockwise end is reserved for New Reel when space is available.'),
    ('3 / Splice', 'Choose and confirm the splice. If the reel contains just one splice, the entire dial selects it. Recording and saving then use the selected reel in its bank. Tap SHIFT before the switch to cancel.'),
], left=100, size=10.5, leading=14, pad=5)
g.section('Start a new recording')
g.body('At the <b>reel</b> step, turn into the last 5% clockwise for the pink/white <b>New Reel</b>. In an empty bank it occupies the whole dial. '
       'Confirm to open a blank immediately, then press REC for the first take. New splices stay in that reel. A bank with 32 recorded reels has no New Reel slot.')
g.note('<b>Quick route within the current bank.</b> Use the short SPLICE-then-REC chord to open the ordinary reel browser. Turn Organize fully clockwise for New Reel and confirm with a second short chord. This browser also works with bank 0.')
g.finish()

g.start('Audition and play through', 'Performance / preview, switch and sequence',
        'The long picker lets you search by ear or prepare a change while the current sound plays. Outside the picker, Organize can step through the splices of one reel.')
g.section('Choose what you hear in the picker')
g.rows([
    ('audt 0 / audition', 'The bank step keeps the current performance audible. At the reel step, pause on a reel to hear its first splice. At the splice step, pause on a splice to hear it loop forward at +1x. The preview begins after about 120 ms plus card read time.'),
    ('audt 1 / perform', 'The current performance stays audible at its live Varispeed, Morph and Gene settings through all three steps. The short reel browser still auditions.'),
    ('Cancel or confirm', 'Audition only changes what you hear. Tap <b>SHIFT</b> to return to the original reel where it has advanced. Confirm with <b>SPLICE then REC</b> to take the selection. Omitting audt enables previews on boot and on settings-only reload.'),
], left=116, size=10.5, leading=14, pad=5)
g.body('With <b>omod 0</b> the preview ends on confirmation and the switch waits for the current Gene transition. A queued change to a different reel shows its REEL color and a blinking SPLICE. '
       'With <b>omod 1</b> the switch starts immediately. Changing reels or banks includes the time to load from SD. New Reel always opens on confirmation.')
g.section('Step through a reel with Organize')
g.rows([
    ('thru 0 / manual', 'The full knob range selects splices. This is the default on an ordinary mount.'),
    ('thru 1 / advance', 'Turn into the top 5% clockwise to step forward through splice numbers and wrap from last to first, even if the sound plays backward. Below the zone, all splices remain selectable.'),
    ('thru 2 / follow', 'The same zone steps forward during forward playback and back during reverse playback, wrapping at either end. At stop there is no advance. Omitting thru on live reload keeps the active setting.'),
], left=116, size=10.5, leading=14, pad=4)
g.note('<b>Try whole phrases.</b> Use a reel with at least two splices, full-length Gene Size, Slide fully CCW, Morph near 9 o’clock, stock timing (dens 0 or dstr 0) and no external clock. Shorter or clocked Genes follow Gene boundaries. Automatic stepping pauses during recording.')
g.finish();g.c.save()

g=Guide(args.card,card=True)
g.start('Quick reference','Morphagene extended / mg204+c7','Settings are in the card’s options.txt. Page numbers refer to the full guide.')
g.rows([
('Banks / 14','<b>bank 0</b> is the ordinary reel browser. <b>bank 1</b> enables banks from the root. Add bank2-bank8 folders as needed, up to 32 reels per bank.'),
('Picker / 14-15','Hold <b>SPLICE first</b>, add <b>REC</b> for ~3 s until REEL blinks. Release both. Turn Organize to bank, reel, then splice. Confirm each with a short SPLICE-then-REC chord. SHIFT cancels. Pink/white at the reel step = New Reel.'),
('Audition / 15','<b>audt 0</b> (default) previews first splice of reel, then highlighted splice, at +1x. <b>1</b> keeps current audio audible. Confirm with <b>omod 0</b> for the Gene boundary or <b>1</b> for immediate switch. Switching reels takes SD load time.'),
('Play-through / 15','<b>thru 0</b> manual. In the top 5% of Organize, <b>1</b> steps through splice numbers forward, <b>2</b> follows Varispeed direction. Wraps at the ends.'),
('Return to 1:1 / 3','<b>vuni 1</b> hold SHIFT alone ≥0.5 s, release for +1x, then pick up with knob/CV. Unpatch SHIFT. <b>vctr 1</b> centers +1x. <b>ntch 0/1/2/3</b> gives no notch / forward / reverse / both. Omit ntch at boot to follow vctr.'),
('Pitch / 3-4','<b>vsop 0/1/2</b> classic bidirectional / bidirectional V/oct / forward. <b>vrng 1</b> extends to +/-4x or forward 8x. <b>vqnt 0/1</b> SHIFT lock / normally quantized. <b>octl 1-4</b> octaves / with fifths / semitones / custom.'),
('Density / loops / 4','<b>dens 1, dstr 0</b> recalls stock timing. SHIFT + Gene Size selects stock at fully CCW, then 0.1-128 Genes/sec (8 at noon). Unshifted knob sets length. Omit dstr for 1.0 at boot or to keep live timing on reload. Clock takes priority. <b>mlop 1</b> loops at minimum Morph.'),
('Recording / 12-13','<b>dryk 0</b> monitors the mix. <b>1-3</b> monitor Genes only. Modes 0/1 use ordinary recording and inop, 2 overdubs stored audio, 3 records input with performed Genes. First take on an empty reel captures full input.'),
('S.O.S. / length / 12-13','<b>sosc 0</b> crossfade, both full at noon. <b>1</b> full input, turn CW to add existing audio. <b>2</b> full existing, turn CW to reduce input. For c4 overdubs use dryk 2, sosc 1. In dryk 2, <b>dlen 0</b> fixes length. With dlen 1 and sosc 0/1, start REC fully CCW on the last splice to grow it.'),
('Presets / 7-8','Recall <b>mpos, gpos, spos, vpos, sosp</b> as knob positions, CCW/noon/CW = 0/50/100%. gpos 0-1% spans the splice. <b>splc</b> selects a splice, capped at the last. Zero for splc, trst or tlen selects 1. A zero chord ratio selects +0.0625. Uncheck Recall to omit. Cross a recalled value for pickup.'),
('Effects / Turing / 5, 8','SHIFT + Morph = SRR/warble (srrp/wrbp), Slide = jitter (jitp), S.O.S. = tape/TLA (fbkp, dryk 0/1). With <b>sldm 1</b>, SHIFT + Organize = evolution (evop), Gene Size = Genes/step (trst, dens off), Slide = spread. tlen sets steps, root the root chance.'),
('Live cards / 6','Wait for writes, remove card, wait for dark SHIFT. Hold SHIFT alone 1 s until steady. Insert matching card while held. Two flashes = success, three = failure. Match all bank paths, reels and markers.'),
('Install / editor / 2, 10','First install by WAV via Left Signal IN. Later boot with <b>mgmod.bin</b> at root. Success renames it <b>mgmod.ok</b>. Both editors and the module write <b>204+c7</b>.')
],left=105,size=9.4,leading=12.1,pad=3)
g.note('<b>(c) 2026 vwal.</b> Built on Briskcat’s mods and Carlos de Paula’s fork (MIT). Free use with notices. No sales, paid bundles/products/services except Make Noise official integration. Full terms in LICENSE.txt. Carefully tested AI-generated code. Independent customization. Not an official Make Noise release. <b>vwal.github.io/morphagene-patcher/</b>')
g.finish();g.c.save()

# Preserve full license terms in independently shared PDFs without adding pages.
from pypdf import PdfReader, PdfWriter
from pypdf.generic import TextStringObject
license_bytes=(Path(__file__).resolve().parents[1]/'LICENSE').read_bytes()
for target in (args.output,args.card):
    reader=PdfReader(target)
    writer=PdfWriter()
    writer.clone_document_from_reader(reader)
    attachment=writer.add_attachment('LICENSE.txt',license_bytes)
    attachment.description=TextStringObject('Complete Morphagene Extended Attribution - No Sale License, Make Noise exception, and upstream MIT notice')
    temp=target.with_suffix('.licensed.pdf')
    with temp.open('wb') as stream:writer.write(stream)
    temp.replace(target)
