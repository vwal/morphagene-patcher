"""Dev4 executes real compiled Thumb code; disk/peripherals are mocked explicitly."""
import os
import struct
import unittest
from pathlib import Path
from tests.arm import *

STATE = 0x2002A820
PHASE, STARTED, OWNED, PENDING, RESULT, FINISHED, ABSENT, SEEN = range(STATE, STATE+32, 4)
VALUES = STATE+32
CARD, FLAGS, REC, REC_REQUEST = 0x20001290, 0x20022074, 0x20022108, 0x20021320
SAMPLES, SHIFT, DETECT = 0x20021c88, 0x40020810, 0x40021C10
MOD, SETTINGS, STOCK = 0x2002A000, 0x2002A0F0, 0x200012A8
OPEN, READ, CLOSE, MOUNT = 0x08032260, 0x080323FC, 0x080327A8, 0x0803219C
SEEK, NAME = 0x08032BE8, 0x08021F74
SPLICE_NAME, STAT = 0x08022060, 0x08033128
FS, LIVE, CID, VALID = 0x2002D000, 0x2002D800, 0x2002427C, STATE+136
DIGEST, HASH_READY, LIVE_FILE, SCANNING = STATE+188, STATE+220, STATE+224, STATE+228
REEL_BYTES=bytes(i%251 for i in range(512))

def remember(a, fs=FS, live=LIVE):
    a.put(CARD,1);a.put(DETECT,0);a.put(0x20001040,9)
    a.uc.mem_write(CID,b'original-card-id')  # 16 bytes
    a.put(live,fs);a.uc.mem_write(live+4,struct.pack('<HBB',1,3,0))
    for offset,value in [(8,96),(12,512),(16,3),(28,65),(32,fs+88)]:a.put(live+offset,value)
    a.uc.mem_write(0x20028000,b'mg9.wav\0')
    call(a,'reload_file_opened',live,0x20028000,0)
    Disk(a,b'header\nvqnt 1\n')
    call(a,'reload_service',fs,live)
    assert a.get(VALID)==1
    assert a.get(HASH_READY)==1
    a.put(CARD,0);a.put(live,0)

def arm():
    a = Arm('settings_reload', 'reload_mount')
    a.put(SETTINGS, 0x5354504F)
    a.put(MOD, 0x53484654)
    a.put(0x20001020, 14)
    a.uc.mem_write(MOD+4, b'\1\0\0\0')
    remember(a)
    return a

def call(a, symbol, *args, stops=()):
    if symbol=='reload_service' and len(args)==1:args=(*args,LIVE)
    for r, v in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
        a.uc.reg_write(r, v)
    a.run(symbol, stops, count=2000000)
    return a.uc.reg_read(UC_ARM_REG_R0)

def line(a, text):
    a.uc.mem_write(0x20028000, text.encode()+b'\0')
    return call(a, 'reload_parse_line', 0x20028000)

def tick(a, now, present=False, shift=True, rec=0, splice=0):
    a.put(SAMPLES, (now*8)&0xffffffff); a.put(DETECT, 0 if present else 8192)
    a.put(SHIFT, 2 if shift else 0)
    return call(a, 'reload_tick', 4 if shift else 0, rec, splice)

