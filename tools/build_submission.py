#!/usr/bin/env python3
"""Build submission.zip from the canonical submission/ directory.

Competition-specific validation and packaging rules will be added after
the HARNESS_README.md audit.
"""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submission"
DIST = ROOT / "dist"
OUT = DIST / "submission.zip"

DIST.mkdir(exist_ok=True)

if not (SRC / "agent.yaml").exists():
    raise SystemExit("submission/agent.yaml is missing")

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in SRC.rglob("*"):
        if path.is_file():
            zf.write(path, path.relative_to(SRC))

print(f"Built: {OUT}")
print("WARNING: agent.yaml is currently a placeholder; do not submit this archive.")
