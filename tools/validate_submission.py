#!/usr/bin/env python3
"""Validate the Gemma submission directory.

This initial version only checks the repository skeleton. Competition-specific
validation will be added after the full HARNESS_README.md audit.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"

required = [
    SUBMISSION / "agent.yaml",
    SUBMISSION / "configs",
    SUBMISSION / "prompts",
    SUBMISSION / "sub_agents",
    SUBMISSION / "adapters",
    SUBMISSION / "skills",
]

missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]

if missing:
    print("FAIL")
    for item in missing:
        print(f"  missing: {item}")
    raise SystemExit(1)

print("PASS: submission skeleton exists")
print("NOTE: Full harness validation is intentionally deferred until HARNESS_README.md is audited.")
