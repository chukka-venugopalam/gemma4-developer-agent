#!/usr/bin/env python3
"""Check repository inventories, artifact hashes, submission ZIPs, and basic secret patterns."""
from pathlib import Path
import csv
import hashlib
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROBLEMS = []


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require_file(rel: str) -> Path | None:
    path = ROOT / rel
    if not path.is_file():
        PROBLEMS.append(f"missing required file: {rel}")
        return None
    return path


for required in [
    "README.md",
    "docs/NEXT_STEPS.md",
    "docs/PROJECT_STATUS.md",
    "docs/RESEARCH_PROGRESS.md",
    "submission/agent.yaml",
    "submissions/manifest.csv",
    "research/artifact_manifest.csv",
    "research/evidence/screenshots/index.csv",
    "evaluation/results/score_observations.csv",
    "docs/BUILD_MANIFEST.csv",
]:
    require_file(required)

# Submission ZIP inventory and hashes.
submission_manifest = ROOT / "submissions" / "manifest.csv"
if submission_manifest.exists():
    rows = read_csv(submission_manifest)
    seen_hashes = set()
    current_flags = []
    for row in rows:
        rel = row.get("archive_path", "")
        path = ROOT / rel
        digest = row.get("sha256", "")
        if digest in seen_hashes:
            PROBLEMS.append(f"duplicate candidate SHA-256 row: {digest}")
        seen_hashes.add(digest)
        if not path.is_file():
            PROBLEMS.append(f"missing archived ZIP: {rel}")
            continue
        if sha256(path) != digest:
            PROBLEMS.append(f"submission hash mismatch: {rel}")
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    PROBLEMS.append(f"corrupt ZIP member {bad}: {rel}")
                if "agent.yaml" not in archive.namelist():
                    PROBLEMS.append(f"archive has no root agent.yaml: {rel}")
        except Exception as exc:
            PROBLEMS.append(f"invalid ZIP {rel}: {exc}")
        if row.get("current_candidate", "").lower() == "yes":
            current_flags.append(row)
    if len(current_flags) != 1:
        PROBLEMS.append(f"expected exactly one current_candidate=yes row, found {len(current_flags)}")

# Research artifact manifest.
artifact_manifest = ROOT / "research" / "artifact_manifest.csv"
if artifact_manifest.exists():
    for row in read_csv(artifact_manifest):
        rel = row.get("path", "")
        path = ROOT / rel
        if not path.is_file():
            PROBLEMS.append(f"missing research artifact: {rel}")
            continue
        if sha256(path) != row.get("sha256", ""):
            PROBLEMS.append(f"research artifact hash mismatch: {rel}")

# Screenshot evidence index includes original filenames separately from stored paths.
screenshot_index = ROOT / "research" / "evidence" / "screenshots" / "index.csv"
if screenshot_index.exists():
    for row in read_csv(screenshot_index):
        rel = row.get("repository_path", "")
        path = ROOT / rel
        if not path.is_file():
            PROBLEMS.append(f"missing screenshot evidence: {rel}")
            continue
        if str(path.stat().st_size) != row.get("bytes", ""):
            PROBLEMS.append(f"screenshot size mismatch: {rel}")
        if sha256(path) != row.get("sha256", ""):
            PROBLEMS.append(f"screenshot hash mismatch: {rel}")

# Observed results must point to existing screenshot evidence; blank candidate hashes are allowed.
score_log = ROOT / "evaluation" / "results" / "score_observations.csv"
if score_log.exists():
    known_hashes = {r.get("sha256", "") for r in read_csv(submission_manifest)} if submission_manifest.exists() else set()
    for row in read_csv(score_log):
        shot = row.get("screenshot_path", "")
        if shot and not (ROOT / shot).is_file():
            PROBLEMS.append(f"score observation references missing screenshot: {shot}")
        candidate_hash = row.get("candidate_sha256", "")
        if candidate_hash and candidate_hash not in known_hashes:
            PROBLEMS.append(f"score observation references unknown candidate hash: {candidate_hash}")

# Build manifest checks every project file except itself, Git metadata, caches, and generated dist output.
build_manifest = ROOT / "docs" / "BUILD_MANIFEST.csv"
if build_manifest.exists():
    listed = {}
    for row in read_csv(build_manifest):
        rel = row.get("path", "")
        path = ROOT / rel
        listed[rel] = row
        if not path.is_file():
            PROBLEMS.append(f"build manifest path missing: {rel}")
            continue
        if str(path.stat().st_size) != row.get("bytes", ""):
            PROBLEMS.append(f"build manifest size mismatch: {rel}")
        if sha256(path) != row.get("sha256", ""):
            PROBLEMS.append(f"build manifest hash mismatch: {rel}")
    expected = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if ".git" in rel.parts or "__pycache__" in rel.parts or ".venv" in rel.parts or ".pytest_cache" in rel.parts:
            continue
        if rel.parts[0] == "dist" or rel.as_posix() == "docs/BUILD_MANIFEST.csv":
            continue
        expected.add(rel.as_posix())
    for rel in sorted(expected - set(listed)):
        PROBLEMS.append(f"file missing from build manifest: {rel}")
    for rel in sorted(set(listed) - expected):
        PROBLEMS.append(f"stale build manifest entry: {rel}")

# High-confidence secret patterns in ordinary text. Raw bundles/logs/screenshots are reviewed separately.
secret_patterns = [
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"AIza[0-9A-Za-z_-]{30,}",
]
skip_parts = {"bundles", "archive", "screenshots", "raw"}
for path in ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".py", ".yaml", ".yml", ".json", ".csv"}:
        continue
    rel = path.relative_to(ROOT)
    if any(part in skip_parts for part in rel.parts):
        continue
    content = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in secret_patterns:
        if re.search(pattern, content):
            PROBLEMS.append(f"possible credential pattern in {rel} ({pattern})")

if PROBLEMS:
    print("FAIL:")
    for problem in PROBLEMS:
        print("-", problem)
    sys.exit(1)

print("PASS: required files, submission hashes/CRCs, research artifact hashes, screenshot index, score references, build manifest, and basic secret-pattern scan.")
print("NOTE: inspect raw bundles, logs, and screenshots manually before publishing; this script does not validate the official competition harness.")
