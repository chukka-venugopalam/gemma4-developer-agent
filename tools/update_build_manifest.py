#!/usr/bin/env python3
"""Regenerate docs/BUILD_MANIFEST.csv (excludes itself, .git, caches, and generated dist/)."""
from pathlib import Path
import csv, hashlib
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "BUILD_MANIFEST.csv"
rows = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    if ".git" in rel.parts or "__pycache__" in rel.parts or ".venv" in rel.parts or ".pytest_cache" in rel.parts:
        continue
    if rel.parts[0] == "dist" or rel.as_posix() == "docs/BUILD_MANIFEST.csv":
        continue
    data = path.read_bytes()
    rows.append({"path": rel.as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
    writer.writeheader()
    writer.writerows(rows)
print(f"Updated {OUT.relative_to(ROOT)} with {len(rows)} entries; manifest excludes itself and generated dist/ files.")
