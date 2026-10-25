#!/usr/bin/env python3
"""Check canonical submission, archive manifest hashes, and obvious secrets."""
from pathlib import Path
import csv, hashlib, re, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_submission import validate

MANIFEST = ROOT / "research" / "submission_archives" / "manifest.csv"
SECRET_PATTERNS = [
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("GitHub token", re.compile(r"(?:ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("Kaggle token assignment", re.compile(r"(?i)KAGGLE_API_TOKEN\s*[:=]\s*[\"']?[A-Za-z0-9_=-]{24,}")),
]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "dist"}
BINARY_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".safetensors"}

def check_manifest():
    if not MANIFEST.is_file():
        raise ValueError("missing research/submission_archives/manifest.csv")
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        rel = row.get("archive", "")
        path = (ROOT / rel).resolve()
        if ROOT.resolve() not in path.parents:
            raise ValueError(f"manifest path escapes repository: {rel}")
        if not path.is_file():
            raise ValueError(f"manifest archive missing: {rel}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != row.get("sha256"):
            raise ValueError(f"hash mismatch for {rel}: expected {row.get('sha256')}, got {actual}")
    return len(rows)

def scan_secrets():
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts) or p.suffix.lower() in BINARY_SUFFIXES:
            continue
        try: text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError): continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text): hits.append(f"{p.relative_to(ROOT)}: possible {label}")
    return hits

def main():
    for note in validate(): print(f"PASS: submission: {note}")
    n = check_manifest()
    print(f"PASS: submission archive manifest hashes ({n} records)")
    hits = scan_secrets()
    if hits:
        print("WARN: possible secret patterns found; review before publishing:")
        for hit in hits: print(f"  {hit}")
        raise SystemExit(2)
    print("PASS: no configured high-confidence secret patterns detected")

if __name__ == "__main__": main()
