#!/usr/bin/env python3
"""Build the printable references for Morphagene mg204+c."""
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
os.environ.setdefault('SOURCE_DATE_EPOCH', str(int(datetime(2026,11,11,tzinfo=timezone.utc).timestamp())))
for name, file in [('Guide','Regular'),('GuideB','Bold')]:
    pdfmetrics.registerFont(TTFont(name,str(args.font_dir/f'LiberationSans-{file}.ttf')))
pdfmetrics.registerFontFamily('Guide',normal='Guide',bold='GuideB',italic='Guide',boldItalic='GuideB')
ink,green,muted,rust,rule,pale = [colors.HexColor(c) for c in
    ('#20322c','#285843','#45594f','#91431f','#cdd8cf','#eaf2eb')]
SITE='https://briskcat.github.io/morphagene-mods/'
MANUAL='https://www.makenoisemusic.com/modules/morphagene/'
def link(url,label):
    return '<link href="%s" color="#285843"><u>%s</u></link>'%(url,label)
class Guide:
    def __init__(self,path,card=False):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.c=canvas.Canvas(str(path),pagesize=paper,pageCompression=1,invariant=1)
        self.c.setCreator('vwal | Morphagene firmware reference');self.c.setAuthor('vwal');self.c.setTitle('Morphagene mg204+c | '+('Quick reference card' if card else 'Firmware reference guide')+' | '+paper_name+' | Extended firmware'+(' | DRAFT' if args.draft else ''))
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
        c.setFillColor(green);c.roundRect(right-86,743,86,20,5,fill=1,stroke=0)
        self.text('mg204+c',right-65,749,10,'GuideB',colors.white)
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
        c.setFont('Guide',9);c.setFillColor(muted);c.drawRightString(right,26,paper_name+'    |    '+('1 / 1' if self.card else f'{self.n} / 8'))
        c.showPage()


g=Guide(args.output)
g.start('Play beyond stock','Morphagene extended firmware / mg204+c','Reference manual for the extended mg204 build. Unofficial community firmware built on Briskcat’s Morphagene mods.')
g.section('One build, selectable features')
g.body('The <b>mg204+c</b> build includes every feature, including Morph Loop. Start with the defaults, then enable the options you want. <b>mlop 0</b> keeps the original Morph gaps; <b>mlop 1</b> enables seamless looping at minimum Morph. No separate firmware is needed.')
g.rows([('Pitch and timing / 3','Expanded Varispeed up to +/-4x or forward 8x; scale locking or normal quantization; independent 0.1-128 Genes/sec density; switchable Morph Loop.'),('Sound and motion / 4','Tape or classic TLA feedback, sample-rate reduction, tape warble, jitter and repeating Turing patterns.'),('Live settings / 5','Trusted-card options reload preserves the reel and playback position and leaves the card mounted. Matching card contents are your responsibility.'),('Options / 6-7','Edit options.txt using the browser editor or a plain-text editor. Keep the first state line unchanged. Missing keys during live reload retain their current values.'),('Install / 2; testing / 8','First installation and recovery use an audio WAV. Later updates can use mgmod.bin on SD. See page 8 for validation and performance limits.')])
g.note('<b>Defaults:</b> extended range, independent density, normal quantization, Turing mode and Morph Loop are all off. Tape mode and SRR are selected but their performance gestures activate/control them.')
g.finish()

