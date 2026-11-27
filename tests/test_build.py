import struct, unittest
from mgmod import card, ledger, registry
from mgmod.module import Module, branch_w

def mod(name,**kw):return Module(name=name,title=name,status='test',**kw)
def image(length=card.MIN_IMAGE):
    b=bytearray(length);struct.pack_into('<II',b,0,0x20030000,0x08021415);return bytes(b)

class BuildChecks(unittest.TestCase):
    def test_bundled_remixes_have_no_collisions(self):
        for name in registry.all_remixes():ledger.check(registry.remix(name)['modules'])
    def test_only_an_explicit_replacement_can_wrap_an_existing_hook(self):
        owner = mod('owner', hooks=[(0x08020040, '0123456789ab', 'first')])
        next_hook = [(0x08020040, '12345678', 'second')]
        valid = mod('wrap', hooks=next_hook, replaces_hooks={0x08020040: 'owner'})
        ledger.check([owner, valid])
        for invalid in (mod('wrap', hooks=next_hook), valid,
                        mod('wrap', hooks=next_hook, replaces_hooks={0x08020040: 'wrong'}),
                        mod('wrap', hooks=[(0x08020040, '00'*8, 'second')],
                            replaces_hooks={0x08020040: 'owner'})):
            with self.assertRaises(ValueError):
                ledger.check([invalid] if invalid is valid else [owner, invalid])

    def test_cross_category_memory_collisions(self):
        for offset,address,kind in [(0,0x2002A000,'mod_bytes'),(4,0x2002A0F4,'settings')]:
            claim={'mod_bytes':[(offset,offset)]} if kind=='mod_bytes' else {'settings':[offset]}
            with self.assertRaises(ValueError):ledger.check([mod('a',**claim),mod('b',ram=[(address,address)])])
    def test_adjacent_memory_is_allowed(self):
        ledger.check([mod('a',mod_bytes=[(0,3)]),mod('b',ram=[(0x2002A004,0x2002A007)])])
    def test_bad_claims_and_duplicates(self):
        for modules in [[mod('a'),mod('a')],[mod('a',mod_bytes=[(240,244)])],
                        [mod('a',settings=[16])],[mod('a',ram=[(0x2002B800,0x2002B803)])]]:
            with self.assertRaises(ValueError):ledger.check(modules)
    def test_card_validates_vectors_and_size(self):
        card.card_file(image());card.card_file(image(0x40000))
        for b in [bytes(8),image()+b'\0',image(0x40004),image()[:4]+struct.pack('<I',0x08060001)+image()[8:]]:
            with self.assertRaises(ValueError):card.card_file(b)
    def test_branch_range_errors(self):
        with self.assertRaises((ValueError,AssertionError)):branch_w(0x08020000,0x10000000)
