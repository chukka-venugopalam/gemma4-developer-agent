#!/usr/bin/env python3
"""Register a new candidate ZIP or research report without overwriting history."""
from pathlib import Path
import argparse, csv, hashlib, re, shutil, sys
from datetime import date
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "research" / "submission_archives"
REPORT_DIR = ROOT / "research" / "reports"
MANIFEST = ARCHIVE_DIR / "manifest.csv"
FIELDS = ["archive", "bytes", "sha256", "candidate_or_version", "official_current_harness_compile", "real_gemma_inference", "hosted_score", "notes"]
SLUG = re.compile(r"[^a-z0-9]+")

def slugify(value):
    value = SLUG.sub("-", value.lower()).strip("-")
    if not value: raise ValueError("title or candidate ID must contain letters or numbers")
    return value[:90]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def register_candidate(args):
    src = Path(args.path).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != ".zip": raise ValueError("candidate must be an existing .zip file")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE_DIR / f"submission-{slugify(args.candidate_id)}.zip"
    if target.exists(): raise FileExistsError(f"refusing to overwrite existing candidate: {target.name}")
    shutil.copy2(src, target)
    digest = sha(target)
    rows=[]
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8", newline="") as f: rows=list(csv.DictReader(f))
    rel=target.relative_to(ROOT).as_posix()
    if any(r.get("sha256")==digest for r in rows):
        target.unlink()
        raise ValueError("this exact ZIP hash is already registered; no duplicate archive was added")
    rows.append({"archive":rel,"bytes":str(target.stat().st_size),"sha256":digest,
        "candidate_or_version":args.candidate_id,"official_current_harness_compile":args.compile_status,
        "real_gemma_inference":args.inference_status,"hosted_score":args.score or "UNKNOWN","notes":args.notes or "Registered; score and runtime evidence must be verified separately."})
    with MANIFEST.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f"Registered {rel}\nSHA-256: {digest}")

def register_report(args):
    src=Path(args.path).expanduser().resolve()
    if not src.is_file(): raise ValueError("report file does not exist")
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    target=REPORT_DIR/f"{args.date or date.today().isoformat()}-{slugify(args.title)}{src.suffix.lower()}"
    if target.exists(): raise FileExistsError(f"refusing to overwrite existing report: {target.name}")
    shutil.copy2(src,target)
    print(f"Registered {target.relative_to(ROOT).as_posix()}\nSHA-256: {sha(target)}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="kind",required=True)
    c=sub.add_parser("candidate",help="archive a submission ZIP and append its hash/status to the manifest")
    c.add_argument("path"); c.add_argument("--candidate-id",required=True); c.add_argument("--notes",default="")
    c.add_argument("--compile-status",choices=["PASS","FAIL","BLOCKED","NOT TESTED"],default="NOT TESTED")
    c.add_argument("--inference-status",choices=["PASS","FAIL","BLOCKED","NOT TESTED"],default="NOT TESTED")
    c.add_argument("--score",default="")
    c.set_defaults(func=register_candidate)
    r=sub.add_parser("report",help="copy a research report into dated research/reports/ without overwriting")
    r.add_argument("path"); r.add_argument("--title",required=True); r.add_argument("--date",default="")
    r.set_defaults(func=register_report)
    args=p.parse_args()
    try: args.func(args)
    except Exception as exc: print(f"ERROR: {type(exc).__name__}: {exc}",file=sys.stderr); raise SystemExit(1)
if __name__ == "__main__": main()