g.start('Install and recover','Audio first / SD thereafter','Back up the entire SD card before installing. Keep your original Make Noise update WAV for recovery.')
g.section('Build from official mg204.wav')
g.body('On '+link('https://vwal.github.io/morphagene-patcher/','the mg204+c patcher')+', choose the original <b>mg204.wav</b> downloaded from Make Noise. The builder verifies its contents, applies the extended patch and verifies the result. Download <b>mg204+c.wav</b> for a first install, or <b>mgmod.bin</b> for later SD updates. Processing stays in your browser.')
g.section('First installation by audio')
g.rows([('1 / Prepare','Remove the SD card. Connect the player to <b>Left Signal IN</b>, starting at about 80% volume. Disable effects, EQ, sound enhancements and notifications.'),('2 / Bootloader','Power on holding <b>REC</b>. Only the SPLICE window lights green. Release REC.'),('3 / Play the WAV','Play the generated update WAV without interruption. Windows flash during loading; all lights flash on completion. Keep power stable.'),('4 / Calibrate','Follow Make Noise’s update instructions: power on holding <b>SPLICE</b>, turn Varispeed fully both ways, press SPLICE, then power-cycle.')],left=100,pad=5)
g.section('Later SD updates and stock recovery')
g.body('Place <b>mgmod.bin</b> in the card root and power on. The installed SD updater handles it automatically; successful installation renames it <b>mgmod.ok</b>. For stock recovery, use the audio procedure with the original official <b>mg204.wav</b>. The mods do not replace the bootloader.')
g.body('If audio loading fails, adjust player level and retry with an unprocessed playback path. If SD updating does not start, verify the exact filename and that the SD updater was installed previously.')
g.note('Installation procedure follows '+link(SITE,'Briskcat’s upstream guide')+' and '+link(MANUAL,'Make Noise’s official instructions')+'. Generated firmware contains Make Noise code; keep it for personal use.')
g.finish()

g.start('Pitch, density and loops','Varispeed / Gene timing / Morph','A SHIFT gesture consumes that hold: releasing it does not advance the splice. After a gesture, most knobs use pickup at their previous position.')
g.rows([('Expanded range','<b>vrng 1</b>: stock vsop 0/1 layouts extend to +/-4x; <b>vsop 2</b> gives forward-only stop to 8x. <b>vrng 0</b> retains stock ranges.'),('SHIFT-to-lock','<b>vqnt 0</b> (default): SHIFT + Varispeed locks to the selected scale. The lock stays after release; turn about half an octave away to release it.'),('Quantize normally','<b>vqnt 1</b>: normal Varispeed is quantized. SHIFT + Varispeed temporarily adjusts continuously; release snaps back. Other SHIFT gestures keep pitch quantized. <b>octl 0</b> disables quantization in either mode.'),('Choose a scale','<b>octl 1</b> octaves; <b>2</b> octaves and fifths; <b>3</b> semitones; <b>4</b> custom. For custom, use <b>scal 3,5,7,10</b> for minor pentatonic, for example. Root and octaves are always included.'),('Independent density','With <b>dens 1</b>, startup density comes from <b>dstr</b>, default <b>8 Genes/sec</b>. Hold SHIFT and turn Gene Size to adjust it from <b>0.1 to 128 Genes/sec</b>, independently of pitch and Morph. Knob changes remain until adjusted again, recalled by dstr reload or powered off; <b>they are not saved across power cycles</b>. Settings-only reload recalls an explicit <b>dstr</b>; omit it to preserve the live rate. The knob midpoint remains 8/sec; 0.1 requests one Gene every ten seconds. External clock takes priority. Available voices limit dense, long Genes; births may be deferred.'),('Gesture priority','Independent density takes priority over Turing’s SHIFT + Gene Size rate control. Set <b>dens 0</b> to use that Turing gesture again.'),('Morph Loop','<b>mlop 1</b> changes the bottom three Morph presets to the seamless-loop behavior normally reached near 8 o’clock. Higher overlap settings stay unchanged. <b>mlop 0</b> restores the original gaps. Settings can be applied at startup or by trusted-card reload.')],left=115,size=10.5,pad=6)
g.note('Morph Loop is included but <b>disabled by default</b>. Switching it changes scheduling for subsequent processing; a gap-free transition, especially with clock or recording, still needs hardware validation.')
g.finish()

