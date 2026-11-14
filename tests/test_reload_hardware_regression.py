"""Regressions from the user's GPIOH=0 hardware diagnostic, November 2026."""
import os
import unittest
from tests import test_settings_reload as r
from tests import test_reload_filesystem as fs
from tests.arm import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC

class HardwareReloadRegression(unittest.TestCase):
    def test_one_second_uses_samples_with_detect_stuck_present(self):
        for block_count in (0,3000,6000,0xfffffffe):
            a=r.arm();a.put(r.DETECT,0);a.put(r.SHIFT,2)
            a.put(0x20021394,block_count)
            a.put(r.SAMPLES,100);r.call(a,'reload_tick',4,0,0)
            a.put(r.SAMPLES,48099);r.call(a,'reload_tick',4,0,0)
            self.assertEqual(a.get(r.PHASE),1)
            a.put(r.SAMPLES,48100);r.call(a,'reload_tick',4,0,0)
            self.assertEqual(a.get(r.PHASE),2)
            self.assertEqual(r.call(a,'reload_led_mask',0xa550),0xa551)
            # Failed stock probes mean no readable card yet; stay armed.
            self.assertEqual(r.call(a,'reload_mounted',3),0)
            self.assertEqual(a.get(r.PHASE),2)
            self.assertEqual(r.call(a,'reload_mounted',0),1)
            self.assertEqual(a.get(r.PHASE),3)
            self.assertEqual(a.get(r.OWNED),1)

    def test_early_or_cancelled_mount_keeps_normal_load_and_cannot_rearm_during_it(self):
        for cancellation in ('early','release','knob','record'):
            a=r.arm();r.tick(a,1,present=True)
            if cancellation!='early':r.tick(a,6001,present=True)
            if cancellation=='release':a.put(r.SHIFT,0)
            if cancellation=='knob':a.uc.mem_write(r.MOD+5,b'\1')
            if cancellation=='record':a.put(r.REC,1)
            self.assertEqual(r.call(a,'reload_mounted',0),0)
            self.assertEqual(a.get(r.PHASE),0)
            self.assertEqual(a.get(r.STATE+240),2)
            a.put(r.REC,0);a.uc.mem_write(r.MOD+5,b'\0')
            r.tick(a,12000,present=True);r.tick(a,18000,present=True)
            self.assertEqual(a.get(r.PHASE),0)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE')
    def test_real_timer_led_and_successful_mount_interception_with_gpio_zero(self):
        from tests.test_firmware_integration import images
        h=r.ReloadIntegration();a=h.timer(images()[1])
        for i in range(10):h.timer_tick(a,True,present=True,blocks=i)
        h.timer_tick(a,True,present=True,blocks=6010)
        self.assertEqual(a.get(r.PHASE),2)
        gpio=[]
        a.calls[0x0802b7ac]=lambda a:gpio.append(('off',a.uc.reg_read(UC_ARM_REG_R1)))
        a.calls[0x0802b7b0]=lambda a:gpio.append(('on',a.uc.reg_read(UC_ARM_REG_R1)))
        a.put(0x20001078,r.bits(1000.));a.put(0x20001074,0);a.put(0x20001034,0)
        h.timer_tick(a,True,present=True,blocks=6011)
        self.assertIn(('on',0x800),gpio) # SHIFT serial data bit goes high
        a.syms['mounted']=0x08023136
        for result,target in ((3,0x0802313c),(0,0x08022f7e)):
            a.uc.reg_write(UC_ARM_REG_R0,result)
            a.run('mounted',[0x08022f7e,0x0802313c,0x08023288])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),target)
        self.assertEqual(a.get(r.PHASE),3)
        self.assertEqual(a.get(r.STATE+240),1)
        self.assertEqual(a.get(0x200012e0),0)
        # An ordinary successful mount keeps the original updater/reel route.
        a=h.timer(images()[1]);a.syms['mounted']=0x08023136
        a.uc.reg_write(UC_ARM_REG_R0,0)
        a.run('mounted',[0x08022f7e,0x0802313c,0x08023288])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x08023288)
        self.assertEqual(a.get(r.STATE+240),2)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE')
    def test_real_fatfs_failed_card_is_parked_until_unavailable_then_rearms(self):
        for fat32 in (False,True):
            a,d=fs.ReloadFilesystem().setup_disk(fat32=fat32)
            a.put(r.DETECT,0) # remains zero through removal and reinsertion
            a.put(r.PHASE,5);a.put(r.SAMPLES,4800)
            r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(a.get(r.PHASE),5,'readable rejected card stays parked')
            reads=len(d.reads)
            a.put(r.SAMPLES,9599);r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(len(d.reads),reads,'availability probes are paced')
            d.inserted=False
            a.put(r.SAMPLES,9600);r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(a.get(r.PHASE),0)
            a.put(0x20001020,14)
            r.tick(a,2000,present=True);r.tick(a,8000,present=True)
            self.assertEqual(a.get(r.PHASE),2)
            d.inserted=True
            self.assertEqual(r.call(a,'mount',r.FS,0x20028000,1),0)
            self.assertEqual(r.call(a,'reload_mounted',0),1)
            self.assertEqual(r.call(a,'reload_service',r.FS,r.LIVE),1)
            r.call(a,'reload_commit')
            self.assertEqual(a.get(r.CARD),1)
            self.assertEqual(a.get(r.LIVE+8),96)
            self.assertEqual(a.get(r.RESULT),1)
            self.assertEqual(d.writes,[])

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE')
    def test_media_loss_detected_by_real_reads_with_gpio_still_low(self):
        a,d=fs.ReloadFilesystem().setup_disk()
        # Mounted at insertion, but removed before the staged options read.
        self.assertEqual(r.call(a,'mount',r.FS,0x20028000,1),0)
        a.put(r.STATE+240,1)
        d.inserted=False;a.put(r.DETECT,0)
        r.call(a,'reload_service',r.FS,r.LIVE)
        self.assertEqual(a.get(r.RESULT),2)
        self.assertEqual(a.get(r.PENDING),0)
        self.assertEqual(a.get(r.CARD),0)
        self.assertEqual(d.writes,[])

if __name__=='__main__':unittest.main()
