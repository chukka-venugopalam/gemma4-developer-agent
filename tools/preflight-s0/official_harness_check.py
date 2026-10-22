#!/usr/bin/env python3
"""Official-harness checks for the S0 submission ZIP.

Run this in an environment where the organizers' wheels are installed
(adk-submission, swegemma, adk-eval-core, google-adk) - for example a Kaggle notebook with the
competition wheelhouse attached, or a local venv built from it. In an environment without them
every official step is reported BLOCKED and nothing is invented.

Design rules (deliberate):
  * Discovery first. The function names below come from HARNESS_README (validate_directory,
    validate_single_declared_model, compile_submission) and from a third-party PR description
    (discover_declared_models). Their import paths and signatures are NOT documented in the README, so
    this script walks the installed packages, prints what it finds, and calls a function ONLY when its
    signature has exactly one required positional parameter (the archive directory). Anything else is
    reported INCONCLUSIVE with the signature, so a human can decide. It never guesses arguments.
  * A passing call proves only that the call did not raise. It does not prove the agent behaves well.

Usage:
    python3 official_harness_check.py submission.zip
    python3 official_harness_check.py --check-budget-prompt first_user_message.txt
        # asserts that a captured first user message shows the S0 budgets (5 min / 50 calls / 100 turns),
        # which is how a fake-model replay proves that eval_config.yaml was actually read.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import importlib.util
import inspect
import pkgutil
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

TARGETS = ["validate_directory", "validate_single_declared_model", "discover_declared_models", "compile_submission"]
TOP_PACKAGES = ["adk_submission", "swegemma", "adk_eval_core"]
DISTRIBUTIONS = ["adk-submission", "swegemma", "adk-eval-core", "google-adk"]

# Format documented in HARNESS_README section 5.2 (item 3, "Task Budget").
BUDGET_LINE_PATTERNS = {
    "time": r"Time allowance:\s*5(?:\.0+)?\s*minutes",
    "tool_calls": r"Tool calls allowance:\s*50\s*calls",
    "turns": r"Max loop iterations:\s*100\s*turns",
}
DEFAULT_BUDGET_PATTERNS = {  # what you would see if eval_config.yaml were NOT applied
    "time": r"Time allowance:\s*60(?:\.0+)?\s*minutes",
    "tool_calls": r"Tool calls allowance:\s*100\s*calls",
    "turns": r"Max loop iterations:\s*500\s*turns",
}


def safe_extract(zpath: Path, dest: Path) -> None:
    with zipfile.ZipFile(zpath) as zf:
        for zi in zf.infolist():
            name = zi.filename
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or "\x00" in name:
                raise SystemExit(f"unsafe entry in archive: {name!r}")
        zf.extractall(dest)


def check_budget_prompt(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    print(f"captured prompt: {path} ({len(text)} chars)")
    ok = True
    for key, pat in BUDGET_LINE_PATTERNS.items():
        hit = re.search(pat, text) is not None
        print(f"  [{'PASS' if hit else 'FAIL'}] S0 budget line present: {key}")
        ok &= hit
    if not ok:
        defaults = [k for k, pat in DEFAULT_BUDGET_PATTERNS.items() if re.search(pat, text)]
        if defaults:
            print(f"  NOTE: harness defaults are visible for {defaults}: eval_config.yaml was probably NOT applied "
                  f"(check its layout: documented layout nests the four keys under `evaluation:`).")
        else:
            print("  NOTE: neither the S0 budgets nor the defaults were found; check that this is the FIRST user message.")
    return 0 if ok else 1


def discover():
    found = {}
    for top in TOP_PACKAGES:
        try:
            if importlib.util.find_spec(top) is None:
                continue
        except Exception:
            continue
        try:
            pkg = importlib.import_module(top)
        except Exception as exc:
            print(f"  could not import {top}: {exc}")
            continue
        modules = [pkg]
        if hasattr(pkg, "__path__"):
            for info in pkgutil.walk_packages(pkg.__path__, prefix=top + "."):
                try:
                    modules.append(importlib.import_module(info.name))
                except Exception:
                    continue  # optional heavy submodules may fail to import; skip silently
        for mod in modules:
            for name in TARGETS:
                obj = getattr(mod, name, None)
                if callable(obj) and getattr(obj, "__module__", None) == mod.__name__:
                    found.setdefault(name, []).append((mod.__name__, obj))
    return found


def single_required_param(fn) -> str | None:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return None
    required = [p for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return required[0].name if len(required) == 1 else None


def run_official(zpath: Path) -> int:
    results = []  # (status, name, detail)
    print("distributions:")
    for dist in DISTRIBUTIONS:
        try:
            print(f"  {dist} == {md.version(dist)}")
        except md.PackageNotFoundError:
            print(f"  {dist}: not installed")
    print(f"python {sys.version.split()[0]}")

    missing = []
    for top in TOP_PACKAGES + ["google.adk"]:
        try:
            present = importlib.util.find_spec(top) is not None
        except Exception:
            present = False
        if not present:
            missing.append(top)
    if missing:
        print(f"\nBLOCKED: not importable here: {missing}. Install the organizers' wheels, then re-run this script.")
        print("Nothing official was executed. No result below this line should be read as a pass.")
        return 3

    found = discover()
    print("\ndiscovered callables:")
    for name in TARGETS:
        for modname, fn in found.get(name, []):
            try:
                sig = str(inspect.signature(fn))
            except (TypeError, ValueError):
                sig = "(signature unavailable)"
            print(f"  {modname}.{name}{sig}")
        if name not in found:
            print(f"  {name}: NOT FOUND in {TOP_PACKAGES}")
            results.append(("BLOCKED", name, "not found in installed packages"))

    with tempfile.TemporaryDirectory() as tmp:
        agent_dir = Path(tmp) / "agent_dir"
        agent_dir.mkdir()
        safe_extract(zpath, agent_dir)
        for name in TARGETS:
            for modname, fn in found.get(name, []):
                param = single_required_param(fn)
                label = f"{modname}.{name}"
                if param is None:
                    results.append(("INCONCLUSIVE", label, f"signature {inspect.signature(fn)} needs more than the archive directory; not called"))
                    continue
                if name == "compile_submission":
                    results.append(("INCONCLUSIVE", label, "documented as compile_submission() -> ADK Runner, which needs harness registries; "
                                    "exercise it through swegemma eval or the official starter notebook instead"))
                    continue
                try:
                    out = fn(agent_dir)
                    results.append(("PASS", label, f"called with the extracted directory; returned {type(out).__name__}"))
                except Exception as exc:  # noqa: BLE001
                    results.append(("FAIL", label, f"{type(exc).__name__}: {exc}"))
    print("\nresults:")
    worst = 0
    for status, label, detail in results:
        print(f"  [{status}] {label}: {detail}")
        if status == "FAIL":
            worst = 1
    print("\nNext: run a scripted-model replay through the real harness and feed the captured first user message to "
          "--check-budget-prompt. See S0_VALIDATION_REPORT.md for the documented swegemma eval route.")
    return worst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", nargs="?", type=Path)
    ap.add_argument("--check-budget-prompt", type=Path, help="captured first user message to check for the S0 budgets")
    args = ap.parse_args()
    if args.check_budget_prompt:
        return check_budget_prompt(args.check_budget_prompt)
    if not args.zip:
        ap.error("give the submission ZIP or --check-budget-prompt")
    return run_official(args.zip)


if __name__ == "__main__":
    raise SystemExit(main())
