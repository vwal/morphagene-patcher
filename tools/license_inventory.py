"""Record file provenance without relicensing pre-existing upstream portions."""
from pathlib import Path
import argparse,hashlib,json,subprocess
s=Path(__file__).resolve().parents[1]
fork_derived={
 'modules/splice_thru/splice_thru.S', 'modules/splice_thru/README.md',
 'modules/playback/playback.S', 'modules/reel_banks/reel_banks.S',
}
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--upstream',type=Path,default=s.parents[1]/'upstream',help='Clean checkout of the recorded Briskcat upstream revision')
u=parser.parse_args().upstream.resolve()
skip={'.git','build','__pycache__','.toolchain','.venv'}
files={}
for p in sorted(s.rglob('*')):
    rel=p.relative_to(s)
    if not p.is_file() or skip.intersection(rel.parts) or p.name in {'license-provenance.json','.DS_Store'} or p.suffix in {'.pyc','.pyo'}:continue
    old=u/rel
    if p.read_bytes()==(u/'LICENSE').read_bytes():kind='verbatim-upstream-MIT-notice'
    elif str(rel) in fork_derived:kind='adapted from carlosedp/morphagene-mods; MIT for original portions, no-sale-with-Make-Noise-exception for our additions'
    elif old.is_file() and old.read_bytes()==p.read_bytes():kind='unchanged-upstream-MIT'
    elif old.is_file():kind='modified-from-upstream; MIT for original portions, no-sale-with-Make-Noise-exception for our additions'
    else:kind='added-or-generated; no-sale-with-Make-Noise-exception for our own portions, retained third-party rights for others'
    files[str(rel)]={'provenance':kind,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(s/'license-provenance.json').write_text(json.dumps({
 'upstream_repository':'https://github.com/briskcat/morphagene-mods',
 'additional_upstream':[{
     'repository':'https://github.com/carlosedp/morphagene-mods',
     'commit':'3305b8566641ed24bb176c98e243831bbf1e21f8',
     'notice':'LICENSES/Briskcat-MIT.txt',
     'scope':'Adapted splice play-through and reel-bank code; inspiration for reverse unity notch.',
 }],
 'upstream_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=u,text=True).strip(),
 'own_license':'LicenseRef-Morphagene-Extended-No-Sale-1.0',
 'notice':'File provenance only: new/modified does not imply that all content is original or copyrightable. Existing third-party grants remain. The complete LICENSE controls.',
 'files':files},indent=2)+'\n')
print('Recorded provenance for',len(files),'files.')
