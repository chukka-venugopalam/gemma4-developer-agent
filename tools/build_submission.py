#!/usr/bin/env python3
"""Validate and deterministically package submission/ into dist/submission.zip."""
from pathlib import Path
import sys
import zipfile
from validate_submission import validate

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submission"
DIST = ROOT / "dist"
OUT = DIST / "submission.zip"
FIXED_TIME = (2026, 10, 26, 0, 0, 0)


def main() -> None:
    for note in validate(): print(f"PASS: {note}")
    DIST.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            rel = path.relative_to(SRC).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(OUT) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"FAIL: corrupt ZIP member {bad}")
        if "agent.yaml" not in archive.namelist():
            raise SystemExit("FAIL: agent.yaml is not at the ZIP root")
    print(f"PASS: built {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