class Disk:
    def __init__(self, a, data, *, open_error=0, read_error_at=None, close_error=0,
                 mount_error=0, unmount_error=0, chunks=512, during_read=None,
                 reel_error=0, seek_error=0, wrong_card=False, changed_reel=False):
        self.a=a; self.data=data; self.position=0; self.events=[];self.handles={}
        def mount(a):
            fs=a.uc.reg_read(UC_ARM_REG_R0)
            opt=a.uc.reg_read(UC_ARM_REG_R2)
            self.events.append(('mount' if fs else 'unmount', opt))
            if fs and wrong_card:a.put(CID,123)
            a.uc.reg_write(UC_ARM_REG_R0, mount_error if fs else unmount_error)
        def op(a):
            ptr=a.uc.reg_read(UC_ARM_REG_R1)
            name=bytes(a.uc.mem_read(ptr,32)).split(b'\0')[0]
            file=a.uc.reg_read(UC_ARM_REG_R0);self.handles[file]=name;a.put(file+8,0)
            self.events.append(('open', name, a.uc.reg_read(UC_ARM_REG_R2)))
            if name==b'options.txt':a.uc.reg_write(UC_ARM_REG_R0,open_error)
            elif name.startswith(b'splice'):a.uc.reg_write(UC_ARM_REG_R0,4)
            else:
                live=a.uc.reg_read(UC_ARM_REG_R0)
                a.put(live,FS);a.uc.mem_write(live+4,struct.pack('<HBB',2,3,0))
                for offset,value in [(8,0),(12,512),(16,4 if changed_reel else 3),
                                     (28,65),(32,FS+88)]:a.put(live+offset,value)
                a.uc.reg_write(UC_ARM_REG_R0,reel_error)
        def read(a):
            self.events.append(('read',))
            file=a.uc.reg_read(UC_ARM_REG_R0)
            options=self.handles.get(file)==b'options.txt'
            if options and during_read: during_read(a)
            self.position=a.get(file+8)
            if options and read_error_at is not None and self.position >= read_error_at:
                a.uc.reg_write(UC_ARM_REG_R0,1); return
            count=min(a.uc.reg_read(UC_ARM_REG_R2),chunks if options else 512)
            source=self.data if options else (b'x'+REEL_BYTES[1:] if changed_reel else REEL_BYTES)
            data=source[self.position:self.position+count]
            self.position+=len(data)
            a.put(file+8,self.position)
            if data: a.uc.mem_write(a.uc.reg_read(UC_ARM_REG_R1),data)
            a.put(a.uc.reg_read(UC_ARM_REG_R3),len(data))
            a.uc.reg_write(UC_ARM_REG_R0,0)
        def close(a):
            self.events.append(('close',));a.uc.reg_write(UC_ARM_REG_R0,close_error)
        def seek(a):
            position=a.uc.reg_read(UC_ARM_REG_R1);self.events.append(('seek',position))
            a.put(a.uc.reg_read(UC_ARM_REG_R0)+8,position)
            a.uc.reg_write(UC_ARM_REG_R0,seek_error)
        def name(a):
            n=a.uc.reg_read(UC_ARM_REG_R1)
            a.uc.mem_write(a.uc.reg_read(UC_ARM_REG_R0),f'mg{n}.wav'.encode()+b'\0')
        def splice_name(a):a.uc.mem_write(a.uc.reg_read(UC_ARM_REG_R0),b'splice9.txt\0')
        def stat(a):
            name=bytes(a.uc.mem_read(a.uc.reg_read(UC_ARM_REG_R0),32)).split(b'\0')[0]
            a.uc.reg_write(UC_ARM_REG_R0,0 if name==b'mg9.wav' else 4)
        a.calls.update({MOUNT:mount,OPEN:op,READ:read,CLOSE:close,SEEK:seek,NAME:name,
                        SPLICE_NAME:splice_name,STAT:stat})

def stage(a, data=b'7 46345 0\nvsop 2\nvqnt 1\noctl 3\n', **kw):
    a.put(PHASE,3); a.put(DETECT,0)
    d=Disk(a,data,**kw)
    call(a,'reload_service',0x2002d000)
    return d

