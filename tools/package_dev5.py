"""Package an already built/tested local Development 5; never modify prior builds.

Run from any directory after the commands in docs/TESTING.md. This deliberately
refuses to package a missing/failed/skipped test run or a non-reference image.
"""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile

source = Path(__file__).resolve().parents[1]
release = source.parent
project = release.parent
prior = project / 'morphagene-dev3-quantized'
upstream = project / 'upstream'
sys.path.insert(0, str(source))
from mgmod import card, registry, stock

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = json.loads((release/'dev3-baseline-sha256.json').read_text())
if any(sha(prior/name) != digest for name, digest in baseline.items()):
    raise SystemExit('Development 3 no longer matches the recorded baseline.')

dev4 = project / 'morphagene-dev4-settings-reload'
for name,digest in json.loads((release/'dev4-baseline-sha256.json').read_text()).items():
    if sha(dev4/name)!=digest: raise SystemExit('Development 4 changed: '+name)
log = (source/'build/dev5-unittest.log').read_text()
match = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\s*$', log)
if not match or 'skipped' in log or 'FAIL' in log or 'ERROR' in log:
    raise SystemExit('Run the full regression suite with all firmware baselines before packaging.')

build = source/'build/dev5'
raw = (build/'mg204-full.bin').read_bytes()
if hashlib.sha256(raw).hexdigest() != registry.remix('full')['sha256']:
    raise SystemExit('Raw image does not match the recorded reference hash.')
if (build/'mgmod.bin').read_bytes() != card.card_file(raw):
    raise SystemExit('SD update does not match the raw image.')
if stock.decode_wav(build/'mg204-full.wav') != raw:
    raise SystemExit('Audio update does not decode to the raw image.')

for name in ('mgmod.bin', 'mg204-full.bin', 'mg204-full.wav'):
    shutil.copy2(build/name, release/name)
    (release/'rollback-dev4').mkdir(exist_ok=True)
    shutil.copy2(dev4/name, release/'rollback-dev4'/name)
(release/'validation').mkdir(exist_ok=True)
shutil.copy2(source/'build/dev5-unittest.log', release/'validation/unittest.log')

guide=(source/'docs/DEVELOPMENT_5_LIVE_OPTIONS.md').read_text()
for name in ('INSTALLING.md','TESTING.md'):
    guide=guide.replace(f']({name})',f'](source/docs/{name})')
guide=guide.replace('](../modules/','](source/modules/')
guide=guide.replace('](../LICENSE)','](LICENSE)').replace('](../LICENSING.md)','](source/LICENSING.md)')
shutil.copy2(source/'LICENSE',release/'LICENSE')
shutil.copytree(source/'LICENSES',release/'LICENSES',dirs_exist_ok=True)
(release/'README.md').write_text(guide+'''

## Package contents

- `mgmod.bin`: Development 5 SD update.
- `mg204-full.wav`: audio update/recovery image.
- `mg204-full.bin`: raw application image for inspection.
- `rollback-dev4/`: exact copies of Development 4's update/recovery files.
- `source/`: complete source, tests, guides and local browser builder.
- `dev4-to-dev5.patch`: changes from the preserved Development 4 source.
- `source.patch`: cumulative changes from the recorded upstream commit.
- `validation/`, `build-info.json`, `SHA256SUMS.json`: test results and provenance.
- `dev3-baseline-sha256.json`: all original Development 3 file hashes.

The browser builder is published as mg204+c at https://vwal.github.io/morphagene-patcher/. Generated PDFs are packaged but omitted from text source patches; regenerate them with tools/make_manual.py.
The hash manifest/archive omit disposable `source/build/` and Python caches.
To verify every packaged file, from this folder run:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json
for name, expected in json.loads(Path('SHA256SUMS.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
print('All package hashes verified.')
PY
```
''')

def files(root):
    return {str(p.relative_to(root)):p for p in root.rglob('*') if p.is_file()
            and not any(x in {'.git','build','__pycache__','.toolchain','.venv'}
                        for x in p.relative_to(root).parts)
            and p.name != '.DS_Store' and p.suffix not in {'.pyc','.pyo'}}

