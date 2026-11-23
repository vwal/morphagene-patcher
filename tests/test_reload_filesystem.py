"""Real mg204 FatFs, mocked sector device: remount, reconnect, write and sync.

The FAT16/FAT32 fixtures are synthesized here; no vendor image or user reel data
is distributed. Only the electrical disk interface is replaced with memory.
"""
import os
import unittest
from tests.arm import *
from tests.test_settings_reload import (arm,call,tick,FS,LIVE,CID,VALID,CARD,DETECT,
    FLAGS,REC,REC_REQUEST,PHASE,RESULT,PENDING,FINISHED,SAMPLES,MOUNT,OPEN,CLOSE,SEEK,
    HASH_READY,DIGEST,SCANNING)

class FatDisk:
    def __init__(self,a,*,fat32=False):
        self.a=a;self.sectors={};self.writes=[];self.reads=[];self.inserted=True
        self.fat32=fat32;self.fat_starts=(32,1056) if fat32 else (1,33)
        self.cid=b'original-card-id'
        boot=bytearray(512);boot[:3]=b'\xeb\x3c\x90';boot[3:11]=b'MGMOD   '
        struct.pack_into('<HBHBHHBHHHII',boot,11,512,4,1,2,512,32768,0xf8,32,32,64,0,0)
        boot[38]=0x29;boot[54:62]=b'FAT16   ';boot[510:]=b'\x55\xaa'
        fat=bytearray(512);struct.pack_into('<4H',fat,0,0xfff8,0xffff,0xffff,0xffff)
        self.root_sector,self.data_sector,self.cluster_sectors=65,97,4
        self.options_cluster,self.reel_cluster=2,3
        if fat32:
            boot[54:62]=bytes(8)
            struct.pack_into('<HBHBHHBHHHII',boot,11,512,1,32,2,0,0,0xf8,0,32,64,0,131072)
            struct.pack_into('<IHHIHH',boot,36,1024,0,0,2,1,6)
            boot[66]=0x29;boot[82:90]=b'FAT32   '
            self.root_sector,self.data_sector,self.cluster_sectors=2080,2080,1
            self.options_cluster,self.reel_cluster=3,4
            fat=bytearray(512);struct.pack_into('<5I',fat,0,0x0ffffff8,*([0x0fffffff]*4))
            self.sectors[32]=self.sectors[1056]=bytes(fat)
        else:self.sectors[1]=self.sectors[33]=bytes(fat)
        self.sectors[0]=bytes(boot)
        self.root=bytearray(512)
        self.file(0,b'OPTIONS TXT',self.options_cluster,b'9 0 0\nvqnt 1\n')
        self.reel=bytes(i%251 for i in range(512))
        self.file(1,b'MG9     WAV',self.reel_cluster,self.reel)
        a.calls.update({0x0802F8CC:self.initialize,0x0802F8E4:self.status,
                        0x0802F8FC:self.read,0x0802F928:self.write,0x0802F954:self.ioctl})
    def file(self,index,name,cluster,data):
        for earlier in range(index):
            if not self.root[earlier*32]:self.root[earlier*32]=0xe5
        self.root[index*32:index*32+11]=name;self.root[index*32+11]=0x20
        struct.pack_into('<HI',self.root,index*32+26,cluster,len(data))
        self.sectors[self.root_sector]=bytes(self.root)
        clusters=max(1,(len(data)+self.cluster_sectors*512-1)//(self.cluster_sectors*512))
        for c in range(cluster,cluster+clusters):
            for start in self.fat_starts:
                width=4 if self.fat32 else 2
                sector=start+c*width//512;fat=bytearray(self.sectors.get(sector,bytes(512)))
                end=0x0fffffff if self.fat32 else 0xffff
                struct.pack_into('<I' if self.fat32 else '<H',fat,c*width%512,c+1 if c<cluster+clusters-1 else end)
                self.sectors[sector]=bytes(fat)
        for offset in range(0,max(1,len(data)),512):
            self.sectors[self.sector(cluster)+offset//512]=data[offset:offset+512].ljust(512,b'\0')
    def sector(self,cluster):return self.data_sector+(cluster-2)*self.cluster_sectors
    def result(self,n=0):self.a.uc.reg_write(UC_ARM_REG_R0,n)
    def initialize(self,a):
        a.uc.mem_write(CID,self.cid);self.result(0 if self.inserted else 3)
    def status(self,a):self.result(0 if self.inserted else 3)
    def read(self,a):
        ptr,sector,count=(a.uc.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
        if not self.inserted:self.result(3);return
        self.reads.append((sector,count))
        a.uc.mem_write(ptr,b''.join(self.sectors.get(i,bytes(512)) for i in range(sector,sector+count)))
        self.result()
    def write(self,a):
        ptr,sector,count=(a.uc.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
        if not self.inserted:self.result(3);return
        for i in range(count):
            self.sectors[sector+i]=bytes(a.uc.mem_read(ptr+i*512,512));self.writes.append(sector+i)
        self.result()
    def ioctl(self,a):self.result(0 if self.inserted else 3)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE for real FatFs')
class ReloadFilesystem(unittest.TestCase):
    def setup_disk(self,*,fat32=False,markers=None):
        from mgmod import stock
        image=stock.load(os.environ['MGMOD_FIRMWARE'])
        a=arm();a.uc.mem_write(0x08020000,image)
        a.calls.clear()  # use real FatFs/name helpers, not the focused mock
        from mgmod.module import branch_w
        for address,name in [(0x08031124,'reload_write'),(OPEN,'reload_open')]:
            a.uc.mem_write(address,branch_w(address,a.syms[name]))
        a.uc.ctl_remove_cache(0x08020000,0x08060000)
        a.uc.mem_write(0x20000000,image[0x27250:0x28400])
        a.put(0x20001040,9);a.put(0x20001064,44)
        a.put(FLAGS,0);a.put(REC,0);a.put(REC_REQUEST,0)
        d=FatDisk(a,fat32=fat32)
        if markers is not None:d.file(2,b'SPLICE9 TXT',8,markers)
        for name,address in [('mount',MOUNT),('open',OPEN),('close',CLOSE),('seek',SEEK),
                             ('write',0x08032688),('sync',0x080326E0)]:a.syms[name]=address
        a.uc.mem_write(0x20028000,b'\0mg9.wav\0')
        self.assertEqual(call(a,'mount',FS,0x20028000,1),0)
        self.assertEqual(call(a,'open',LIVE,0x20028001,3),0)
        self.assertEqual(call(a,'seek',LIVE,96),0)
        a.put(CARD,1);call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(VALID),1)
        self.assertEqual(a.get(HASH_READY),1)
        import hashlib
        self.assertEqual(a.get(LIVE+8),96)
        # Same removal path as stock: the absent driver makes close fail,
        # deregistering the filesystem invalidates its old mount ID.
        d.inserted=False;a.put(DETECT,8192)
        self.assertNotEqual(call(a,'close',LIVE),0)
        self.assertEqual(call(a,'mount',0,0x20028000,0),0)
        a.put(CARD,0)
        d.inserted=True;a.put(DETECT,0);a.put(PHASE,3)
        return a,d

    def test_actual_fatfs_reconnect_and_stock_recording_write_path(self):
        for fat32 in (False,True):
            with self.subTest(fat32=fat32):self.recording_write(fat32)

    def recording_write(self,fat32):
        a,d=self.setup_disk(fat32=fat32)
        d.file(0,b'OPTIONS TXT',d.options_cluster,b'9 0 0\ndens 1\ndstr 0.1\ndryk 2\ndlen 1\n')
        before=dict(d.sectors)
        preserved={addr:bytes(a.uc.mem_read(addr,n)) for addr,n in
                   [(0x20001040,4),(0x20001064,4),(0x20021E64,0x400),(0xD0000000,0x1000)]}
        self.assertEqual(call(a,'reload_service',FS,LIVE),1)
        self.assertEqual(d.sectors,before);self.assertEqual(d.writes,[])
        self.assertEqual(a.get(CARD),0)
        self.assertEqual(a.uc.mem_read(0x2002a61a,2), b'\x00\x00')
        call(a,'reload_commit')
        self.assertEqual(a.uc.mem_read(0x2002a61a,2), b'\x02\x01')
        self.assertEqual(a.get(CARD),1);self.assertEqual(a.get(LIVE+8),96)
        self.assertEqual(a.get(LIVE),FS)
        self.assertEqual(a.get(0x2002a808),480000)
        for addr,data in preserved.items():self.assertEqual(bytes(a.uc.mem_read(addr,len(data))),data)
        # Execute mg204's actual buffered recording save at 0x08023958.
        # It expects FIL at main SP+844, so choose a matching simulated frame.
        a.uc.reg_write(UC_ARM_REG_SP,LIVE-844)
        a.uc.reg_write(UC_ARM_REG_R7,FLAGS)
        a.put(0x2002131C,52);a.put(0x20021318,4)
        a.put(0x20001064,44);a.put(0x20001060,0xD0000000)
        # Actual buffer pointer is loaded at 0x08023b8c; resolve from image.
        pointer=a.get(0x08023B8C)
        a.put(pointer,0xD0000000)
        payload=b'\x01\x23\x45\x67'*4;a.uc.mem_write(0xD0000000,payload)
        a.put(FLAGS,1);a.syms['save']=0x08023958
        a.run('save',[0x0802398A],count=2000000)
        self.assertEqual(a.get(LIVE+8),112)
        self.assertEqual(call(a,'sync',LIVE),0)
        self.assertTrue(d.writes)
        reel_sector,options_sector=d.sector(d.reel_cluster),d.sector(d.options_cluster)
        self.assertEqual(d.sectors[reel_sector][96:112],payload)
        self.assertEqual(d.sectors[options_sector],before[options_sector],'options must not be touched by reel save')
        # Check the remainder of the reel stayed intact.
        self.assertEqual(d.sectors[reel_sector][:96],d.reel[:96])
        self.assertEqual(d.sectors[reel_sector][112:],d.reel[112:])

    def test_actual_fatfs_wrong_card_and_replaced_or_missing_reel(self):
        for kind in ('size','missing'):
            with self.subTest(kind=kind):
                a,d=self.setup_disk()
                if kind=='audio':d.file(1,b'MG9     WAV',d.reel_cluster,b'x'+d.reel[1:])
                elif kind=='cluster':struct.pack_into('<H',d.root,32+26,4)
                elif kind=='size':struct.pack_into('<I',d.root,32+28,400)
                elif kind=='catalog':d.file(3,b'MG1     WAV',10,b'new reel')
                elif kind=='markers':d.file(2,b'SPLICE9 TXT',8,b'0 123\n')
                else:d.root[32]=0xe5
                d.sectors[65]=bytes(d.root);before=dict(d.sectors)
                self.assertEqual(call(a,'reload_service',FS,LIVE),0)
                self.assertEqual(a.get(CARD),0);self.assertEqual(a.get(RESULT),2)
                self.assertEqual(a.get(PENDING),0);self.assertEqual(a.get(LIVE),0)
                self.assertEqual(d.writes,[]);self.assertEqual(d.sectors,before)

    def test_three_cards_accept_file_copies_across_layout_capacity_and_format(self):
        a,d=self.setup_disk(markers=b'0 24000\n24000 48000\n')
        for index in range(3):
            d=FatDisk(a,fat32=bool(index%2));d.cid=bytes([index+1])*16
            d.root[32]=0xe5
            d.file(4,b'MG9     WAV',12,d.reel)  # different directory slot/cluster
            d.file(2,b'SPLICE9 TXT',8,b'0 24000\n24000 48000\n')
            d.file(0,b'OPTIONS TXT',d.options_cluster,f'9 0 0\noctl {index+1}\ndens 1\ndstr {("0.1","8","128")[index]}\n'.encode())
            a.put(PHASE,3);a.put(DETECT,0)
            self.assertEqual(call(a,'reload_service',FS,LIVE),1)
            call(a,'reload_commit')
            self.assertEqual(a.get(CARD),1);self.assertEqual(a.uc.mem_read(0x2002a0f5,1),bytes([index+1]))
            self.assertEqual(a.get(0x2002a808),(480000,6000,375)[index])
            self.assertEqual(a.get(LIVE+8),96);self.assertEqual(d.writes,[])
            reads=len(d.reads);call(a,'reload_service',FS,LIVE)
            self.assertEqual(len(d.reads),reads,'verified digest must stay cached')
            d.inserted=False;call(a,'close',LIVE);call(a,'mount',0,0x20028000,0)
            a.put(CARD,0)

    def test_saved_changes_refresh_snapshot_but_stale_same_size_copy_is_trusted(self):
        a,d=self.setup_disk();call(a,'reload_service',FS,LIVE);call(a,'reload_commit')
        a.uc.mem_write(0x20028100,b'new recording!!!')
        self.assertEqual(call(a,'write',LIVE,0x20028100,16,0x20028200),0)
        self.assertEqual(a.get(HASH_READY),0,'real write core must invalidate digest')
        self.assertEqual(call(a,'sync',LIVE),0)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(HASH_READY),1)
        d.inserted=False;call(a,'close',LIVE);call(a,'mount',0,0x20028000,0);a.put(CARD,0)
        stale=FatDisk(a);stale.cid=b'stale-card-copy!';a.put(PHASE,3)
        call(a,'reload_service',FS,LIVE)
        call(a,'reload_commit')
        self.assertEqual(a.get(RESULT),1);self.assertEqual(a.get(CARD),1)
        self.assertEqual(stale.writes,[])

    def test_splice_truncation_and_printf_invalidate_cached_content(self):
        a,d=self.setup_disk(markers=b'0 24000\n')
        call(a,'reload_service',FS,LIVE);call(a,'reload_commit')
        a.uc.mem_write(0x20028300,b'splice9.txt\0')
        self.assertEqual(call(a,'open',LIVE-552,0x20028300,10),0)
        self.assertEqual(a.get(HASH_READY),0,'truncate/open must invalidate without needing a write')
        # Set it back only to isolate the printf/core-write invalidation check.
        a.put(HASH_READY,1);a.syms['printf']=0x08034804
        a.uc.mem_write(0x20028400,b'0 12000\n\0')
        self.assertGreaterEqual(call(a,'printf',LIVE-552,0x20028400),8)
        self.assertEqual(a.get(HASH_READY),0)
        self.assertEqual(call(a,'close',LIVE-552),0)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(HASH_READY),1)

    def test_snapshot_and_reconnect_do_not_scan_reel_audio(self):
        a,d=self.setup_disk()
        call(a,'reload_service',FS,LIVE);call(a,'reload_commit')
        a.put(HASH_READY,0)
        reads=len(d.reads)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(len(d.reads),reads)
        self.assertEqual(a.get(LIVE+8),96)
        self.assertEqual(a.get(HASH_READY),1)
        a.put(REC_REQUEST,1)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(HASH_READY),0)
        self.assertEqual(len(d.reads),reads)

    def test_success_returns_to_mounted_led_and_can_repeat(self):
        a,d=self.setup_disk();call(a,'reload_service',FS,LIVE);call(a,'reload_commit')
        a.put(SAMPLES,a.get(FINISHED)+19200)
        self.assertEqual(call(a,'reload_led_mask',0xa551),0xa551)
        call(a,'reload_service',FS,LIVE)
        d.inserted=False;a.put(DETECT,8192)
        call(a,'close',LIVE);call(a,'mount',0,0x20028000,0);a.put(CARD,0)
        tick(a,7000,shift=False);tick(a,8000,shift=False)
        call(a,'reload_service',FS,LIVE)
        self.assertEqual(a.get(PHASE),0)
        a.put(0x20001020,14);a.uc.mem_write(0x2002a005,b'\0')
        tick(a,9000);tick(a,15000)
        d.inserted=True;tick(a,15001,present=True)
        self.assertEqual(call(a,'mount',FS,0x20028000,1),0)
        self.assertEqual(call(a,'reload_mounted',0),1)
        call(a,'reload_service',FS,LIVE);call(a,'reload_commit')
        self.assertEqual(a.get(CARD),1);self.assertEqual(a.get(RESULT),1)
        self.assertEqual(d.writes,[])
