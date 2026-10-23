#!/usr/bin/env python3
"""Copy a new research/submission/evidence artifact into the repo and register its provenance."""
from __future__ import annotations
import argparse, csv, hashlib, shutil
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def append_csv(path:Path, fields:list[str], row:dict):
 path.parent.mkdir(parents=True,exist_ok=True)
 existed=path.exists() and path.stat().st_size>0
 with path.open('a',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields)
  if not existed: w.writeheader()
  w.writerow(row)

def main()->int:
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--kind',choices=['submission','research','evidence','bundle'],required=True)
 p.add_argument('--source',type=Path,required=True)
 p.add_argument('--destination',required=True,help='Path relative to repository root')
 p.add_argument('--date',default=date.today().isoformat())
 p.add_argument('--title',required=True)
 p.add_argument('--status',default='collected; not independently evaluated')
 p.add_argument('--score',default='')
 p.add_argument('--notes',default='')
 p.add_argument('--overwrite',action='store_true')
 a=p.parse_args()
 src=a.source.expanduser().resolve()
 if not src.is_file(): p.error(f'source file not found: {src}')
 dst=(ROOT/a.destination).resolve()
 try: dst.relative_to(ROOT.resolve())
 except ValueError: p.error('destination must remain inside the repository')
 if dst.exists() and not a.overwrite: p.error(f'destination already exists: {dst.relative_to(ROOT)} (use --overwrite intentionally)')
 dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
 h=sha(dst); n=dst.stat().st_size
 if a.kind=='submission':
  if dst.parent != (ROOT/'submissions/archive').resolve(): p.error('submission destinations must be directly inside submissions/archive/')
  append_csv(ROOT/'submissions/manifest.csv', ['artifact_id','file','alias_source_name','sha256','bytes','date_label','status','score','notes'], {
   'artifact_id':f'ADD-{a.date.replace("-","")}-{h[:8]}','file':dst.name,'alias_source_name':'','sha256':h,'bytes':n,'date_label':a.date,'status':a.status,'score':a.score,'notes':(a.title+'; '+a.notes).strip('; ')})
 else:
  append_csv(ROOT/'research/artifact_manifest.csv',['date','kind','title','path','sha256','bytes','status','notes'],{
   'date':a.date,'kind':a.kind,'title':a.title,'path':dst.relative_to(ROOT).as_posix(),'sha256':h,'bytes':n,'status':a.status,'notes':a.notes})
 print(f'REGISTERED: {dst.relative_to(ROOT)}')
 print(f'SHA256: {h}')
 print(f'BYTES: {n}')
 return 0
if __name__=='__main__': raise SystemExit(main())
