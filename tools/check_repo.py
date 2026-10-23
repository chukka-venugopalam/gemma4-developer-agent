#!/usr/bin/env python3
"""Check repository archive manifests and prevent accidental secrets in a source checkout."""
from __future__ import annotations
import csv, hashlib, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'submissions'/'manifest.csv'
SECRET_PATTERNS=[re.compile(r'(?i)AKIA[0-9A-Z]{16}'),re.compile(r'(?i)AIza[0-9A-Za-z_-]{30,}'),re.compile(r'(?i)KAGGLE_KEY\s*=\s*[^\s#]{8,}')]

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main() -> int:
    issues=[]
    if not MANIFEST.exists(): issues.append('submissions/manifest.csv missing')
    else:
        with MANIFEST.open(newline='',encoding='utf-8') as f:
            for row in csv.DictReader(f):
                name=row.get('file','').strip()
                expected=row.get('sha256','').strip()
                if not name or not expected: continue
                p=ROOT/'submissions'/'archive'/name
                if not p.is_file():
                    # aliases are records rather than duplicate files
                    if row.get('alias_source_name'): continue
                    issues.append(f'manifest file missing: {p.relative_to(ROOT)}')
                elif sha(p)!=expected: issues.append(f'hash mismatch: {p.relative_to(ROOT)}')
    for p in ROOT.rglob('*'):
        if not p.is_file() or '.git' in p.parts or any(part in {'.venv','venv','__pycache__'} for part in p.parts): continue
        if p.name in {'.env','.env.local','kaggle.json'}: issues.append(f'secret-like filename: {p.relative_to(ROOT)}'); continue
        if p.suffix.lower() not in {'.md','.txt','.py','.yaml','.yml','.json','.csv','.toml','.ini','.png','.jpg','.jpeg','.zip','.ipynb','.keep'}: continue
        try: text=p.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        for pat in SECRET_PATTERNS:
            if pat.search(text): issues.append(f'possible secret pattern in {p.relative_to(ROOT)}'); break
    if issues:
        print('REPOSITORY CHECK: FAIL')
        for issue in issues: print(' -',issue)
        return 1
    print('REPOSITORY CHECK: PASS')
    print('Manifest hashes match files stored in submissions/archive/.')
    print('Secret scan is heuristic only; inspect files manually before publishing.')
    return 0
if __name__=='__main__': raise SystemExit(main())
