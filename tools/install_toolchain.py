#!/usr/bin/env python3
"""Install the pinned Arm GNU toolchain locally; never changes system packages."""
import argparse, hashlib, json, os, platform, subprocess, sys, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,help='use an already-downloaded archive (still SHA-256 checked)')
    p.add_argument('--destination',type=Path,default=ROOT/'.toolchain')
    p.add_argument('--print-bin',action='store_true',help='print only the bin path on stdout, e.g. for GITHUB_PATH')
    args=p.parse_args()
    machine=platform.machine().lower()
    if machine=='amd64':machine='x86_64'
    if platform.system()=='Linux' and machine=='arm64':machine='aarch64'
    pins=json.loads((ROOT/'tools/toolchain.json').read_text())
    key=platform.system()+'-'+machine
    if key not in pins['platforms']:p.error(f'no pinned toolchain for {key}')
    spec=pins['platforms'][key]
    target=args.destination.resolve()/spec['filename'].removesuffix('.tar.xz')
    stamp=target/'.mgmod-archive-sha256'
    if not (stamp.exists() and stamp.read_text().strip()==spec['sha256']):
        args.destination.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            archive=args.archive or Path(tmp)/spec['filename']
            if not args.archive:
                print(f'Downloading Arm GNU {pins["release"]} for {key}',file=sys.stderr)
                urllib.request.urlretrieve(spec['url'],archive)
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest!=spec['sha256']:p.error(f'archive SHA-256 mismatch: {digest}')
            # Only the archive whose exact digest is pinned above is extracted.
            subprocess.run(['tar','-xf',str(archive),'-C',str(args.destination.resolve())],check=True)
            stamp.write_text(spec['sha256']+'\n')
    if not (target/'bin/arm-none-eabi-as').is_file():p.error('toolchain installation is incomplete')
    if args.print_bin:print(target/'bin')
    else:print(f'Installed verified Arm GNU {pins["release"]}\nAdd to PATH: {target / "bin"}')

if __name__=='__main__':main()
