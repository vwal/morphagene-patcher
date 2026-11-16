"""Package isolated Dev7; verify public and hardware-tested Dev6 stay intact."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import re
import shutil
import sys
import zipfile

source = Path(__file__).resolve().parents[1]
release, project = source.parent, source.parent.parent
public, prior = project/'morphagene-patcher', project/'morphagene-dev6-unity'
build, validation = release/'build-work', release/'validation'
sys.path.insert(0,str(source))
from mgmod import stock, card, registry

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def files(root):
    return {str(p.relative_to(root)):p for p in root.rglob('*') if p.is_file()
            and not any(part in {'.git','build','build-work','__pycache__','.venv','.toolchain'}
                        for part in p.relative_to(root).parts)
            and p.suffix not in {'.pyc','.pyo'} and p.name != '.DS_Store'}

baseline=json.loads((validation/'release-source-baseline.json').read_text())
prior_baseline=json.loads((validation/'dev6-baseline.json').read_text())
for name,digest in baseline.items():
    if sha(public/name)!=digest:raise SystemExit('Published source changed: '+name)
for name,digest in prior_baseline.items():
    if sha(prior/name)!=digest:raise SystemExit('Tested Development 6 changed: '+name)
for name in ('mgmod.bin','mg204-full.bin','mg204-full.wav'):
    if sha(release/'rollback-dev6-r3'/name)!=sha(prior/name):
        raise SystemExit('Development 6 rollback mismatch: '+name)

log=(validation/'unittest.log').read_text()
result=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\s*$',log)
if not result or 'skipped' in log:raise SystemExit('Require full passing tests with no skips.')
if 'PASS Dev7' not in (validation/'web-tests.log').read_text():
    raise SystemExit('Require the Dev7 browser option tests.')
raw=(build/'mg204-full.bin').read_bytes()
if hashlib.sha256(raw).hexdigest()!=registry.remix('full')['sha256']:
    raise SystemExit('Reference build hash mismatch.')
if (build/'mgmod.bin').read_bytes()!=card.card_file(raw):
    raise SystemExit('SD container differs from raw image.')
if stock.decode_wav(build/'mg204-full.wav')!=raw:
    raise SystemExit('WAV payload differs from raw image.')
for name in ('mgmod.bin','mg204-full.bin','mg204-full.wav'):
    shutil.copy2(build/name,release/name)
shutil.copy2(source/'LICENSE',release/'LICENSE')
shutil.copytree(source/'LICENSES',release/'LICENSES',dirs_exist_ok=True)

guide=(source/'docs/DEVELOPMENT_7_PRESETS.md').read_text()
for old,new in [('](INSTALLING.md)','](source/docs/INSTALLING.md)'),
                ('](DEVELOPMENT_6_UNITY.md)','](source/docs/DEVELOPMENT_6_UNITY.md)'),
                ('](../web/index.html)','](source/web/index.html)')]:guide=guide.replace(old,new)
(release/'README.md').write_text(guide+f'''

## Package verification

**{result[1]} automated firmware tests passed, no skips**, in {result[2]} seconds.
Browser option tests passed. The raw image, SD updater container and decoded
WAV agree. The private web patch data reproduces the recorded firmware.
Physical hardware testing of Development 7 remains pending.

- `source/`: complete experimental source, editor and guides.
- `rollback-dev6-r3/`: exact copies of the tested Development 6 firmware.
- `rollback-mg204c/`: original published firmware.
- `rollback-dev6-initial/`: historical regression fixture.
- `dev6-to-dev7.patch`: changes from Development 6 revision 3.
- `release-to-dev7.patch`: changes from published mg204+c.
- `validation/`: test logs and preserved baseline hashes.
- `build-info.json`, `SHA256SUMS.json`: provenance and package hashes.

The published checkout and all recorded Development 6 files are unchanged.
Generated firmware contains vendor code and is packaged for your local testing.
''')

provenance_path=source/'license-provenance.json'
provenance=json.loads(provenance_path.read_text())
for name,path in files(source).items():
    if name=='license-provenance.json':continue
    item=provenance['files'].setdefault(name,{
        'provenance':'added-or-generated; no-sale-with-Make-Noise-exception for our own portions, retained third-party rights for others'})
    item['sha256']=sha(path)
provenance_path.write_text(json.dumps(provenance,indent=2)+'\n')

def patch(old,new,destination):
    diff=[]
    for name in sorted(old.keys()|new.keys()):
        a=old[name].read_bytes() if name in old else b''
        b=new[name].read_bytes() if name in new else b''
        if a==b:continue
        try:a=a.decode();b=b.decode()
        except UnicodeDecodeError:raise SystemExit('Unexpected binary source change: '+name)
        diff.append(f'diff --git a/{name} b/{name}\n')
        if name not in old:diff.append('new file mode 100644\n')
        if name not in new:diff.append('deleted file mode 100644\n')
        diff.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),
             fromfile='a/'+name if name in old else '/dev/null',
             tofile='b/'+name if name in new else '/dev/null'))
    destination.write_text(''.join(diff))

patch({n:public/n for n in baseline},files(source),release/'release-to-dev7.patch')
patch(files(prior/'source'),files(source),release/'dev6-to-dev7.patch')
info={
    'version':'mg204+c Development 7 experimental',
    'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'base':'Development 6 revision 3; user confirmed hardware tests passed',
    'base_raw_sha256':sha(prior/'mg204-full.bin'),
    'raw_image_bytes':len(raw),'raw_image_sha256':sha(release/'mg204-full.bin'),
    'sd_update_sha256':sha(release/'mgmod.bin'),'wav_sha256':sha(release/'mg204-full.wav'),
    'toolchain':'Arm GNU 14.2.rel1 (GCC 14.2.1)',
    'new_options':{key:{'default':'omitted/off','range':rng} for key,rng in
                   [('mpos','0-100 integer percent'),('gpos','0-100 integer percent'),
                    ('spos','0-100 integer percent'),('splc','1-300, within loaded reel')]},
    'recall':'Explicit values reapply at normal load and settings-only reload; omitted values preserve live state; configured values only are persisted',
    'validation':{'tests':int(result[1]),'skips':0,'seconds':float(result[2]),
                  'sd_and_wav':'match raw','browser':'passed',
                  'public_files_unchanged':len(baseline),
                  'dev6_files_unchanged':len(prior_baseline),'hardware':'pending'},
    'license_own_additions':'LicenseRef-Morphagene-Extended-No-Sale-1.0',
    'license_upstream':'MIT; notices retained',
    'make_noise_exception':'LICENSE section 5 unchanged','published':False,
}
(release/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
manifest={name:sha(path) for name,path in sorted(files(release).items()) if name!='SHA256SUMS.json'}
(release/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=release.with_suffix('.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in [*manifest,'SHA256SUMS.json']:z.write(release/name,release.name+'/'+name)
for name,digest in manifest.items():assert sha(release/name)==digest,name
print(json.dumps({'directory':str(release),'archive':str(archive),'files':len(manifest)+1,
                  'tests':int(result[1]),'raw_sha256':info['raw_image_sha256']},indent=2))
