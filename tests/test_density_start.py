"""Execute startup-density parsing, persistence, timing and reload as Thumb code."""
import os
import unittest
from tests.arm import *
from tests.test_settings_reload import arm, stage, call, line, SEEN, PENDING, RESULT
from tests import test_arm_updater

DSTR, DENS, DENSITY = 0x2002A614, 0x2002A607, 0x2002A800

def parse(a, text):
    a.uc.mem_write(0x20002000,bytes(128))
    a.uc.mem_write(0x20002000,text.encode()+b'\0')
    a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
    a.run('opt_parse',[0x080232FC,0x0802332A])
    assert a.uc.reg_read(UC_ARM_REG_PC)==0x080232FC

class DensityStart(unittest.TestCase):
    def test_every_tenth_parses_consistently_at_boot_and_reload(self):
        boot=Arm('options_keys','opt_parse');live=arm()
        for n in range(1281):
            text=f'dstr {n//10}.{n%10}'
            parse(boot,text)
            self.assertEqual(boot.get(DSTR),n,text)
            live.put(SEEN,0)
            self.assertEqual(line(live,text),1,text)
            self.assertEqual(live.get(0x2002A820+236),n,text)
        for text,n in [('dstr 0',0),('dstr 0.0',0),('dstr 8',80),('dstr\t128',1280),('dstr  0.5  ',5)]:
            parse(boot,text);self.assertEqual(boot.get(DSTR),n)
        parse(boot,'dstr 2.5 // startup');self.assertEqual(boot.get(DSTR),25)

    def test_normal_mount_after_density_initialized_rearms_the_scheduler(self):
        boot = Arm('options_keys', 'opt_parse')
        for value, expected in [('1.0', 10), ('0', 0)]:
            boot.put(DENSITY, 1)
            parse(boot, 'dstr '+value)
            self.assertEqual(boot.get(DENSITY), 0)
            self.assertEqual(boot.get(DSTR), expected)

    def test_invalid_values_leave_boot_value_and_reject_reload_atomically(self):
        boot=Arm('options_keys','opt_parse')
        for value in ['', '0.01', '0.09', '128.1', '129', '-1', '+8', '.5', '8.', '8.00',
                      'nan', 'inf', '1e1', '0008', '999999999999999999', '8junk', '8 9', '8/']:
            text='dstr '+value
            boot.put(DSTR,80);parse(boot,text);self.assertEqual(boot.get(DSTR),80,text)
            live=arm();live.put(DSTR,80)
            stage(live,('header\nvqnt 1\n'+text+'\n').encode());call(live,'reload_commit')
            self.assertEqual(live.get(DSTR),80,text)
            self.assertEqual(live.get(RESULT),2,text)
            self.assertEqual(bytes(live.uc.mem_read(0x2002a610,1)),b'\0',text)
        live=arm();stage(live,b'header\ndstr 4\ndstr 16\n')
        self.assertEqual(live.get(PENDING),0)
        self.assertEqual(live.get(RESULT),2)

    def test_startup_default_rounding_and_live_adjustments(self):
        a=Arm('gene_shape','g2_size');a.uc.mem_write(DENS,b'\1');a.put(0x200220e0,bits(1))
        for n in range(1,1281):
            a.put(DENSITY,0);a.put(DSTR,n);a.run('density_prepare')
            self.assertEqual(a.get(DENSITY+8),(480000+n//2)//n,n)
            self.assertEqual(a.get(DENSITY+12),a.get(DENSITY+8),n)
        a.put(DENSITY,0);a.put(DSTR,0);a.run('density_prepare')
        self.assertEqual([a.get(DENSITY+k) for k in (0,4,8,12)], [1,0,0,0])
        a.uc.reg_write(UC_ARM_REG_R0, 192)  # just above the shifted detent
        a.run('density_adjust')
        a.run('density_prepare')
        self.assertEqual([a.get(DENSITY+k) for k in (4,8,12)], [1,480000,480000])
        self.assertEqual(a.get(DSTR), 0)  # panel edit leaves the boot value intact
        for n in [1281,0xffffffff]:
            a.put(DENSITY,0);a.put(DSTR,n);a.run('density_prepare')
            self.assertEqual(a.get(DENSITY+8),48000,n)
        a.put(DENSITY,0);a.put(DSTR,25);a.run('density_prepare')
        self.assertEqual(a.get(DENSITY+8),19200)
        a.uc.reg_write(UC_ARM_REG_R0,4032);a.run('density_adjust')
        self.assertEqual(a.get(DENSITY+8),375)
        self.assertEqual(a.get(DSTR),25)
        a.put(DSTR,40);a.uc.mem_write(DENS,b'\0');a.run('density_prepare')
        a.uc.mem_write(DENS,b'\1');a.run('density_prepare')
        self.assertEqual(a.get(DENSITY+8),375)  # same boot keeps performed value
        a.put(DENSITY,0);a.run('density_prepare')
        self.assertEqual(a.get(DENSITY+8),12000) # new boot initializes from dstr

    def test_boot_resets_dirty_startup_setting_to_one(self):
        a,events=test_arm_updater.UpdaterHooks().run_update(None)
        self.assertEqual(a.get(DSTR),10)

    def test_writer_round_trips_configured_rate_not_performed_rate(self):
        a=Arm('options_keys','opt_parse');a.put(0x2002A0F0,0x5354504F)
        output=[]
        def printf(a):
            p=a.uc.reg_read(UC_ARM_REG_R1)
            fmt=bytes(a.uc.mem_read(p,512)).split(b'\0')[0].decode()
            args=[a.uc.reg_read(UC_ARM_REG_R2),a.uc.reg_read(UC_ARM_REG_R3)]
            nargs = fmt.count('%d') + fmt.count('%u')
            output.append(fmt % tuple(args[:nargs]))
            a.uc.reg_write(UC_ARM_REG_R0,len(output[-1]))
        a.calls={0x08034804:printf,0x080327a8:lambda a:a.uc.reg_write(UC_ARM_REG_R0,0)}
        for n in (0,1,2,3,4,5,10,25,80,1279,1280):
            a.put(DSTR,n);a.put(DENSITY+8,375);output.clear()
            a.run('opt_write',[0x08024566])
            written=next(x for x in ''.join(output).splitlines() if x.startswith('dstr '))
            self.assertTrue(written.startswith(f'dstr {n//10}.{n%10} '),written)
            a.put(DSTR,0xffffffff);parse(a,written);self.assertEqual(a.get(DSTR),n)
            self.assertEqual(a.get(DENSITY+8),375)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)

    def test_reload_recalls_explicit_rates_even_when_config_unchanged(self):
        from tests.test_settings_reload import CARD, LIVE
        for n in (0,1,2,3,4,5,25,80,1280):
            for enabled in (0,1):
                a=arm();call(a,'reload_commit')  # initialize Morph table cache
                a.put(DSTR,80);a.uc.mem_write(DENS,bytes([enabled]))
                a.uc.mem_write(DENSITY,struct.pack('<5I',1,enabled,375,100,4))
                preserved={addr:bytes(a.uc.mem_read(addr,size)) for addr,size in
                           [(0x20001040,4),(0x200012e0,4),(0x20021e64,0x400),(0xd0000000,4096)]}
                stage(a,f'header\ndstr {n//10}.{n%10}\n'.encode())
                self.assertEqual(a.get(DSTR),80)
                self.assertEqual(a.get(DENSITY+8),375)
                call(a,'reload_commit')
                interval=(480000+n//2)//n if n else 0
                self.assertEqual(a.get(DSTR),n)
                self.assertEqual(a.get(DENSITY),1)
                self.assertEqual(a.get(DENSITY+8),interval)
                self.assertEqual(a.get(DENSITY+12),interval)
                self.assertEqual(bytes(a.uc.mem_read(DENS,1)),bytes([enabled]))
                self.assertEqual(a.get(RESULT),1)
                self.assertEqual(a.get(CARD),1);self.assertEqual(a.get(LIVE+8),96)
                for addr,data in preserved.items():
                    self.assertEqual(bytes(a.uc.mem_read(addr,len(data))),data)
                a.put(DENSITY+12,99);call(a,'reload_commit')
                self.assertEqual(a.get(DENSITY+12),99)  # apply only once

    def test_missing_dstr_preserves_live_rate_and_phase(self):
        a=arm();a.put(DSTR,80);a.uc.mem_write(DENSITY,struct.pack('<5I',1,1,375,100,4))
        before=bytes(a.uc.mem_read(DENSITY,32))
        stage(a,b'header\nmlop 1\n');call(a,'reload_commit')
        self.assertEqual(a.get(DSTR),80)
        self.assertEqual(bytes(a.uc.mem_read(DENSITY,32)),before)
        self.assertEqual(a.get(RESULT),1)

    def test_failed_reconnection_or_validation_does_not_recall_density(self):
        from tests.test_settings_reload import REC
        for failure in ('invalid','duplicate','seek','reel','recording'):
            a=arm();a.put(DSTR,80);a.uc.mem_write(DENSITY,struct.pack('<5I',1,1,375,100,4))
            before=bytes(a.uc.mem_read(DENSITY,32))
            text=b'header\ndstr 0.1\n'
            if failure=='invalid':text+=b'vqnt 9\n'
            if failure=='duplicate':text+=b'dstr 8\n'
            stage(a,text,**({'seek_error':1} if failure=='seek' else {'reel_error':1} if failure=='reel' else {}))
            if failure=='recording':a.put(REC,1)
            call(a,'reload_commit')
            self.assertEqual(a.get(DSTR),80,failure)
            self.assertEqual(bytes(a.uc.mem_read(DENSITY,32)),before,failure)
            self.assertEqual(a.get(RESULT),2,failure)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
    def test_zero_boot_and_explicit_zero_reload_sound_like_stock_timing(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        from tests.test_unity_center import configure
        # Start both engines on the same playing splice. One is booted in the
        # configured stock detent. The reference uses dens 0 and no gestures.
        test, stock = (Audio(images()[1]) for _ in range(2))
        for engine in (test, stock):
            configure(engine.a, (0, 0, 0, 0), centered=1)
            for addr, val in ((0x20022160, 9600), (0x20021fbc, bits(9600)),
                              (0x20021c74, 2048), (0x20021c78, 0),
                              (0x20021c7c, 0), (0x20021c6c, 420), (DSTR, 0)):
                engine.a.put(addr, val)
        test.uc.mem_write(DENS, bytes([1]))
        self.assertEqual(test.blocks(1600), stock.blocks(1600))
        self.assertEqual(test.births, [0, 9600])
        self.assertEqual(test.births, stock.births)

        # The same configured zero must override a performed numeric rate.
        # Start both schedulers at 8/s and allow one new Gene to be born.
        for engine in (test, stock):
            engine.uc.mem_write(DENS, bytes([1]))
            engine.a.put(DENSITY, 1)
            engine.a.put(DENSITY+8, 6000)
            engine.a.put(DENSITY+12, 6000)
        self.assertEqual(test.blocks(800), stock.blocks(800))
        test.a.put(SEEN, 1 << 27)
        test.a.put(0x2002a820+236, 0)
        test.a.put(PENDING, 1)
        stock.uc.mem_write(DENS, bytes([0]))
        self.assertEqual(test.blocks(1600), stock.blocks(1600))
        self.assertEqual(test.births, stock.births)
        self.assertEqual(test.a.get(PENDING), 0)
        self.assertEqual(test.a.get(DENSITY+8), 0)
        self.assertEqual(test.uc.mem_read(DENS, 1), bytes([1]))

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
    def test_audio_boundary_recall_preserves_voices_and_ten_second_interval(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        a,b=Audio(images()[1]),Audio(images()[1])
        for engine in (a,b):
            engine.a.put(DSTR,80);engine.uc.mem_write(DENS,b'\1')
            engine.a.put(0x20021c7c,4095)
        self.assertEqual(a.blocks(8),b.blocks(8))
        # Stage 0.1 Hz on one engine. Change only the density timer on the
        # control engine: audio, voices and playback progress must still match.
        a.a.put(SEEN,1<<27);a.a.put(0x2002A820+236,1);a.a.put(PENDING,1)
        b.a.put(DENSITY+8,480000);b.a.put(DENSITY+12,480000)
        start=a.sample_index
        self.assertEqual(a.blocks(2),b.blocks(2))
        self.assertEqual(a.uc.mem_read(0x20021e64,0x400),b.uc.mem_read(0x20021e64,0x400))
        self.assertEqual(a.a.get(DSTR),1);self.assertEqual(a.a.get(PENDING),0)
        births=len(a.births)
        a.blocks(59997)
        self.assertEqual(len(a.births),births)  # no early launch within ten seconds
        a.blocks(1)
        self.assertEqual(a.births[-1],start+480000)
        # Recall a much faster rate without waiting for the old ten-second timer.
        start=a.sample_index
        a.a.put(SEEN,1<<27);a.a.put(0x2002A820+236,1280);a.a.put(PENDING,1)
        a.blocks(48)
        self.assertEqual(a.births[-1],start+375)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
    def test_recall_keeps_density_disabled_and_external_clock_priority(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        for enabled,clock in ((0,0),(1,1)):
            a=Audio(images()[1]);a.uc.mem_write(DENS,bytes([enabled]))
            a.a.put(0x20021cb0,clock)
            a.a.put(SEEN,1<<27);a.a.put(0x2002A820+236,1);a.a.put(PENDING,1)
            a.blocks(1)
            self.assertEqual(a.a.get(DENSITY+8),480000)
            self.assertEqual(a.a.get(DENSITY+4),0)
            self.assertEqual(a.a.get(0x20021cb0),clock)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
    def test_configured_rate_drives_real_audio_births(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        for n in (25,160,1280):
            a=Audio(images()[1]);a.a.put(DSTR,n);a.uc.mem_write(DENS,b'\1')
            a.a.put(0x20021c7c,4095)
            interval=(480000+n//2)//n
            a.blocks(max(400,interval*4//8))
            self.assertGreaterEqual(len(a.births),3,(n,a.births))
            self.assertEqual([y-x for x,y in zip(a.births,a.births[1:])],[interval]*(len(a.births)-1),n)
