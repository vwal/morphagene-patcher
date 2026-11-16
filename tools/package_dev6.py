"""Package this isolated test build; verify the public checkout stays intact.

Build full into ../build-work and run the full suite into
../validation/unittest.log first. No Git operations or publication occur here.
"""
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
release = source.parent
project = release.parent
public = project / 'morphagene-patcher'
build = release / 'build-work'
validation = release / 'validation'
sys.path.insert(0, str(source))
from mgmod import stock, card, registry

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = json.loads((validation/'release-source-baseline.json').read_text())
for name, digest in baseline.items():
    if sha(public/name) != digest:
        raise SystemExit('Public checkout changed: '+name)
for name in ('mgmod.bin','mg204-full.bin','mg204-full.wav'):
    if sha(release/'rollback-mg204c'/name) != sha(project/'morphagene-dev5-live-options'/name):
        raise SystemExit('Rollback does not match preserved release: '+name)

log = (validation/'unittest.log').read_text()
result = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\s*$', log)
if not result or 'skipped' in log:
    raise SystemExit('Require a complete passing regression run without skips.')
raw = (build/'mg204-full.bin').read_bytes()
if hashlib.sha256(raw).hexdigest() != registry.remix('full')['sha256']:
    raise SystemExit('Raw firmware does not match the reference manifest.')
if (build/'mgmod.bin').read_bytes() != card.card_file(raw):
    raise SystemExit('SD container does not match raw firmware.')
if stock.decode_wav(build/'mg204-full.wav') != raw:
    raise SystemExit('WAV does not decode to raw firmware.')

for name in ('mgmod.bin','mg204-full.bin','mg204-full.wav'):
    shutil.copy2(build/name,release/name)
shutil.copy2(source/'LICENSE',release/'LICENSE')
shutil.copytree(source/'LICENSES',release/'LICENSES',dirs_exist_ok=True)
guide=(source/'docs/DEVELOPMENT_6_UNITY.md').read_text().replace('](INSTALLING.md)','](source/docs/INSTALLING.md)').replace('](DEVELOPMENT_6_HARDWARE_TESTS.md)','](source/docs/DEVELOPMENT_6_HARDWARE_TESTS.md)')
(release/'README.md').write_text(guide+f'''

## Package and verification

- `mgmod.bin`: Development 6 SD updater.
- `mg204-full.wav`: Development 6 audio installer/recovery.
- `mg204-full.bin`: raw Development 6 application.
- `rollback-mg204c/`: exact copies of the released firmware, including its WAV.
- `rollback-dev6-initial/`: first Development 6 firmware for A/B comparison.
- `rollback-dev6-rev2/`: previous test firmware and its metadata.
- `source/`: full test-build source; the published checkout is unchanged.
- `release-to-dev6.patch`: changes from the preserved public source.
- `validation/`: full regression log and artifact/build checks.
- `build-info.json` and `SHA256SUMS.json`: provenance and package hashes.

Validation: **{result[1]} automated tests passed, no skips** in {result[2]} seconds.
Raw firmware, SD container and decoded update WAV agree. Both compatibility
remixes reproduce the same recorded hash. Physical hardware testing remains
pending. Generated firmware includes vendor code and is for your local use.
The copied browser UI/PDFs describe the released baseline; this guide is the
reference for the two new options. No website or PDF release has been published.

Verify the package from this directory:

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
            and not any(part in {'.git','build','build-work','__pycache__','.venv','.toolchain'}
                        for part in p.relative_to(root).parts)
            and p.suffix not in {'.pyc','.pyo'} and p.name != '.DS_Store'}

# Keep license scope/attribution; update hashes for the isolated source only.
provenance_path = source/'license-provenance.json'
provenance = json.loads(provenance_path.read_text())
for name, path in files(source).items():
    if name == 'license-provenance.json': continue
    item=provenance['files'].setdefault(name, {
        'provenance':'added-or-generated; no-sale-with-Make-Noise-exception for our own portions, retained third-party rights for others'})
    item['sha256']=sha(path)
provenance_path.write_text(json.dumps(provenance,indent=2)+'\n')

old={name:public/name for name in baseline}
new=files(source)
diff=[]
for name in sorted(old.keys() | new.keys()):
    a=old[name].read_bytes() if name in old else b''
    b=new[name].read_bytes() if name in new else b''
    if a==b: continue
    try: a=a.decode();b=b.decode()
    except UnicodeDecodeError:
        raise SystemExit('Unexpected binary source change: '+name)
    diff.append(f'diff --git a/{name} b/{name}\n')
    if name not in old:diff.append('new file mode 100644\n')
    if name not in new:diff.append('deleted file mode 100644\n')
    diff.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),
                fromfile='a/'+name if name in old else '/dev/null',
                tofile='b/'+name if name in new else '/dev/null'))
(release/'release-to-dev6.patch').write_text(''.join(diff))
info={
    'version':'mg204+c Development 6 revision 3', 'status':'private hardware-test build',
    'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'base_release':'mg204+c / Development 5',
    'supersedes_dev6_raw_sha256':sha(release/'rollback-dev6-rev2/mg204-full.bin'),
    'raw_image_bytes':len(raw),'raw_image_sha256':sha(release/'mg204-full.bin'),
    'sd_update_sha256':sha(release/'mgmod.bin'),'wav_sha256':sha(release/'mg204-full.wav'),
    'rollback_raw_sha256':sha(release/'rollback-mg204c/mg204-full.bin'),
    'toolchain':'Arm GNU 14.2.rel1 (GCC 14.2.1)',
    'new_options':{'vuni':{'default':0,'behavior':'SHIFT alone >=24000 samples; reset on release; automatic combined-control pickup'},
                   'vctr':{'default':0,'behavior':'+1x at calibrated midpoint; common 48-52% notch and centered native/quantized unity cell; endpoints preserved'}},
    'validation':{'tests':int(result[1]),'skips':0,'seconds':float(result[2]),
                  'sd_and_wav':'both match raw firmware',
                  'public_source_files_unchanged':len(baseline),
                  'hardware':'pending'},
    'limitations':['SHIFT button/gate share firmware input: use vuni with SHIFT input unpatched',
                   'Knob/CV are combined: CV can cancel a gesture or trigger pickup; noon assumes zero CV',
                   'Noon mapping changes CV response; original 1 V/oct behavior is not preserved',
                   'Audible chord/warble/Turing pitch changes remain active'],
    'license_own_additions':'LicenseRef-Morphagene-Extended-No-Sale-1.0',
    'license_upstream':'MIT; notices retained',
    'make_noise_exception':'LICENSE section 5 remains unchanged',
    'published':False,
}
(release/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
manifest={name:sha(path) for name,path in sorted(files(release).items()) if name!='SHA256SUMS.json'}
(release/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=release.with_suffix('.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in [*manifest,'SHA256SUMS.json']:z.write(release/name,release.name+'/'+name)
for name,digest in manifest.items():assert sha(release/name)==digest,name
print(json.dumps({'directory':str(release),'archive':str(archive),
                  'files':len(manifest)+1,'tests':int(result[1]),
                  'raw_sha256':info['raw_image_sha256']},indent=2))
