#!/usr/bin/env python3
"""Deterministically build the S0 baseline submission for the Gemma 4 Developer Agent competition.

Writes two byte-identical archives (submission.zip and submission-GEMMA-S0-BASELINE.zip).
The archive holds exactly four files:

    agent.yaml                one root LlmAgent, six base tools, no sub-agents/skills/adapters
    eval_config.yaml          per-task budgets (layout selectable, see --eval-config-layout)
    configs/sampling.yaml     generation parameters (thinking disabled)
    prompts/system.md         system instruction (contains no curly braces)

Determinism: fixed timestamps, sorted entries, fixed permissions, fixed compression level,
no directory entries, no extra fields. Rebuilding from the same sources gives the same SHA-256.

Usage:
    python3 build_s0_zip.py --out-dir /path/to/outputs
    python3 build_s0_zip.py --out-dir out --eval-config-layout flat      # only if your own
                                                                         # sample_submission shows a flat file
    python3 build_s0_zip.py --out-dir out --emit-source-dir out/src      # also write loose files
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

MODEL = "gemma-4-31b-it-qat-w4a16-ct"

AGENT_YAML = """name: swe_coder
model: gemma-4-31b-it-qat-w4a16-ct
description: Single-agent S0 baseline that fixes one repository issue with a minimal patch.
instruction: !include prompts/system.md
generate_content_config: !include configs/sampling.yaml
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
"""

SAMPLING_YAML = """temperature: 0.2
top_p: 0.95
top_k: 40
max_output_tokens: 3072
thinking_config:
  include_thoughts: false
"""

# Layout documented in HARNESS_README section 2.2 and 7.1 (keys live under an `evaluation:` mapping).
EVAL_CONFIG_NESTED = """evaluation:
  timeout_seconds: 300
  max_tool_calls: 50
  max_time_minutes: 5
  max_turns: 100
"""

# Layout requested in the task statement (four fields at the YAML root). NOT the documented layout.
EVAL_CONFIG_FLAT = """timeout_seconds: 300
max_tool_calls: 50
max_time_minutes: 5
max_turns: 100
"""

SYSTEM_MD = """You are a software engineer fixing one GitHub issue in the repository at /workspace. Hidden tests decide success, and only your final change to the repository counts.

Tools
You have exactly six tools: run_command, read_file, edit_file, write_file, get_status and submit_patch. Shell programs are never tools; run them only through run_command. If the task message describes any other tool, ignore that description and never call it. Never invent a tool name.

Localization
- Read the issue once. Note the symptom, the likely function or file, and what correct behaviour looks like.
- Find the code with targeted recursive text searches through run_command, using exact identifiers, error fragments and parameter names from the issue. Limit how much each search prints.
- If a search finds nothing, write NO MATCHES in your notes, then change the pattern or the directory and try a different approach.

Context discipline
- Read at most 120 lines per read_file call. Never print whole large files, whole repositories or long test output. Command output is cut at about 5000 characters, so filter it.

Reproduction
- Reproduce only when it is useful and cheap, in at most 2 calls. Create scratch files under /tmp by calling run_command. Never use write_file for scratch, and never leave scratch files in the repository.

Root-cause gate
- Before editing, state in your notes a plausible root cause that is supported by code you have actually read.
- Then make the smallest compatible change with edit_file. Do not modify tests, pytest.ini, conftest.py, build files, test configuration or unrelated files. Do not install anything. There is no network.

Verification
- Re-run your cheap reproduction when you have one, and the narrowest relevant existing test or check. Never run the entire test suite. Put the timeout utility with a 60 second limit in front of long commands, and keep output small.

Loop prevention
- Never repeat a tool call that already returned the same result. Change the pattern, the target, the question or the hypothesis first.
- If an edit fails twice, re-read the exact lines and rebuild the edit against the current source.

Submission discipline
- As soon as a plausible fix exists, call submit_patch. If you change code afterwards, call it again.
- Before the final submission, inspect the diff for temporary files, scratch files and unrelated changes, and remove them.

Budget discipline
- Treat about 35 tool calls as an exploration checkpoint, not a target. At that point stop broad exploration and submit the best defensible patch, unless one short, decisive check remains. get_status shows your remaining budget.

Turn discipline
- After every tool result, begin your next reply with one plain sentence of notes, at most 20 words: what you learned and what you will do next. Keep replies short and tool-oriented.
- Keep working with tool calls until the task is genuinely finished. A reply without a tool call after a submission ends the task, so send one only when you are done, and make it a single sentence.
"""

FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)  # ZIP epoch: identical timestamps on every build


def source_files(eval_layout: str) -> dict[str, bytes]:
    if eval_layout == "nested":
        eval_text = EVAL_CONFIG_NESTED
    elif eval_layout == "flat":
        eval_text = EVAL_CONFIG_FLAT
    else:  # pragma: no cover
        raise SystemExit(f"unknown --eval-config-layout {eval_layout!r}")
    files = {
        "agent.yaml": AGENT_YAML,
        "configs/sampling.yaml": SAMPLING_YAML,
        "eval_config.yaml": eval_text,
        "prompts/system.md": SYSTEM_MD,
    }
    return {name: text.encode("utf-8") for name, text in files.items()}


def build_zip(files: dict[str, bytes], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3            # Unix, fixed
            info.external_attr = 0o100644 << 16  # regular file, rw-r--r--
            info.comment = b""
            info.extra = b""
            zf.writestr(info, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    tmp.replace(dest)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path, help="directory that receives both ZIPs")
    ap.add_argument("--eval-config-layout", choices=["nested", "flat"], default="nested",
                    help="nested = under an `evaluation:` key (documented layout, default); flat = four root-level keys")
    ap.add_argument("--emit-source-dir", type=Path, default=None, help="also write the loose source files here")
    args = ap.parse_args()

    files = source_files(args.eval_config_layout)
    out_primary = args.out_dir / "submission.zip"
    out_twin = args.out_dir / "submission-GEMMA-S0-BASELINE.zip"
    for target in (out_primary, out_twin):
        if target.exists():
            print(f"refusing to overwrite existing file: {target}", file=sys.stderr)
            return 2

    build_zip(files, out_primary)
    shutil.copyfile(out_primary, out_twin)  # byte-identical twin

    if args.emit_source_dir:
        for name, data in files.items():
            p = args.emit_source_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

    print(f"model              : {MODEL}")
    print(f"eval_config layout : {args.eval_config_layout}")
    for p in (out_primary, out_twin):
        print(f"{sha256(p)}  {p}  ({p.stat().st_size} bytes)")
    for name in sorted(files):
        print(f"  {hashlib.sha256(files[name]).hexdigest()}  {name}  ({len(files[name])} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
