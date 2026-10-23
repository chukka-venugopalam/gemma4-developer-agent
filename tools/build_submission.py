#!/usr/bin/env python3
"""Build a deterministic competition ZIP from submission/ after static validation."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submission"
DEFAULT_OUT = ROOT / "dist" / "submission.zip"
FIXED_TIME = (2026, 10, 23, 0, 0, 0)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build(out: Path) -> Path:
    validate = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_submission.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    print(validate.stdout, end="")
    if validate.stderr:
        print(validate.stderr, file=sys.stderr, end="")
    if validate.returncode != 0:
        raise SystemExit("Build aborted: static validation failed.")

    paths = sorted(p for p in SRC.rglob("*") if p.is_file())
    if not paths:
        raise SystemExit("Build aborted: submission/ contains no files.")
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in paths:
            rel = path.relative_to(SRC).as_posix()
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(out, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"Build failed ZIP integrity: {bad}")
        if "agent.yaml" not in zf.namelist():
            raise SystemExit("Build failed: agent.yaml not at archive root")
    print(f"BUILT: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    print(f"BYTES: {out.stat().st_size}")
    print(f"SHA256: {digest(out)}")
    print("NOTE: deterministic ZIP + local static checks do not prove official Kaggle compilation.")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