g.start('Feedback and motion','Tape / effects / scatter / Turing','Hold SHIFT and turn a knob to perform. A plain SHIFT tap still advances the splice. Moving CV can be interpreted as knob movement while SHIFT is held.')
g.rows([('SHIFT + S.O.S.','<b>tape 1</b>: first gesture after startup activates tape mode. During overdub, a Varispeed tape head writes inside the Slide / Gene Size window; the gesture sets retained feedback. Plain S.O.S. controls the listening mix. <b>tape 0</b> selects classic TLA: input plus feedback-scaled Gene playback.'),('SHIFT + Morph','<b>fxsl 1</b>: sample-rate reduction; <b>fxsl 2</b>: tape wow/flutter; <b>fxsl 0</b>: disabled. Effects act on Gene playback, not the direct input. Amount resets at power-up.'),('SHIFT + Slide','Gene start jitter: fully left is off; turning right widens scatter. In Turing mode, scatter repeats with the stored random steps.'),('Turing setup','Set <b>sldm 1</b>. Start with short Genes and low Morph for a melody; higher Morph gives overlap. Stock chord ratios <b>mcr1-mcr3</b> supply pitch choices.'),('Turing controls','SHIFT + <b>Organize</b>: evolution, left locked / right fresh randomness. SHIFT + <b>Gene Size</b>: 1, 2, 3, 4, 6, 8, 12 or 16 Genes per step (dens must be off). SHIFT + <b>Slide</b>: spread. To make a new pattern, turn evolution fully right, then left.'),('Pattern options','<b>tlen</b> sets 1-16 steps, default 8. <b>root</b> sets root-pitch probability, default 50%; 100 means no chord-pitch changes.'),('Gain and mono','Hold REC and tap SHIFT for stock input gain changes; saved after about 3 seconds. <b>mono 1</b> always copies L to both channels; <b>mono 2</b> does so while R is quiet; <b>mono 0</b> stays stereo.')],left=110,size=10.4,leading=14.4,pad=5)
g.note('Tape overdub Morph cap: <b>mcap 3</b> limits Morph to 0.3 while dubbing. Higher values or no cap can glitch under heavy load. Try warble instead of SRR to reduce CPU use.')
g.finish()

g.start('Change settings live','Advanced / trusted matching cards','The dedicated reload preserves the current reel, splice selection and playback position. Successful reload leaves the card mounted for subsequent recording and saving.')
g.note('<b>No reel-content verification.</b> You must keep WAV contents, splice sidecars and the complete reel-name inventory identical across cards. Same capacity or file size does not establish a match. A mismatch can cause incorrect saves or overwrite audio.')
g.section('Prepare and swap')
g.rows([('1 / Prepare copies','Copy the complete card. Change only options.txt on each copy. Preserve its first state line. Back up the source separately. Ordinary supported card formats still apply; equal capacities are not required.'),('2 / Remove idle card','Finish recording and wait for normal card writes to complete. Remove the card and wait for its mounted SHIFT light to go out. Do not record, edit splices or change reels while it is disconnected.'),('3 / Arm','Hold <b>SHIFT alone for one second</b>, until its LED is steady. No arming while a card is mounted. Moving a knob or pressing another button cancels arming.'),('4 / Insert','Keep SHIFT held and insert the prepared matching card. <b>Two short flashes</b>: success. <b>Three short flashes</b>: failure. Keep the card inserted through confirmation, then release SHIFT.'),('5 / Continue','After success, recording and saving use the newly mounted card. Any recording, splice edit, save or reel-list change can make other copies stale. Synchronize copies again before reusing them.')],left=108,size=10.5,pad=5)
g.section('Failure and normal mounting')
g.body('Missing or differently sized current-reel files, invalid recognized settings, card errors, offline edits or concurrent recording/card work can reject the reload. Failure keeps settings unchanged and leaves the card unmounted. Remove it and mount normally to recover. Use normal mounting, without the armed gesture, to load another reel; its usual playback interruption remains.')
g.body('No full-reel hash or background scan runs. Mounting, reading options and reopening/seeking the reel still require SD access. Hardware testing confirmed changed options applying without an audible playback interruption. Exact latency and all performance combinations remain unmeasured.')
g.finish()