def patch(before, after):
    old, new = files(before), files(after)
    # Generated PDFs are rebuilt by tools/make_manual.py, not text diff inputs.
    old={k:v for k,v in old.items() if v.suffix!='.pdf'}
    new={k:v for k,v in new.items() if v.suffix!='.pdf'}
    chunks=[]
    for name in sorted(old.keys() | new.keys()):
        a=old[name].read_text().splitlines(True) if name in old else []
        b=new[name].read_text().splitlines(True) if name in new else []
        if name not in old and not b:
            chunks.append(f'diff --git a/{name} b/{name}\nnew file mode 100644\n'
                          'index 0000000..e69de29\n')
            continue
        if name not in new and not a:
            chunks.append(f'diff --git a/{name} b/{name}\ndeleted file mode 100644\n'
                          'index e69de29..0000000\n')
            continue
        if a == b:
            continue
        chunks.append(f'diff --git a/{name} b/{name}\n')
        if name not in old:
            chunks.append('new file mode 100644\n')
        elif name not in new:
            chunks.append('deleted file mode 100644\n')
        chunks.extend(difflib.unified_diff(a,b,
            fromfile='a/'+name if name in old else '/dev/null',
            tofile='b/'+name if name in new else '/dev/null'))
    return ''.join(chunks)

if subprocess.check_output(['git','status','--porcelain'],cwd=upstream):
    raise SystemExit('Upstream must be clean to generate the cumulative patch.')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip()
(release/'dev4-to-dev5.patch').write_text(patch(dev4/'source',source))
(release/'source.patch').write_text(patch(upstream,source))
info={
    'version':'mg204+c',
    'license_own_additions':'LicenseRef-Morphagene-Extended-No-Sale-1.0',
    'license_upstream':'MIT; original copyright and permission notice retained',
    'license_make_noise_exception':'Section 5: official integration/commercial distribution, authorized channels and official-product resale',
    'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'upstream_commit':commit, 'base_firmware':'mg204',
    'build_toolchain':'Arm GNU 14.2.rel1 (GCC 14.2.1, reference binutils)',
    'raw_image_bytes':len(raw), 'raw_image_sha256':sha(release/'mg204-full.bin'),
    'sd_update_sha256':sha(release/'mgmod.bin'),
    'audio_update_sha256':sha(release/'mg204-full.wav'),
    'rollback_raw_sha256':sha(release/'rollback-dev4/mg204-full.bin'),
    'source_patch_sha256':sha(release/'source.patch'),
    'incremental_patch_sha256':sha(release/'dev4-to-dev5.patch'),
    'validation':{
        'unittest':f'{match[1]} passed, no skips, {match[2]} seconds',
        'firmware_baselines':['official mg204','extended 4x','Development 2','Development 3','Development 4 Full and static Morph Loop'],
        'web':'PASS settings validation and round trips; both browser bundles match local builds',
        'reproducibility':'Both remixes match recorded hashes with Arm GNU 14.2.rel1',
        'packaging':'SD container and decoded update WAV match raw application image',
        'filesystem':'Real mg204 FatFs on synthesized FAT16/FAT32; trusted alternate cards, snapshot invalidation, no preparation scan, recording write and sync verified',
        'development_3':f'All {len(baseline)} baseline files unchanged; rollback copies identical',
        'hardware':'Original arming failure confirmed by diagnostic report: GPIOH13 remained low without a card; 16 samples/audio block. Corrected mount-result/sample-clock build passed user hardware retest: SHIFT arming and changed options applying on insertion without audible playback interruption. Exact latency and all performance combinations remain unmeasured.'
    },
    'gesture':'Hold SHIFT alone for one second with card absent, then insert while held.',
    'success_feedback':'two short SHIFT flashes', 'failure_feedback':'three short SHIFT flashes',
    'card_after_reload':'compatible original or copied card remains mounted on success; fresh current-reel FIL, original file position; failure remains unmounted',
    'reconnect_requirements':'Trusted identical WAVs, splice sidecars and reel-name inventory (user responsibility); file size/live-state checks only; no offline recording or edits',
    'startup_density':'dstr 0.1-128 Genes/sec in 0.1 steps; default 8; startup and explicit settings-only recall, even if unchanged; omitted dstr preserves live rate/phase; recalled next birth waits one new interval, existing voices/playheads retained; knob 0.1-128 with 8 midpoint; writer retains configured value',
    'morph_loop':'Included in Full; mlop 0 default, mlop 1 enables; boot and live reload supported',
    'arming_requires':'CARD_OK=0, no normal load in progress, SHIFT alone for 48000 samples; successful main-loop mount claims insertion before updater/reel load. GPIOH13 is not used; never arms while mounted',
}
(release/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
manifest={name:sha(p) for name,p in sorted(files(release).items()) if name!='SHA256SUMS.json'}
(release/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=release.with_suffix('.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in [*manifest,'SHA256SUMS.json']:
        z.write(release/name,release.name+'/'+name)
print(json.dumps({'release':str(release),'files':len(manifest)+1,
                  'archive':str(archive),'archive_bytes':archive.stat().st_size},indent=2))
