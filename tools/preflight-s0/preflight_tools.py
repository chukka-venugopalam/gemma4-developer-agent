#!/usr/bin/env python3
"""Helpers for the S0 official-harness gate (used by the Kaggle notebook cells; also runnable locally).

Everything here is READ-ONLY and OFFLINE. Nothing imports or executes official harness scripts: official
source files are inspected with the `ast` module only, so no vLLM server, evaluation or network call can
start by accident.

Sub-commands (python3 preflight_tools.py <cmd> ...):
    selftest                         run the helpers against synthetic fixtures (proves the helpers work; says nothing about the harness)
    inventory [ROOT]                 locate HARNESS_README.md, tasks.jsonl, sample_submission, wheels, snapshots, scripts/*.py under ROOT
    compare-sample SAMPLE_DIR S0_DIR compare layout/keys of the official sample with the S0 archive (eval_config nesting first)
    official-source FILE FUNC...     print the source of functions from an official .py file, extracted with ast (never executed)
    first-prompt TRACE OUT           pull the first user message out of a trace JSON and write it to OUT
    trace-tools TRACE                list tool-call names found in a trace and count calls after the first submit_patch
    help-scan FILE                   scan saved `--help` text for any documented fake / stub / scripted / mock model option
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

S0_TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
WANTED_NAMES = {
    "HARNESS_README.md": "harness_readme", "tasks.jsonl": "tasks_jsonl",
    "inference.py": "inference_py", "metric.py": "metric_py",
}
WANTED_DIRS = {"sample_submission": "sample_submission", "wheels": "wheels", "snapshots": "snapshots",
               "graphs": "graphs", "embeddings": "embeddings", "docker": "docker", "sandbox": "sandbox"}
FAKE_MODEL_KEYWORDS = ["fake", "stub", "mock", "scripted", "dry-run", "dry_run", "replay", "offline-model", "dummy"]


# ----------------------------------------------------------------------------- basics
def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(zip_path, dest) -> list[str]:
    """Extract a ZIP after rejecting absolute paths, '..', backslashes, NUL bytes and symlink entries."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(zip_path) as zf:
        for zi in zf.infolist():
            n = zi.filename
            p = PurePosixPath(n)
            if p.is_absolute() or ".." in p.parts or "\\" in n or "\x00" in n:
                raise ValueError(f"unsafe archive entry: {n!r}")
            if ((zi.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError(f"symlink entry refused: {n!r}")
            names.append(n)
        zf.extractall(dest)
    return names


def load_yaml_lenient(path):
    """YAML loader that tolerates the official `!include` tag by returning a marker string."""
    class L(yaml.SafeLoader):
        pass
    L.add_constructor("!include", lambda loader, node: f"<!include {loader.construct_scalar(node)}>")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.load(fh, Loader=L)


# ----------------------------------------------------------------------------- inventory
def inventory(root="/kaggle/input", max_depth=4, max_hits=40) -> dict:
    """Breadth-first, depth-limited search. Does not descend into 'snapshots' (thousands of files)."""
    root = Path(root)
    found: dict[str, list[str]] = {}
    if not root.exists():
        return {"error": f"{root} does not exist (not running on Kaggle, or no inputs mounted)"}
    queue = [(root, 0)]
    while queue:
        d, depth = queue.pop(0)
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            continue
        for e in entries:
            if e.is_file() and e.name in WANTED_NAMES:
                found.setdefault(WANTED_NAMES[e.name], []).append(e.path)
            if e.is_dir(follow_symlinks=False):
                if e.name in WANTED_DIRS:
                    found.setdefault(WANTED_DIRS[e.name], []).append(e.path)
                if e.name == "snapshots":
                    continue
                if depth + 1 <= max_depth:
                    queue.append((Path(e.path), depth + 1))
    return {k: v[:max_hits] for k, v in found.items()}


def describe_tree(path, max_entries=60) -> list[str]:
    out = []
    path = Path(path)
    for i, p in enumerate(sorted(path.rglob("*"))):
        if i >= max_entries:
            out.append("... (truncated)")
            break
        rel = p.relative_to(path)
        out.append(f"{'d' if p.is_dir() else 'f'} {rel}" + (f"  ({p.stat().st_size} B)" if p.is_file() else ""))
    return out


# ----------------------------------------------------------------------------- sample comparison
def classify_eval_layout(data) -> str:
    keys = {"timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"}
    if data is None:
        return "empty"
    if not isinstance(data, dict):
        return "not-a-mapping"
    if set(data) == {"evaluation"} and isinstance(data["evaluation"], dict) and set(data["evaluation"]) <= keys:
        return "nested"
    if set(data) <= keys and data:
        return "flat"
    return f"other (root keys: {sorted(map(str, data))})"


def compare_with_sample(sample_dir, s0_dir) -> dict:
    sample_dir, s0_dir = Path(sample_dir), Path(s0_dir)
    result = {"sample_dir": str(sample_dir), "s0_dir": str(s0_dir), "lines": [], "verdict": "UNKNOWN"}
    add = result["lines"].append
    if not sample_dir.exists():
        add("official sample_submission directory not found: layout comparison BLOCKED")
        result["verdict"] = "BLOCKED"
        return result
    sample_files = sorted(str(p.relative_to(sample_dir)) for p in sample_dir.rglob("*") if p.is_file())
    s0_files = sorted(str(p.relative_to(s0_dir)) for p in s0_dir.rglob("*") if p.is_file())
    add(f"sample files: {sample_files}")
    add(f"S0 files    : {s0_files}")
    sample_eval = sample_dir / "eval_config.yaml"
    s0_eval = s0_dir / "eval_config.yaml"
    layouts = {}
    for label, p in (("sample", sample_eval), ("S0", s0_eval)):
        if p.exists():
            layouts[label] = classify_eval_layout(load_yaml_lenient(p))
            add(f"{label} eval_config.yaml layout: {layouts[label]}")
        else:
            layouts[label] = "absent"
            add(f"{label} eval_config.yaml: absent")
    if layouts.get("sample") == layouts.get("S0") == "nested":
        result["verdict"] = "MATCH"
        add("VERDICT: S0 and the official sample both nest the four limits under `evaluation:`")
    elif layouts.get("sample") in ("flat", "other") or layouts.get("sample", "").startswith("other"):
        result["verdict"] = "MISMATCH"
        add("VERDICT: the official sample does NOT use the nested layout S0 uses. STOP and re-check the contract before any upload.")
    elif layouts.get("sample") == "absent":
        result["verdict"] = "UNKNOWN"
        add("VERDICT: the sample has no eval_config.yaml, so it cannot confirm the layout")
    else:
        result["verdict"] = "UNKNOWN"
    sample_agent = sample_dir / "agent.yaml"
    s0_agent = s0_dir / "agent.yaml"
    if sample_agent.exists() and s0_agent.exists():
        sa, za = load_yaml_lenient(sample_agent), load_yaml_lenient(s0_agent)
        add(f"sample agent.yaml keys: {sorted(sa) if isinstance(sa, dict) else type(sa).__name__}")
        add(f"S0 agent.yaml keys    : {sorted(za) if isinstance(za, dict) else type(za).__name__}")
        if isinstance(sa, dict) and isinstance(za, dict):
            add(f"keys only in S0: {sorted(set(za) - set(sa))}; keys only in sample: {sorted(set(sa) - set(za))}")
            add(f"sample model: {sa.get('model')!r}; S0 model: {za.get('model')!r}")
            st, zt = sa.get("tools"), za.get("tools")
            add(f"sample tools: {st}")
            add(f"S0 tools    : {zt}")
    return result


# ----------------------------------------------------------------------------- official source by AST (never executed)
def extract_function_source(py_path, func_name):
    src = Path(py_path).read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return ast.get_source_segment(src, node)
    return None


def official_source_report(py_path, funcs) -> dict:
    out = {"file": str(py_path), "functions": {}}
    for f in funcs:
        s = extract_function_source(py_path, f)
        out["functions"][f] = s
    loader = out["functions"].get("load_submission_eval_config")
    if loader:
        out["reads_evaluation_key"] = bool(re.search(r"""['"]evaluation['"]""", loader))
        out["mentions_four_keys"] = {k: (k in loader) for k in ("timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns")}
    return out


# ----------------------------------------------------------------------------- traces
def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def extract_first_user_message(trace_path, out_path) -> dict:
    data = json.loads(Path(trace_path).read_text(encoding="utf-8"))
    chosen = None
    steps = data.get("steps") if isinstance(data, dict) else None
    if isinstance(steps, list):
        for st in steps:
            if isinstance(st, dict) and st.get("source") in ("user", "system") and isinstance(st.get("message"), str) and "Task Budget" in st["message"]:
                chosen = st["message"]
                break
    if chosen is None:
        for s in _strings(data):
            if "## Task Budget" in s:
                chosen = s
                break
    if chosen is None:
        return {"ok": False, "reason": "no string containing '## Task Budget' found in the trace"}
    Path(out_path).write_text(chosen, encoding="utf-8")
    return {"ok": True, "chars": len(chosen), "out": str(out_path)}


def trace_tools(trace_path, declared=S0_TOOLS) -> dict:
    data = json.loads(Path(trace_path).read_text(encoding="utf-8"))
    ordered = []
    for d in _walk(data):
        name = d.get("function_name") or (d.get("name") if ("arguments" in d or "args" in d) else None)
        if isinstance(name, str):
            ordered.append(name)
    undeclared = sorted({n for n in ordered if n not in declared})
    after = None
    if "submit_patch" in ordered:
        after = len(ordered) - 1 - ordered.index("submit_patch")
    return {"tool_calls_found": len(ordered), "distinct": sorted(set(ordered)), "undeclared": undeclared,
            "calls_after_first_submit_patch": after,
            "note": "heuristic: reads ATIF-style `function_name` or `name`+`arguments`; confirm against the trace by eye"}


# ----------------------------------------------------------------------------- CLI help scan
def help_scan(text: str) -> dict:
    hits = {}
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for kw in FAKE_MODEL_KEYWORDS:
            if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", low):
                hits.setdefault(kw, []).append((i, line.strip()[:160]))
    return {"documented_fake_model_option_found": bool(hits), "hits": hits}


# ----------------------------------------------------------------------------- self-test on synthetic fixtures
def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # layout classification
        check("classify nested", classify_eval_layout({"evaluation": {"max_turns": 1}}) == "nested")
        check("classify flat", classify_eval_layout({"max_turns": 1, "max_tool_calls": 2}) == "flat")
        check("classify other", classify_eval_layout({"foo": 1}).startswith("other"))
        # sample comparison: nested sample -> MATCH; flat sample -> MISMATCH; missing -> BLOCKED
        (tmp / "s0").mkdir(); (tmp / "s0/eval_config.yaml").write_text("evaluation:\n  max_turns: 100\n")
        (tmp / "s0/agent.yaml").write_text("name: a\nmodel: m\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n")
        (tmp / "samp_n").mkdir(); (tmp / "samp_n/eval_config.yaml").write_text("evaluation:\n  max_turns: 50\n")
        (tmp / "samp_f").mkdir(); (tmp / "samp_f/eval_config.yaml").write_text("max_turns: 50\n")
        check("sample nested -> MATCH", compare_with_sample(tmp / "samp_n", tmp / "s0")["verdict"] == "MATCH")
        check("sample flat -> MISMATCH", compare_with_sample(tmp / "samp_f", tmp / "s0")["verdict"] == "MISMATCH")
        check("sample missing -> BLOCKED", compare_with_sample(tmp / "nope", tmp / "s0")["verdict"] == "BLOCKED")
        # AST extraction never executes the file
        marker = tmp / "executed.flag"
        (tmp / "inference.py").write_text(
            f"open({str(marker)!r}, 'w').write('x')\n"
            "def load_submission_eval_config(path):\n"
            "    data = yaml.safe_load(open(path))\n"
            "    ev = data.get('evaluation', {})\n"
            "    return {k: ev.get(k) for k in ('timeout_seconds','max_tool_calls','max_time_minutes','max_turns')}\n")
        rep = official_source_report(tmp / "inference.py", ["load_submission_eval_config", "missing_func"])
        check("AST extraction finds the loader", rep["functions"]["load_submission_eval_config"] is not None)
        check("AST extraction detects `evaluation` key", rep.get("reads_evaluation_key") is True)
        check("AST extraction returns None for a missing function", rep["functions"]["missing_func"] is None)
        check("official file was NOT executed", not marker.exists())
        # trace helpers
        trace = {"steps": [
            {"step_id": 1, "source": "user", "message": "You are evaluating...\n## Task Budget (x)\n- Time allowance: 5.0 minutes\n- Tool calls allowance: 50 calls\n- Max loop iterations: 100 turns\n"},
            {"step_id": 2, "source": "agent", "tool_calls": [{"tool_call_id": "1", "function_name": "run_command", "arguments": {"command": "x"}}]},
            {"step_id": 3, "source": "agent", "tool_calls": [{"tool_call_id": "2", "function_name": "submit_patch", "arguments": {}}]},
            {"step_id": 4, "source": "agent", "tool_calls": [{"tool_call_id": "3", "function_name": "search_similar_code", "arguments": {"query": "a"}}]},
        ]}
        (tmp / "trace.json").write_text(json.dumps(trace))
        r = extract_first_user_message(tmp / "trace.json", tmp / "first.txt")
        check("first user message extracted", r["ok"] and "Time allowance: 5.0 minutes" in (tmp / "first.txt").read_text())
        t = trace_tools(tmp / "trace.json")
        check("undeclared tool detected", t["undeclared"] == ["search_similar_code"])
        check("calls after first submit_patch counted", t["calls_after_first_submit_patch"] == 1)
        # help scan
        check("help scan finds a stub option", help_scan("  --stub-model  use a scripted model")["documented_fake_model_option_found"])
        check("help scan quiet on plain help", not help_scan("  --tasks PATH\n  --sandbox {docker,subprocess}")["documented_fake_model_option_found"])
        # inventory on a fake mount
        (tmp / "in/comp/wheels").mkdir(parents=True); (tmp / "in/comp/sample_submission").mkdir()
        (tmp / "in/comp/HARNESS_README.md").write_text("x"); (tmp / "in/comp/tasks.jsonl").write_text("{}\n")
        inv = inventory(tmp / "in")
        check("inventory finds README, tasks, wheels, sample", all(k in inv for k in ("harness_readme", "tasks_jsonl", "wheels", "sample_submission")))
        check("inventory reports a missing root", "error" in inventory(tmp / "absent"))
        # safe extraction
        bad = tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("../evil.txt", "x")
        try:
            safe_extract(bad, tmp / "o"); refused = False
        except ValueError:
            refused = True
        check("safe_extract refuses traversal", refused)
    print("selftest:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "selftest":
        return selftest()
    if cmd == "inventory":
        print(json.dumps(inventory(argv[2] if len(argv) > 2 else "/kaggle/input"), indent=2))
        return 0
    if cmd == "compare-sample":
        r = compare_with_sample(argv[2], argv[3])
        print("\n".join(r["lines"]))
        print("verdict:", r["verdict"])
        return 0 if r["verdict"] in ("MATCH",) else 1
    if cmd == "official-source":
        r = official_source_report(argv[2], argv[3:])
        for f, s in r["functions"].items():
            print(f"===== {f} =====")
            print(s if s else "(not found)")
        print({k: v for k, v in r.items() if k not in ("functions",)})
        return 0
    if cmd == "first-prompt":
        r = extract_first_user_message(argv[2], argv[3])
        print(json.dumps(r))
        return 0 if r["ok"] else 1
    if cmd == "trace-tools":
        print(json.dumps(trace_tools(argv[2]), indent=2))
        return 0
    if cmd == "help-scan":
        r = help_scan(Path(argv[2]).read_text(encoding="utf-8", errors="replace"))
        print(json.dumps(r, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