class ReloadGesture(unittest.TestCase):
    def test_hold_then_insertion_claims_only_at_insertion(self):
        a=arm()
        self.assertEqual(tick(a,100),0);self.assertEqual(a.get(PHASE),1)
        self.assertEqual(tick(a,6099),0);self.assertEqual(a.get(PHASE),1)
        self.assertEqual(tick(a,6100),0);self.assertEqual(a.get(PHASE),2)
        self.assertEqual(tick(a,6200,present=True),0)
        self.assertEqual(call(a,'reload_mounted',0),1)
        self.assertEqual(a.get(PHASE),3)
        self.assertEqual(bytes(a.uc.mem_read(MOD+4,3)),b'\1\1\7')
        self.assertEqual(tick(a,6300,present=True),1)
        self.assertEqual(tick(a,6400,present=True,shift=False),0)
        self.assertEqual(a.get(OWNED),0)

    def test_no_interception_for_boot_ordinary_mount_or_existing_gestures(self):
        for name in ('boot','mounted','recording','request','knob','rec_button','splice_button','early_insert','release'):
            with self.subTest(name=name):
                a=arm();tick(a,10)
                args={}
                if name=='boot':a.put(SETTINGS,0)
                if name=='mounted':a.put(CARD,1)
                if name=='recording':a.put(REC,1)
                if name=='request':a.put(REC_REQUEST,1)
                if name=='knob':a.uc.mem_write(MOD+5,b'\1')
                if name=='rec_button':args['rec']=10
                if name=='splice_button':args['splice']=10
                if name=='early_insert':call(a,'reload_mounted',0)
                if name=='release':args['shift']=False
                self.assertEqual(tick(a,6010,**args),0)
                self.assertEqual(a.get(PHASE),0)

    def test_wraparound_and_removal_debounce(self):
        a=arm();tick(a,0xfffffff0);tick(a,5990)
        self.assertEqual(a.get(PHASE),2)
        a.put(PHASE,5);tick(a,7000,present=True,shift=False)
        tick(a,7100,shift=False);tick(a,7699,shift=False)
        self.assertEqual(a.get(PHASE),5)
        tick(a,7800,shift=False)
        Disk(a,b'',mount_error=3)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(PHASE),0)

    def test_parked_card_cannot_mount_again_until_removed(self):
        a=arm();a.put(PHASE,5)
        tick(a,10,present=True,shift=False)
        call(a,'reload_mount',stops=[0x08023132,0x0802313c])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x0802313c)
        tick(a,20,shift=False);tick(a,1000,shift=False)
        Disk(a,b'',mount_error=3)
        call(a,'reload_service',FS,LIVE)
        call(a,'reload_mount',stops=[0x08023132,0x0802313c])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x08023132)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0),SP+1948)

    def test_led_patterns_preserve_other_leds(self):
        a=arm();a.put(PHASE,2)
        self.assertEqual(call(a,'reload_led_mask',0xa550),0xa551)
        for result, expected in [(1,[1,0,1,0,0,0]),(2,[1,0,1,0,1,0])]:
            a.put(PHASE,5);a.put(RESULT,result);a.put(FINISHED,100)
            for n,on in enumerate(expected):
                a.put(SAMPLES,100+n*4800)
                self.assertEqual(call(a,'reload_led_mask',0xa550),0xa550|on)

