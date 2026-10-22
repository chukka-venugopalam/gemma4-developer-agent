#!/usr/bin/env python3
"""Register a new submission ZIP or research file without overwriting prior artifacts."""
from __future__ import annotations
import argparse, csv, hashlib, re, shutil, zipfile
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def slug(s: str) -> str:
    return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',s.lower())).strip('-')[:80] or 'artifact'
def read_csv(path: Path):
    if not path.exists(): return []
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kind',choices=['submission','research','prompt','log'],required=True)
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--date',default=date.today().isoformat())
    ap.add_argument('--label',required=True)
    ap.add_argument('--status',default='received')
    ap.add_argument('--score',default='')
    ap.add_argument('--notes',default='')
    args=ap.parse_args(); src=args.source.resolve()
    if not src.is_file(): raise SystemExit(f'FAIL: source file not found: {src}')
    h=digest(src)
    if args.kind=='submission':
        if src.suffix.lower()!='.zip': raise SystemExit('FAIL: submissions must be ZIP files')
        try:
            with zipfile.ZipFile(src) as z:
                bad=z.testzip()
                if bad: raise SystemExit(f'FAIL: ZIP CRC failed at {bad}')
                if 'agent.yaml' not in z.namelist(): raise SystemExit('FAIL: agent.yaml must be at ZIP root')
        except zipfile.BadZipFile: raise SystemExit('FAIL: invalid ZIP archive')
        dest_dir=ROOT/'submissions/archive'; manifest=ROOT/'submissions/manifest.csv'
        fields=['archive_path','sha256','bytes','members','source_names','source_paths','aliases','current_candidate','notes']
        rows=read_csv(manifest)
        existing=next((r for r in rows if r.get('sha256')==h),None)
        if existing:
            names=set(v.strip() for v in existing.get('source_names','').split(' | ') if v.strip()); names.add(src.name)
            paths=set(v.strip() for v in existing.get('source_paths','').split(' | ') if v.strip()); paths.add(str(src))
            existing['source_names']=' | '.join(sorted(names)); existing['source_paths']=' | '.join(sorted(paths)); existing['aliases']=str(len(names))
            write_csv(manifest,fields,rows)
            print(f'DUPLICATE: identical bytes already stored at {existing["archive_path"]}; source alias recorded.')
            destination=ROOT/existing['archive_path']
        else:
            dest_dir.mkdir(parents=True,exist_ok=True)
            destination=dest_dir/f'{args.date}__{slug(args.label)}.zip'
            if destination.exists(): destination=dest_dir/f'{args.date}__{slug(args.label)}__{h[:8]}.zip'
            shutil.copy2(src,destination)
            with zipfile.ZipFile(destination) as z: members=len(z.namelist())
            rows.append({'archive_path':destination.relative_to(ROOT).as_posix(),'sha256':h,'bytes':destination.stat().st_size,'members':members,'source_names':src.name,'source_paths':str(src),'aliases':1,'current_candidate':'no','notes':f'{args.status}; score={args.score or "unknown"}; {args.notes}'})
            write_csv(manifest,fields,rows)
    else:
        dest_dir=ROOT/({'research':'research/reports','prompt':'research/prompts','log':'evaluation/logs/new'}[args.kind])
        manifest=ROOT/'research/artifact_manifest.csv'
        fields=['artifact_id','date_added','kind','path','source_filename','sha256','evidence_level','summary','related_experiment','status']
        rows=read_csv(manifest)
        existing=next((r for r in rows if r.get('sha256')==h),None)
        if existing:
            print(f'DUPLICATE: identical artifact already registered at {existing.get("path")}; no second copy created.')
            destination=ROOT/existing['path']
        else:
            dest_dir.mkdir(parents=True,exist_ok=True)
            ext=src.suffix.lower() or '.bin'; destination=dest_dir/f'{args.date}__{slug(args.label)}{ext}'
            if destination.exists(): destination=dest_dir/f'{args.date}__{slug(args.label)}__{h[:8]}{ext}'
            shutil.copy2(src,destination)
            rows.append({'artifact_id':f'RES-{h[:10]}','date_added':args.date,'kind':args.kind,'path':destination.relative_to(ROOT).as_posix(),'source_filename':src.name,'sha256':h,'evidence_level':'needs review','summary':args.notes or args.label,'related_experiment':'','status':args.status})
            write_csv(manifest,fields,rows)
    print(f'REGISTERED: {destination.relative_to(ROOT)}\nSHA256: {h}\nBYTES: {destination.stat().st_size}')
if __name__=='__main__': main()
