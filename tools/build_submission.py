#!/usr/bin/env python3
"""Build a reproducible submission.zip from the canonical submission/ source."""
from __future__ import annotations
import argparse, hashlib, os, subprocess, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'dist'/'submission.zip')
    ap.add_argument('--skip-static-validation',action='store_true')
    args=ap.parse_args(); src=ROOT/'submission'; out=args.out.resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    if not (src/'agent.yaml').is_file(): raise SystemExit('FAIL: submission/agent.yaml is missing')
    if not args.skip_static_validation:
        r=subprocess.run([sys.executable,str(ROOT/'tools'/'validate_submission.py'),str(src)],text=True)
        if r.returncode: raise SystemExit('FAIL: static validation failed; ZIP not built')
    files=[p for p in src.rglob('*') if p.is_file()]
    # Keep the established archive member order to preserve byte-identical rebuilds
    # where the source content is unchanged. Additional files sort after these entries.
    canonical_order={'agent.yaml':0,'eval_config.yaml':1,'configs/sampling.yaml':2,'prompts/system.md':3}
    files.sort(key=lambda p:(canonical_order.get(p.relative_to(src).as_posix(),99),p.relative_to(src).as_posix()))
    if not files: raise SystemExit('FAIL: source folder is empty')
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            arc=p.relative_to(src).as_posix()
            zi=zipfile.ZipInfo(arc,date_time=(1980,1,1,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=(0o100644 & 0xffff)<<16
            z.writestr(zi,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad: raise SystemExit(f'FAIL: built ZIP CRC issue: {bad}')
    print(f'BUILT: {out}')
    print(f'BYTES: {out.stat().st_size}')
    print('SHA256:',hashlib.sha256(out.read_bytes()).hexdigest())
    print('NOTICE: static package validity only; run the official current competition compiler separately.')
if __name__=='__main__': main()