class ReloadParser(unittest.TestCase):
    def test_bank_validates_without_changing_the_browsed_or_open_bank(self):
        bank = 0x2002a61f
        for value in range(9):
            with self.subTest(bank=value):
                a=arm()
                a.uc.mem_write(bank,bytes([2]))
                stage(a,f'1 45875 0\nbank {value}\n'.encode())
                call(a,'reload_commit')
                self.assertEqual(a.get(CARD),1)
                self.assertEqual(a.uc.mem_read(bank,1),bytes([2]))
                self.assertEqual(a.uc.mem_read(0x20028ff0,2),bytes([1,9]))
        for value in ('', '9', '00', '3.0', '2 junk', '1\nbank 2'):
            with self.subTest(bad=value):
                a=arm()
                stage(a,f'1 45875 0\nvqnt 1\nbank {value}\n'.encode())
                self.assertEqual(a.get(RESULT),2)
                self.assertEqual(a.get(PENDING),0)
                self.assertEqual(a.uc.mem_read(0x2002a610,1),bytes(1))

    def test_primary_open_forgets_previous_identity_after_failure(self):
        for path,error in [('bank2/mgw.wav',4),('mg0.wav',0),('bank9/mg1.wav',0),
                           ('bank2/mgx.wav',0),('bank2/mg1.wav.tmp',0)]:
            with self.subTest(path=path,error=error):
                a=arm()
                a.uc.mem_write(0x20028000,path.encode()+bytes(1))
                call(a,'reload_file_opened',LIVE,0x20028000,error)
                self.assertEqual(a.uc.mem_read(0x20028ff0,2),bytes(2))
                self.assertEqual(a.get(HASH_READY),0)
                d=stage(a)
                self.assertEqual(d.events,[('unmount',0)])
                self.assertEqual(a.get(CARD),0)

    def test_all_keys_bounds_and_fractional_chords(self):
        keys=[('vsop',2),('pmod',2),('omod',1),('cvop',1),('ckop',2),('rsop',1),
              ('pmin',1),('inop',1),('gnsm',1),('mcr1','-0.06250'),('mcr2','1.49831'),
              ('mcr3','16.00000'),('tape',0),('octl',4),('fxsl',2),('mono',2),('cpul',1),
              ('mcap',9),('sldm',1),('root',100),('tlen',16),('ingn',3),
              ('scal','3,5,7,10'),('vrng',1),('dens',1),('vqnt',1),('mlop',1),('dstr','2.5')]
        a=arm()
        for i,(key,val) in enumerate(keys):
            self.assertEqual(line(a,f'{key}\t{val}'),1,key)
            expected=25 if i==27 else bits(float(val)) if 9<=i<=11 else 1192 if i==22 else int(val)
            self.assertEqual(a.get(STATE+236 if i==27 else STATE+232 if i==26 else VALUES+4*i),expected,key)
        self.assertEqual(a.get(SEEN),(1<<28)-1)

    def test_invalid_recognized_values_and_duplicates(self):
        for text in ['mlop 2','mlop -1','mlop 10','vsop 3','vqnt 2','tape -1','octl 5','fxsl 3','mono 3','mcap 10',
                     'root 101','root 999999999','tlen 0x','tlen 17','ingn 4','gnsm 2',
                     'vqnt 1oops','vqntX1','scal 12','scal 0,3','scal 3,','scal 3,,5',
                     'mcr1 0.','mcr1 nan','mcr1 inf','mcr1 -17','mcr1 0.06','mcr1 1e99']:
            with self.subTest(text=text):self.assertEqual(line(arm(),text),0)
        a=arm();self.assertEqual(line(a,'vqnt 1'),1);self.assertEqual(line(a,'vqnt 0'),0)

    def test_whitespace_empty_scale_unknown_and_missing_keys(self):
        a=arm();self.assertEqual(line(a,'  scal 0\r'),1)
        self.assertEqual(a.get(VALUES+22*4),0)
        self.assertEqual(line(a,'future 3'),1)
        self.assertEqual(a.get(SEEN),1<<22)
        a.put(STOCK,1);a.uc.mem_write(SETTINGS+4,bytes(range(10)))
        a.put(PENDING,1);call(a,'reload_commit')
        self.assertEqual(a.get(STOCK),1)
        self.assertEqual(bytes(a.uc.mem_read(SETTINGS+4,10)),bytes(range(10)))