g.start('Options: pitch and timing','Reference / file format','Use the browser editor to load the module’s options.txt, choose values and save it back to the card root. Keep the first line unchanged; it stores the module’s own state.')
g.body('Boot parsing retains defaults for invalid mod values. Dedicated live reload rejects the whole transaction for an invalid or duplicated recognized key. Missing keys during reload keep their live values. The editor normalizes editable duplicates and replaces invalid editable values with defaults; review its generated preview.')
g.rows([('vrng / 0','0 stock; 1 extended +/-4x in vsop 0/1, or forward stop-to-8x in vsop 2.'),('vqnt / 0','0 SHIFT-to-lock; 1 normally quantized with SHIFT + Varispeed temporarily continuous.'),('octl / 1','0 off; 1 octaves; 2 octaves + fifths; 3 semitones; 4 custom.'),('scal / 0','Custom semitones 1-11, separated by commas or spaces. 0 means no added intervals. Root and octaves remain.'),('dens / 0','0 off; 1 on. SHIFT + turning Gene Size adjusts 0.1-128 Genes/sec. Knob changes are <b>not saved across power cycles</b>; startup uses dstr.'),('dstr / 8','Startup/reload density: <b>0.1-128 Genes/sec</b>, in 0.1 steps. Explicit dstr recalls on settings-only reload, even if unchanged; omit to keep the live rate. Existing Genes finish; the next unclocked Gene waits one new interval. Stored in options.txt.'),('mlop / 0','0 original Morph gaps; 1 seamless loop at minimum Morph. Included in mg204+c.'),('vsop / stock','Stock layout 0/1 bidirectional, 2 forward-only. The editor exposes this because it selects the extended 8x layout.'),('gnsm / stock','Stock envelope: 0 original, 1 smooth. Preserve your existing preference.')],left=100,pad=7)
g.note('Example: <b>vsop 2</b>, <b>vrng 1</b>, <b>vqnt 1</b>, <b>octl 3</b> gives forward 8x with normal semitone quantization. Add <b>mlop 1</b> if you also want the bottom of Morph to loop seamlessly.')
g.finish()

g.start('Options: sound and workflow','Reference / key followed by default','Gesture amounts such as feedback, jitter and effects are separate from their options switches. They are not all persisted by options.txt.')
g.rows([('tape / 1','0 classic TLA feedback; 1 tape mode selected for SHIFT + S.O.S.'),('fxsl / 1','0 off; 1 sample-rate reduction; 2 tape warble.'),('mcap / 3','0 no cap; 1-9 = Morph cap 0.1-0.9 while tape-dubbing.'),('sldm / 0','0 Turing mode off; 1 on.'),('root / 50','Turing root probability, 0-100 percent.'),('tlen / 8','Turing loop length, 1-16 steps.'),('ingn / 0','Saved input gain index, 0-3; follows REC + SHIFT taps.'),('mono / 0','0 stereo; 1 always copy left to right; 2 copy left while right is quiet.'),('cpul / 0','0 logging off; 1 CPU troubleshooting log in cpulog.txt. Writes periodically; disable again after troubleshooting.')],left=100,size=10.5,pad=5)
g.section('Other stock settings')
g.body('The editor preserves other stock lines, including <b>pmod, omod, cvop, ckop, rsop, pmin, inop</b> and chord ratios <b>mcr1-mcr3</b>. Their meanings remain those in Make Noise’s manual. Dedicated reload accepts these keys too. Chord ratios must have magnitude 0.0625-16, with a sign selecting direction; use ordinary decimal notation.')
g.note('When no options file is loaded, the editor produces a <b>snippet</b>, not a complete card file. Add mod lines to the existing file and replace existing vsop/gnsm lines. Do not duplicate keys or remove the first state line.')
g.finish()

g.start('Testing, limits and credits','Read before performance use','Hardware testing confirmed armed insertion and changed options without an audible playback interruption. Exact latency and all performance combinations remain unmeasured.')
g.section('Performance checks')
g.body('Audition both <b>mlop 0</b> and <b>mlop 1</b>, then switch between them with trusted-card reload. Check short and long Genes, reverse and forward ranges, both Gene envelopes, external clock, recording and overdubbing. Confirm two success flashes, continued playback and a usable mounted card after each swap.')
g.body('Try your densest performance patch. Stock audio can already approach CPU limits at high Morph with short Genes. Independent density, overdubbing and SRR can add pressure. Reduce density/overlap, retain the tape Morph cap or choose warble when necessary. Clocked Morph Loop transitions and heavy overdubbing need further hardware audition.')
g.section('What remains your responsibility')
g.body('Trusted-card reload checks basic file/state conditions but does <b>not</b> compare audio, splice metadata or reel inventory. Re-copy changed reels and sidecars after saving, recording or editing. If copies are uncertain, mount normally to load the card’s reel. Keep a separate backup.')
g.section('Credits and license')
g.body('<b>Copyright (c) 2026 vwal</b> for our original additions. Upstream: <b>Copyright (c) 2026 the morphagene-mods contributors</b>, under MIT. Briskcat created the upstream mods, patcher and fixed Morph Loop edits. Audio encoding follows Emilie Gillet’s '+link('https://github.com/pichenettes/stm-audio-bootloader','stm-audio-bootloader')+'.')
g.body('<b>Attribution - No Sale License 1.0:</b> free use, modification and sharing with notices retained. No sales, paid bundles, paid products containing our additions or paid firmware services without separate permission. Paid music-making, recordings and performances are allowed. Upstream MIT rights remain unchanged.')
g.body('<b>Make Noise exception:</b> Make Noise may integrate and commercially distribute our additions in official firmware and products, with notices retained. Authorized integration/distribution and resale of those official products are covered. This does not permit general third-party sales of the community release or imply endorsement.')
g.note('Full terms and upstream MIT notice are embedded as <b>LICENSE.txt</b> in this PDF. Keep the attachment when sharing; retain notices and include the full terms with print copies. No rights in Make Noise firmware are granted. Recovery: original mg204.wav via the audio procedure on page 2.')
g.finish();g.c.save()