class ReloadTransaction(unittest.TestCase):
    def test_matching_content_accepts_different_hardware_id(self):
        a=arm();stage(a,wrong_card=True);call(a,'reload_commit')
        self.assertEqual(a.get(CARD),1);self.assertEqual(a.get(RESULT),1)

    def test_write_invalidation_ignores_options_and_cpu_logs(self):
        for file in (LIVE,LIVE-552,0x2002a920,0x20029a00,LIVE+552):
            a=arm();call(a,'reload_dirty',file)
            self.assertEqual(a.get(HASH_READY),0 if file in (LIVE,LIVE-552) else 1)

    def test_snapshot_requires_clean_idle_file_and_rejects_offline_edits(self):
        for kind in ('dirty','error','recording','request','wrong_fs'):
            with self.subTest(kind=kind):
                a=arm();a.put(CARD,1);a.put(LIVE,FS)
                if kind=='dirty':a.uc.mem_write(LIVE+6,b'\x43')
                elif kind=='error':a.uc.mem_write(LIVE+7,b'\x01')
                elif kind=='recording':a.put(REC,1)
                elif kind=='request':a.put(FLAGS,1)
                else:a.put(LIVE,0)
                call(a,'reload_service',FS,LIVE)
                self.assertEqual(a.get(VALID),0)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_PRIMASK),0)
        a=arm();a.put(FLAGS,32);tick(a,10,shift=False)
        self.assertEqual(a.get(VALID),0)
        a.put(FLAGS,0);stage(a)
        self.assertEqual(a.get(PENDING),0);self.assertEqual(a.get(RESULT),2)

    def test_reconnect_stage_then_audio_commit(self):
        a=arm();a.put(0x20001040,9);a.put(0x200220e0,bits(1.25))
        a.uc.mem_write(0x2002215c,b'\x17'*128)
        before=bytes(a.uc.mem_read(0x20000000,0x2a820))
        d=stage(a,chunks=7)
        self.assertEqual(bytes(a.uc.mem_read(0x20000000,0x2a820)),before)
        self.assertEqual(a.get(PENDING),1)
        self.assertEqual(d.events[0],('mount',1))
        self.assertIn(('open',b'options.txt',1),d.events)
        self.assertIn(('open',b'mg9.wav',3),d.events)
        self.assertEqual(d.events[-1],('seek',96))
        self.assertNotIn(('unmount',0),d.events)
        self.assertEqual(a.get(CARD),0)
        call(a,'reload_commit')
        self.assertEqual(a.get(STOCK),2)
        self.assertEqual(a.uc.mem_read(0x2002a610,1),b'\1')
        self.assertEqual(a.get(0x20001040),9)
        self.assertEqual(a.get(0x200220e0),bits(1.25))
        self.assertEqual(a.uc.mem_read(0x2002215c,128),b'\x17'*128)
        self.assertEqual(a.get(RESULT),1);self.assertEqual(a.get(CARD),1)

    def test_all_failures_leave_settings_intact(self):
        cases=[(b'header\nvqnt 1\noctl 9\n',{}), (b'header\nvqnt 1\nvqnt 0\n',{}),
               (b'',{}),(b'header\n//comments only\n',{}),
               (b'header\nvqnt 1\0\n',{}),(b'header\n'+b'x'*128,{}),
               (b'header\n//'+b'x'*17000,{}),
               (b'header\nvqnt 1\n',{'open_error':4}),
               (b'header\nvqnt 1\n',{'read_error_at':0}),
               (b'header\nvqnt 1\n',{'close_error':1}),
               (b'header\nvqnt 1\n',{'mount_error':3}),
               (b'header\nvqnt 1\n',{'reel_error':4}),
               (b'header\nvqnt 1\n',{'seek_error':1})]
        for data,kw in cases:
            with self.subTest(data=data[:30],kw=kw):
                a=arm();before=bytes(a.uc.mem_read(0x20000000,0x2a820))
                d=stage(a,data,**kw);call(a,'reload_commit')
                self.assertEqual(a.get(PENDING),0)
                self.assertEqual(a.get(RESULT),2)
                # CID is refreshed by the SD driver even on a wrong-card failure.
                after=bytearray(a.uc.mem_read(0x20000000,0x2a820))
                after[CID-0x20000000:CID-0x20000000+16]=before[CID-0x20000000:CID-0x20000000+16]
                self.assertEqual(bytes(after),before)
                self.assertEqual(d.events[-1],('unmount',0))

    def test_long_comments_crlf_eof_and_chunk_boundaries(self):
        data=b'999 123 0\r\n//'+b'a'*700+b'\r\nvqnt 1 //'+b'b'*1000+b'\r\nscal 3 5 7 10'
        for chunks in (1,7,512):
            a=arm();stage(a,data,chunks=chunks)
            self.assertEqual(a.get(PENDING),1)
            call(a,'reload_commit')
            self.assertEqual(a.uc.mem_read(0x2002a610,1),b'\1')
            self.assertEqual(struct.unpack('<H',a.uc.mem_read(0x2002a604,2))[0],1192)

    def test_recording_and_card_work_defer_read_and_commit(self):
        for addr in (REC,REC_REQUEST,FLAGS):
            a=arm();a.put(addr,1);d=stage(a)
            self.assertEqual(d.events,[]);self.assertEqual(a.get(PHASE),3)
            a.put(addr,0);call(a,'reload_service',FS)
            self.assertEqual(a.get(PENDING),0)
            self.assertEqual(a.get(RESULT),2,'offline edits invalidate reconnect')

    def test_record_starts_during_read_no_partial_application(self):
        a=arm();stage(a,during_read=lambda a:a.put(REC,1))
        call(a,'reload_commit');self.assertEqual(a.get(STOCK),0)
        a.put(REC,0);call(a,'reload_commit');self.assertEqual(a.get(STOCK),0)
        self.assertEqual(a.get(CARD),0);self.assertEqual(a.get(RESULT),2)

    def test_record_or_changed_reel_before_commit_cleans_up_in_main(self):
        for address,value in [(REC,1),(REC_REQUEST,1),(FLAGS,1),(0x20001040,8)]:
            a=arm();d=stage(a);a.put(address,value)
            call(a,'reload_commit')
            self.assertEqual(a.get(CARD),0);self.assertEqual(a.get(STOCK),0)
            self.assertEqual(a.get(PHASE),7);self.assertEqual(a.get(PENDING),0)
            call(a,'reload_service',FS)
            self.assertEqual(d.events[-1],('unmount',0))
            self.assertEqual(a.get(PHASE),5);self.assertEqual(a.get(LIVE),0)

    def test_missing_snapshot_and_changed_live_reel_fail_without_mount(self):
        for address,value in [(VALID,0),(0x20001040,8),(0x20001064,99)]:
            a=arm();a.put(address,value);d=stage(a)
            self.assertEqual(d.events,[('unmount',0)])
            self.assertEqual(a.get(RESULT),2)

    def test_gain_apply_marker_chord_mirrors_and_locks(self):
        a=arm();a.uc.mem_write(MOD+7,b'\1');a.uc.mem_write(SETTINGS+14,b'\1\2')
        stage(a,b'123 999 0\ningn 3\nmcr1 -0.5\nmcr2 1.5\nmcr3 4\nvrng 1\n')
        call(a,'reload_commit')
        self.assertEqual(a.uc.mem_read(SETTINGS+13,3),b'\3\0\0')
        self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')
        self.assertEqual(a.uc.mem_read(0x20022124,12),struct.pack('<3f',-.5,1.5,4))

    def test_commit_is_atomic_and_preserves_primask(self):
        a=arm();stage(a)
        writes=[]
        from unicorn import UC_HOOK_MEM_WRITE
        h=a.uc.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,val,user:
                       writes.append((addr,uc.reg_read(UC_ARM_REG_PRIMASK))),
                       begin=STOCK,end=STOCK+56)
        call(a,'reload_commit')
        self.assertTrue(writes);self.assertTrue(all(mask==1 for _,mask in writes))
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PRIMASK),0)
        a.uc.hook_del(h)

    def test_hook_registers_stack_and_led_routing(self):
        a=arm();a.put(PHASE,2);a.put(SAMPLES,48000)
        a.uc.reg_write(UC_ARM_REG_R1,0);a.uc.reg_write(UC_ARM_REG_R3,0xa550)
        a.run('reload_led',[0x08024944])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R3),0xa551)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R2),0xa551)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
        a=arm();stage(a)
        regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
              UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
              UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]
        for i,r in enumerate(regs):a.uc.reg_write(r,0x12340000+i)
        for i in range(32):a.uc.reg_write(UC_ARM_REG_S0+i,bits(i+.5))
        a.run('reload_audio',[0x0802751c])
        for i,r in enumerate(regs):self.assertEqual(a.uc.reg_read(r),0x12340000+i)
        for i in range(32):self.assertEqual(a.uc.reg_read(UC_ARM_REG_S0+i),bits(i+.5))
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP-36)
        self.assertEqual(a.get(PENDING),0)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE for real audio/main integration')
class ReloadIntegration(unittest.TestCase):
    def timer(self, image):
        a=arm();a.uc.mem_write(0x08020000,image)
        a.uc.ctl_remove_cache(0x08020000,0x08060000)
        a.uc.mem_map(0x40000000,0x1000)  # TIM2 status/ack registers
        a.uc.mem_write(0x20000000,image[0x27250:0x28400])
        a.put(SETTINGS,0x5354504f);a.put(MOD,0x53484654)
        a.put(0x20001020,1);a.put(0x200012e0,0)
        a.uc.mem_write(MOD+4,b'\0\0\0\0')
        a.calls[0x0802dcd4]=lambda a:a.uc.reg_write(UC_ARM_REG_R0,1)
        a.syms['timer']=0x08024718
        return a

    def timer_tick(self,a,shift,*,present=True,blocks=None):
        a.put(SAMPLES,max(a.get(SAMPLES)+32,blocks*8 if blocks is not None else 0))
        a.put(SHIFT,2 if shift else 0);a.put(DETECT,0 if present else 8192)
        a.put(0x20021394,a.get(SAMPLES)//16)
        a.run('timer',count=50000)

    def test_real_timer_owned_hold_release_and_following_navigation(self):
        from tests.test_firmware_integration import images
        a=self.timer(images()[1])
        for i in range(10):self.timer_tick(a,True,present=False,blocks=i)
        self.assertEqual(a.get(PHASE),1)
        self.timer_tick(a,True,present=False,blocks=6010)
        self.assertEqual(a.get(PHASE),2)
        self.timer_tick(a,True,present=True,blocks=6011)
        a.syms['mounted']=0x08023136
        a.uc.reg_write(UC_ARM_REG_R0,0)
        a.run('mounted',[0x08022f7e,0x0802313c,0x08023288])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x08022f7e)
        self.assertEqual(a.get(PHASE),3)
        self.assertEqual(a.get(0x200012e0),0)
        for _ in range(8):self.timer_tick(a,True,blocks=6012)
        a.put(PHASE,5);a.put(RESULT,1);a.put(FINISHED,6012*8)
        for _ in range(8):self.timer_tick(a,False,blocks=6013)
        self.assertEqual(a.get(OWNED),0)
        self.assertEqual(a.get(0x200012e0),0,'reload release must not navigate')
        # Let the normal release debounce settle, then ordinary SHIFT remains
        # available while the settings card is parked (no remount required).
        for _ in range(1000):self.timer_tick(a,False,blocks=6014)
        for _ in range(8):self.timer_tick(a,True,blocks=6015)
        for _ in range(8):self.timer_tick(a,False,blocks=6016)
        self.assertEqual(a.get(0x200012e0),1)
        self.assertEqual(a.get(PHASE),5)

    def test_real_timer_ordinary_shift_tap_matches_development_3(self):
        from tests.test_firmware_integration import images
        previous=os.environ.get('MGMOD_DEV3')
        if not previous:self.skipTest('set MGMOD_DEV3')
        for image in (Path(previous).read_bytes(),images()[1]):
            a=self.timer(image);a.put(CARD,1)
            for _ in range(8):self.timer_tick(a,True)
            for _ in range(8):self.timer_tick(a,False)
            self.assertEqual(a.get(0x200012e0),1)

    def test_mounted_shift_hold_never_arms_or_claims_reload(self):
        from tests.test_firmware_integration import images
        for inserted in (True,False):
            a=self.timer(images()[1]);a.put(CARD,1)
            for i in range(10):self.timer_tick(a,True,present=inserted,blocks=i)
            for blocks in (6000,12000,60000):
                self.timer_tick(a,True,present=inserted,blocks=blocks)
                self.assertEqual(a.get(PHASE),0)
                self.assertEqual(a.get(OWNED),0)
                self.assertNotEqual(bytes(a.uc.mem_read(MOD+6,1)),b'\7')

    def test_unchanged_audio_and_playhead_match_development_3(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        previous=os.environ.get('MGMOD_DEV3')
        if not previous:self.skipTest('set MGMOD_DEV3 to the preserved Development 3 raw image')
        old=Path(previous).read_bytes();new=images()[1]
        for mono in (0,1,2):
            for density in (0,1):
                with self.subTest(mono=mono,density=density):
                    a,b=Audio(old),Audio(new)
                    for audio in (a,b):
                        audio.a.uc.mem_write(SETTINGS+7,bytes([mono]))
                        audio.a.uc.mem_write(0x2002a607,bytes([density]))
                        audio.a.uc.mem_write(0x2002a610,b'\1')
                    self.assertEqual(a.blocks(8),b.blocks(8))
                    # Stage a no-op configuration and commit through the actual
                    # patched audio entry. No playhead/rate/voice state changes.
                    b.a.put(SEEN,(1<<13)|(1<<15)|(1<<24)|(1<<25))
                    for i,value in [(13,1),(15,mono),(24,density),(25,1)]:b.a.put(VALUES+4*i,value)
                    b.a.put(PENDING,1)
                    self.assertEqual(a.blocks(32),b.blocks(32))
                    self.assertEqual(a.uc.mem_read(0x20021e64,0x400),b.uc.mem_read(0x20021e64,0x400))

    def test_actual_main_hook_never_reaches_reel_or_updater_paths(self):
        from tests.test_firmware_integration import images
        a=arm();remember(a,SP+1948,SP+844)
        a.uc.mem_write(0x08020000,images()[1])
        a.uc.ctl_remove_cache(0x08020000,0x08060000)
        a.put(PHASE,3);a.put(DETECT,0)
        a.uc.reg_write(UC_ARM_REG_R6,0);a.uc.reg_write(UC_ARM_REG_R7,FLAGS)
        Disk(a,b'7 0 0\nvqnt 1\n')
        # This hook receives the original main-frame objects, not test scratch.
        a.syms['main']=0x08022f7e
        # Execute the branch itself once before stopping at the common head.
        a.uc.emu_start(0x08022f7f,0,count=1)
        a.syms['main']=a.uc.reg_read(UC_ARM_REG_PC)
        # Disk's mock fresh FIL must point into this main frame.
        original_open=a.calls[OPEN]
        def opened(a):
            live=a.uc.reg_read(UC_ARM_REG_R0);original_open(a)
            if live==SP+844:a.put(live,SP+1948);a.put(live+32,SP+1948+88)
        a.calls[OPEN]=opened
        a.run('main',[0x08022f7e,0x08023288,0x0802734c],count=2000000)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x08022f7e)
        self.assertEqual(a.get(PENDING),1)
        self.assertEqual(a.get(CARD),0)

    def test_gain_is_applied_by_real_main_loop_while_card_is_unmounted(self):
        from tests.test_firmware_integration import images
        a=arm();a.uc.mem_write(0x08020000,images()[1])
        a.uc.ctl_remove_cache(0x08020000,0x08060000)
        a.uc.mem_write(SETTINGS+13,b'\3\0\0')
        a.put(0x20001068,1);a.put(PHASE,5)
        a.uc.reg_write(UC_ARM_REG_R6,0);a.uc.reg_write(UC_ARM_REG_R7,FLAGS)
        gain_calls=[]
        a.calls[0x080257dc]=lambda a:gain_calls.append(a.uc.reg_read(UC_ARM_REG_R0))
        a.syms['main']=0x08022fbc
        a.run('main',[0x08022f7e],count=100000)
        self.assertEqual(gain_calls,[3])
        self.assertEqual(a.get(0x20001068),3)
        self.assertEqual(a.get(CARD),0)