g=Guide(args.card,card=True)
g.start('Quick reference','Morphagene extended / mg204+c','One mg204+c build. Morph Loop is included, off by default. Manual page numbers below.')
g.rows([('Pitch / p. 3','<b>vrng 1</b>: +/-4x; with <b>vsop 2</b>: stop to forward 8x. <b>octl 1/2/3/4</b>: octaves / fifths / semitones / custom scal.'),('Quantization','<b>vqnt 0</b>: SHIFT + Varispeed locks. <b>vqnt 1</b>: normally quantized; SHIFT + Varispeed frees it temporarily; release snaps back.'),('Density / loop','<b>dens 1</b>: startup rate from <b>dstr</b>, default <b>8 Genes/sec</b>. Set dstr to <b>0.1-128</b> in 0.1 steps. SHIFT + Gene Size adjusts 0.1-128/sec; <b>knob changes are not saved across power cycles</b>. Reload recalls explicit <b>dstr</b>; omit to keep the live rate. External clock takes priority. <b>mlop 1</b>: seamless minimum Morph; <b>0</b>: stock gaps.'),('Feedback / p. 4','SHIFT + S.O.S.: <b>tape 1</b> tape mode / <b>0</b> classic TLA. <b>mcap 3</b> caps Morph at 0.3 during tape dubbing.'),('Effects / scatter','SHIFT + Morph: <b>fxsl 1</b> SRR / <b>2</b> warble / <b>0</b> off. SHIFT + Slide: start jitter, left off.'),('Turing / p. 4','<b>sldm 1</b>: SHIFT + Organize = evolution, left locked; SHIFT + Gene Size = Genes/step if dens is off; SHIFT + Slide = repeating scatter. <b>tlen</b> steps; <b>root</b> root chance.'),('Live options / p. 5','Finish card writes; remove card; wait for SHIFT light to go out. Hold <b>SHIFT alone 1 s</b> (steady LED); insert matching card while held. <b>2 flashes</b> success, mounted; <b>3</b> failure, unmounted. Release SHIFT. Cannot arm while mounted.'),('Trusted cards','<b>No content verification.</b> Identical WAVs, splice files and reel names; only options.txt differs. No offline recording/editing. Saves make other copies stale: synchronize again. Normal mount loads another reel.'),('Gain / mono','REC held + SHIFT taps: input gain, saved after ~3 s. <b>mono 0</b> stereo / <b>1</b> copy L / <b>2</b> auto while R quiet.'),('Install / recover','First install: generated WAV into Left IN, power on holding REC. Follow calibration instructions (p. 2). Later: mgmod.bin in card root, power on. Recovery: official mg204.wav via audio.')],left=105,size=9.8,leading=13.1,pad=4)
g.note('<b>(c) 2026 vwal</b> (our additions). Upstream: <b>(c) 2026 the morphagene-mods contributors</b> (MIT), by Briskcat. Free use/share with notices; no sales, paid bundles/products or firmware services. <b>Exception: Make Noise official integration/distribution.</b> Paid music-making remains allowed. Full terms: embedded LICENSE.txt. Patcher: vwal.github.io/morphagene-patcher/.')
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
