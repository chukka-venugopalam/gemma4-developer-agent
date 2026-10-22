#!/usr/bin/env python3
"""Static preflight validator for the S0 baseline submission ZIP (v2, 2026-10-17: adds Y10 agent_class check and P06 undeclared-tool-token check).

IMPORTANT: this is an EMULATION of the rules documented in HARNESS_README (sections 2.2-2.4, 5, 6, 7.1).
It is NOT the official compiler. Official compilation and fake-model replay are reported as BLOCKED
unless the organizers' wheels are importable (see official_harness_check.py for those checks).

Every check has a status: PASS, WARN, FAIL or BLOCKED, and a kind:
    STATIC-ZIP | YAML | PROMPT | BUDGET | REPRO | OFFICIAL-COMPILE | FAKE-REPLAY | REAL-INFERENCE | HIDDEN-EVAL

Usage:
    python3 validate_s0.py submission.zip
    python3 validate_s0.py submission.zip --twin submission-GEMMA-S0-BASELINE.zip --builder build_s0_zip.py
    python3 validate_s0.py submission.zip --inventory /mnt/user-data/uploads --json-out report.json
    python3 validate_s0.py submission.zip --selftest        # mutation tests: every defect must be caught
Exit code: 0 when there is no FAIL, 1 otherwise (BLOCKED and WARN do not fail the run).
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    raise

# ----------------------------------------------------------------------------- contract constants
OFFICIAL_MODEL = "gemma-4-31b-it-qat-w4a16-ct"
REGISTRY_TOOLS = {  # HARNESS_README section 6: SwegemmaContext.create_tools()
    "run_command", "submit_patch", "get_status", "read_file", "edit_file", "write_file",
    "get_code_neighbors", "search_similar_code", "get_code_subgraph",
}
S0_TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
ALLOWED_EXT = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
ROOT_CONFIG_NAMES = ("agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml")
EXPECTED_FILES = {"agent.yaml", "eval_config.yaml", "configs/sampling.yaml", "prompts/system.md"}
LLM_AGENT_KEYS = {"name", "model", "adapter", "description", "instruction", "tools", "skills", "sub_agents",
                  "output_key", "include_contents", "disallow_transfer_to_parent",
                  "disallow_transfer_to_peers", "generate_content_config", "agent_class"}
S0_FORBIDDEN_AGENT_KEYS = {"adapter", "skills", "sub_agents", "output_key", "include_contents",
                           "disallow_transfer_to_parent", "disallow_transfer_to_peers"}
GEN_ALLOWED = {"temperature", "top_p", "top_k", "max_output_tokens", "presence_penalty", "frequency_penalty",
               "stop_sequences", "response_mime_type", "seed", "thinking_config"}
GEN_FORBIDDEN = {"tools", "system_instruction", "http_options", "safety_settings", "response_schema"}
MAX_TOTAL_BYTES = 3 * 1024 ** 3
MAX_FILES = 10_000
MAX_YAML_FILES = 1_000
MAX_YAML_BYTES = 50 * 1024 ** 2
MAX_INSTRUCTION_CHARS = 1_000_000
MAX_INCLUDE_DEPTH = 10
INTENDED_SAMPLING = {"temperature": 0.2, "top_p": 0.95, "top_k": 40, "max_output_tokens": 3072}
INTENDED_EVAL = {"timeout_seconds": 300, "max_tool_calls": 50, "max_time_minutes": 5, "max_turns": 100}
CONTEXT_CEILING = 32_768

FORBIDDEN_PROMPT_TERMS = [
    r"search_similar_code", r"get_code_neighbors", r"get_code_subgraph", r"agent_tool", r"sub[-_ ]?agents?",
    r"helper", r"investigator", r"analy[sz]er", r"graph", r"similarity", r"semantic", r"embedding",
    r"skills?", r"adapters?", r"\blora\b", r"custom tool",
]
SHELL_LITERAL_PATTERNS = [
    (r"```", "code fence"),
    (r"`", "backtick"),
    (r"(?m)^\s*[$>]\s+\S", "shell prompt line"),
    (r"(?<![\w-])(grep|find|sed|awk|cat|ls|git|python3?|pytest|pip|head|tail|xargs|rg|ag)\s+-{1,2}[A-Za-z]", "command with flags"),
    (r"(?<![\w-])(grep|find|sed|awk|cat|ls|git|python3?|pytest|pip|head|tail|xargs)\s+\S+\s*\|", "command piped"),
    (r"\|", "pipe character"),
    (r"&&", "command chaining"),
]
BEHAVIOR_REQUIREMENTS = [  # (label, regex) -> must be present in prompts/system.md
    ("exactly six tools named", r"exactly six tools: run_command, read_file, edit_file, write_file, get_status and submit_patch"),
    ("shell programs are not tools / run via run_command", r"Shell programs are never tools; run them only through run_command"),
    ("ignore other tool descriptions in task message", r"ignore that description and never call it"),
    ("read the issue once", r"Read the issue once"),
    ("targeted recursive lexical search via run_command", r"targeted recursive text searches through run_command"),
    ("explicit NO MATCHES then change approach", r"write NO MATCHES in your notes, then change the pattern or the directory"),
    ("at most 120 lines per read_file", r"at most 120 lines per read_file call"),
    ("never dump whole files/repos/long output", r"Never print whole large files, whole repositories or long test output"),
    ("reproduce in at most 2 calls", r"at most 2 calls"),
    ("scratch under /tmp via run_command", r"scratch files under /tmp by calling run_command"),
    ("never write_file for scratch", r"Never use write_file for scratch"),
    ("never leave scratch in repository", r"never leave scratch files in the repository"),
    ("root-cause gate before editing", r"Before editing, state in your notes a plausible root cause"),
    ("smallest compatible change", r"smallest compatible change"),
    ("no test/harness/build/config edits", r"Do not modify tests, pytest\.ini, conftest\.py, build files, test configuration or unrelated files"),
    ("no installs / no network", r"Do not install anything\. There is no network"),
    ("narrowest relevant test, never entire suite", r"Never run the entire test suite"),
    ("60 second command limit", r"60 second limit"),
    ("no identical repeated calls", r"Never repeat a tool call that already returned the same result"),
    ("edit fails twice -> re-read and rebuild", r"If an edit fails twice, re-read the exact lines"),
    ("submit plausible fix; resubmit after changes", r"call submit_patch\. If you change code afterwards, call it again"),
    ("inspect diff for scratch/unrelated changes", r"inspect the diff for temporary files, scratch files and unrelated changes"),
    ("about 35 calls is a checkpoint, not a target", r"about 35 tool calls as an exploration checkpoint, not a target"),
    ("one-sentence notes <= 20 words after tool result", r"one plain sentence of notes, at most 20 words"),
    ("keep using tools until finished", r"Keep working with tool calls until the task is genuinely finished"),
]


class ContractError(Exception):
    pass


# ----------------------------------------------------------------------------- result bookkeeping
class Results:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, cid: str, kind: str, name: str, status: str, detail: str) -> None:
        assert status in {"PASS", "WARN", "FAIL", "BLOCKED"}
        self.items.append({"id": cid, "kind": kind, "name": name, "status": status, "detail": detail})

    def status_of(self, cid: str) -> str | None:
        for it in self.items:
            if it["id"] == cid:
                return it["status"]
        return None

    @property
    def failed(self) -> bool:
        return any(i["status"] == "FAIL" for i in self.items)


# ----------------------------------------------------------------------------- helpers
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_include(base_dir: str, rel: str) -> str:
    """Emulates the documented !include path rules: relative to the including file, no absolute
    paths, no NUL, no '..' components (HARNESS_README section 2.2)."""
    if "\x00" in rel:
        raise ContractError("include path contains a NUL byte")
    if rel.startswith("/") or "\\" in rel or re.match(r"^[A-Za-z]:", rel):
        raise ContractError(f"include path is absolute or not POSIX-relative: {rel!r}")
    if any(part == ".." for part in rel.split("/")):
        raise ContractError(f"include path contains a '..' component: {rel!r}")
    resolved = posixpath.normpath(posixpath.join(base_dir, rel))
    if resolved.startswith("../") or resolved == "..":
        raise ContractError(f"include escapes the archive root: {rel!r}")
    return resolved


def load_yaml_with_includes(files: dict[str, bytes], path: str, trace: list, depth: int = 0, stack: tuple = ()):
    if depth > MAX_INCLUDE_DEPTH:
        raise ContractError(f"include depth exceeds {MAX_INCLUDE_DEPTH} at {path}")
    if path in stack:
        raise ContractError(f"include cycle: {' -> '.join(stack + (path,))}")
    if path not in files:
        raise ContractError(f"file not found in archive: {path}")
    base_dir = posixpath.dirname(path)

    class Loader(yaml.SafeLoader):
        pass

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            if key in seen:
                raise ContractError(f"{path}: duplicate YAML key {key!r}")
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(self, node, deep)

    def include(loader, node):
        rel = loader.construct_scalar(node)
        resolved = resolve_include(base_dir, rel)
        trace.append({"from": path, "include": rel, "resolved": resolved, "depth": depth + 1})
        if resolved not in files:
            raise ContractError(f"{path}: include target not in archive: {rel!r}")
        ext = posixpath.splitext(resolved)[1].lower()
        if ext in (".md", ".txt"):
            return files[resolved].decode("utf-8")
        if ext in (".yaml", ".yml"):
            return load_yaml_with_includes(files, resolved, trace, depth + 1, stack + (path,))
        raise ContractError(f"{path}: unsupported include extension {ext!r}")

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    Loader.add_constructor("!include", include)
    try:
        return yaml.load(files[path].decode("utf-8"), Loader=Loader)
    except yaml.YAMLError as exc:
        raise ContractError(f"{path}: YAML syntax error: {exc}") from exc


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# ----------------------------------------------------------------------------- the checks
def check_zip(zpath: Path, res: Results):
    """Static ZIP checks. Returns (files dict, infos) or (None, None) when the archive is unusable."""
    try:
        zf = zipfile.ZipFile(zpath, "r")
    except Exception as exc:
        res.add("Z01", "STATIC-ZIP", "archive opens", "FAIL", f"cannot open: {exc}")
        return None, None
    with zf:
        bad = zf.testzip()
        if bad is not None:
            res.add("Z01", "STATIC-ZIP", "archive opens and CRC32 verifies", "FAIL", f"CRC error in {bad}")
            return None, None
        infos = zf.infolist()
        res.add("Z01", "STATIC-ZIP", "archive opens and CRC32 verifies", "PASS", f"{len(infos)} entries, all CRC32 values valid")

        problems, warns, names = [], [], []
        for zi in infos:
            n = zi.filename
            names.append(n)
            if n.endswith("/"):
                warns.append(f"directory entry {n!r}")
                continue
            if "\x00" in n:
                problems.append(f"NUL byte in name {n!r}")
            if n.startswith("/") or re.match(r"^[A-Za-z]:", n):
                problems.append(f"absolute path {n!r}")
            if "\\" in n:
                problems.append(f"backslash in name {n!r}")
            if any(p == ".." for p in n.split("/")):
                problems.append(f"'..' traversal in {n!r}")
            if any(p.startswith(".") for p in n.split("/")):
                problems.append(f"hidden file/dir component in {n!r}")
            if "__pycache__" in n.split("/"):
                problems.append(f"__pycache__ in {n!r}")
            mode = (zi.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                problems.append(f"symlink entry {n!r}")
            if zi.flag_bits & 0x1:
                problems.append(f"encrypted entry {n!r}")
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            problems.append(f"duplicate entries {sorted(dupes)}")
        if problems:
            res.add("Z02", "STATIC-ZIP", "entry names are safe (no absolute/../symlink/hidden/duplicate)", "FAIL", "; ".join(problems))
        elif warns:
            res.add("Z02", "STATIC-ZIP", "entry names are safe (no absolute/../symlink/hidden/duplicate)", "WARN", "; ".join(warns))
        else:
            res.add("Z02", "STATIC-ZIP", "entry names are safe (no absolute/../symlink/hidden/duplicate)", "PASS", "no unsafe names, no directory entries, no duplicates")

        files = {zi.filename: zf.read(zi.filename) for zi in infos if not zi.filename.endswith("/")}

    bad_ext = sorted(n for n in files if posixpath.splitext(n)[1].lower() not in ALLOWED_EXT)
    res.add("Z03", "STATIC-ZIP", "only allowed file extensions (.yaml .yml .md .txt .py .json .safetensors)",
            "FAIL" if bad_ext else "PASS", f"rejected: {bad_ext}" if bad_ext else "all extensions allowed; no .sh, no dotfiles")

    present = set(files)
    missing, extra = sorted(EXPECTED_FILES - present), sorted(present - EXPECTED_FILES)
    top_levels = {n.split("/")[0] for n in files if "/" in n}
    nested_root = "agent.yaml" not in present and len(top_levels) == 1 and any(
        n.split("/", 1)[1] in ROOT_CONFIG_NAMES for n in files if "/" in n)
    if nested_root:
        res.add("Z04", "STATIC-ZIP", "minimal file set with agent.yaml at the archive root", "FAIL",
                f"nested root detected: agent.yaml lives under {sorted(top_levels)[0]!r}/ instead of the archive root")
    elif missing or extra:
        res.add("Z04", "STATIC-ZIP", "minimal file set with agent.yaml at the archive root", "FAIL",
                f"missing={missing} unexpected={extra}")
    else:
        res.add("Z04", "STATIC-ZIP", "minimal file set with agent.yaml at the archive root", "PASS",
                f"exactly {sorted(present)}; agent.yaml is at the root")

    total = sum(len(v) for v in files.values())
    yaml_files = [n for n in files if n.lower().endswith((".yaml", ".yml"))]
    big_yaml = [n for n in yaml_files if len(files[n]) > MAX_YAML_BYTES]
    ok = total < MAX_TOTAL_BYTES and len(files) <= MAX_FILES and len(yaml_files) <= MAX_YAML_FILES and not big_yaml
    res.add("Z05", "STATIC-ZIP", "size and count limits (<3 GiB, <=10,000 files, <=1,000 YAML files, YAML <=50 MiB)",
            "PASS" if ok else "FAIL", f"{len(files)} files, {total} bytes unpacked, {len(yaml_files)} YAML files")

    roots = [n for n in ROOT_CONFIG_NAMES if n in files]
    res.add("Z06", "STATIC-ZIP", "exactly one root config file", "PASS" if len(roots) == 1 else "FAIL",
            f"root configs found: {roots}")
    return files, infos


def check_yaml_and_agent(files: dict[str, bytes], res: Results, eval_layout: str):
    trace: list = []
    agent = None
    try:
        agent = load_yaml_with_includes(files, "agent.yaml", trace)
        parse_msg = f"agent.yaml parsed; {len(trace)} include(s) resolved: " + "; ".join(
            f"{t['from']} -> {t['resolved']}" for t in trace)
        # every other YAML must parse too
        for n in sorted(files):
            if n.endswith((".yaml", ".yml")) and n != "agent.yaml":
                load_yaml_with_includes(files, n, [])
        res.add("Y01", "YAML", "YAML parses with the documented !include rules (relative, no .., depth<=10, no cycles, no duplicate keys)",
                "PASS", parse_msg + " (emulated loader, not the official one)")
    except ContractError as exc:
        res.add("Y01", "YAML", "YAML parses with the documented !include rules (relative, no .., depth<=10, no cycles, no duplicate keys)",
                "FAIL", str(exc))
        return None, trace
    if not isinstance(agent, dict):
        res.add("Y02", "YAML", "exactly one root LlmAgent", "FAIL", "agent.yaml is not a mapping")
        return None, trace

    # ---- single root agent
    probs = []
    if agent.get("agent_class", "LlmAgent") != "LlmAgent":
        probs.append(f"agent_class={agent.get('agent_class')!r}")
    for key in ("sub_agents",):
        if agent.get(key):
            probs.append(f"{key} present")
    tools = agent.get("tools")
    if isinstance(tools, list):
        for t in tools:
            if not isinstance(t, str):
                probs.append(f"non-string tool entry (agent_tool or inline agent): {t!r}")
    sub_yaml = [n for n in files if n.endswith((".yaml", ".yml")) and n not in ("agent.yaml", "eval_config.yaml", "configs/sampling.yaml")]
    if sub_yaml:
        probs.append(f"additional YAML files that could define agents: {sub_yaml}")
    res.add("Y02", "YAML", "exactly one root LlmAgent (no sub-agents, agent_tool or inline agents)",
            "FAIL" if probs else "PASS", "; ".join(probs) if probs else f"single agent {agent.get('name')!r}")

    # ---- agent_class (documented default)
    ac = agent.get("agent_class", None)
    if ac is None:
        res.add("Y10", "YAML", "agent_class omitted: relies on the documented default (LlmAgent)", "PASS",
                "agent_class is absent; HARNESS_README 2.3 states SandboxedAgentConfig defaults to LlmAgent when it is omitted "
                "(third-party copy; the official loader has not been run, see O01)")
    elif ac == "LlmAgent":
        res.add("Y10", "YAML", "agent_class is LlmAgent", "PASS", "agent_class: LlmAgent")
    else:
        res.add("Y10", "YAML", "agent_class is LlmAgent or omitted", "FAIL", f"agent_class={ac!r}")

    # ---- model
    models = {agent.get("model")}
    gen = agent.get("generate_content_config")
    res.add("Y03", "YAML", f"model is exactly {OFFICIAL_MODEL} (single base model)",
            "PASS" if models == {OFFICIAL_MODEL} else "FAIL", f"declared models: {sorted(map(str, models))}")

    # ---- tools
    if not isinstance(tools, list):
        res.add("Y04", "YAML", "tools are exactly the six documented base tools", "FAIL", "tools is not a list")
    else:
        strs = [t for t in tools if isinstance(t, str)]
        unknown = sorted(set(strs) - REGISTRY_TOOLS)
        dupes = sorted({t for t in strs if strs.count(t) > 1})
        missing = sorted(set(S0_TOOLS) - set(strs))
        extra = sorted(set(strs) - set(S0_TOOLS))
        problems = []
        nonstr = [t for t in tools if not isinstance(t, str)]
        if nonstr:
            problems.append(f"non-string tool entries (agent_tool / inline agents are not part of S0): {nonstr}")
        if unknown:
            problems.append(f"not in the official 9-tool registry: {unknown}")
        if dupes:
            problems.append(f"duplicates: {dupes}")
        if missing:
            problems.append(f"missing S0 tools: {missing}")
        if extra:
            problems.append(f"tools outside the six S0 base tools: {extra}")
        res.add("Y04", "YAML", "tools are exactly the six documented base tools (subset of the official registry)",
                "FAIL" if problems else "PASS", "; ".join(problems) if problems else f"{S0_TOOLS} all in registry")

    # ---- agent fields
    unknown_keys = sorted(set(agent) - LLM_AGENT_KEYS)
    forbidden_keys = sorted(set(agent) & S0_FORBIDDEN_AGENT_KEYS)
    probs = []
    if unknown_keys:
        probs.append(f"unknown LlmAgent fields: {unknown_keys}")
    if forbidden_keys:
        probs.append(f"fields not allowed in S0 (skills/sub-agents/adapters etc.): {forbidden_keys}")
    for req in ("name", "model", "instruction"):
        if req not in agent:
            probs.append(f"missing required field {req!r}")
    if isinstance(agent.get("instruction"), str) and len(agent["instruction"]) > MAX_INSTRUCTION_CHARS:
        probs.append("instruction exceeds 1,000,000 chars")
    if isinstance(agent.get("name"), str) and not agent["name"].isidentifier():
        probs.append(f"name {agent['name']!r} is not a valid identifier")
    res.add("Y05", "YAML", "agent fields are documented LlmAgent fields; S0 adds no skills/sub-agents/adapters",
            "FAIL" if probs else "PASS", "; ".join(probs) if probs else f"fields: {sorted(agent)}")

    # ---- generate_content_config
    gprobs = []
    if not isinstance(gen, dict):
        gprobs.append("generate_content_config missing or not a mapping")
        gen = {}
    forb = sorted(set(gen) & GEN_FORBIDDEN)
    unk = sorted(set(gen) - GEN_ALLOWED - GEN_FORBIDDEN)
    if forb:
        gprobs.append(f"forbidden fields: {forb}")
    if unk:
        gprobs.append(f"fields not listed in the documented allow-list: {unk}")
    t = gen.get("temperature"); p = gen.get("top_p"); k = gen.get("top_k"); m = gen.get("max_output_tokens")
    if t is not None and not (is_number(t) and t >= 0):
        gprobs.append("temperature must be >= 0")
    if p is not None and not (is_number(p) and 0 <= p <= 1):
        gprobs.append("top_p must be within [0, 1]")
    if k is not None and not (isinstance(k, int) and not isinstance(k, bool) and k >= 1):
        gprobs.append("top_k must be an integer >= 1")
    if m is not None and not (isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= CONTEXT_CEILING):
        gprobs.append(f"max_output_tokens must be an integer in 1..{CONTEXT_CEILING}")
    tc = gen.get("thinking_config")
    if tc is not None:
        if not isinstance(tc, dict):
            gprobs.append("thinking_config is not a mapping")
        else:
            tb = tc.get("thinking_budget")
            if tb is not None and not (isinstance(tb, int) and not isinstance(tb, bool) and 0 <= tb <= CONTEXT_CEILING):
                gprobs.append(f"thinking_budget must be an integer in 0..{CONTEXT_CEILING}")
            lvl = tc.get("thinking_level")
            if lvl is not None and str(lvl).upper() not in {"MINIMAL", "LOW", "MEDIUM", "HIGH", "NONE"}:
                gprobs.append(f"thinking_level {lvl!r} not in the documented set")
            if tc.get("include_thoughts") is not None and not isinstance(tc["include_thoughts"], bool):
                gprobs.append("include_thoughts must be a boolean")
    res.add("Y06", "YAML", "generate_content_config uses only documented fields within documented ranges",
            "FAIL" if gprobs else "PASS", "; ".join(gprobs) if gprobs else f"fields: {sorted(gen)}")

    # ---- intended S0 values
    mism = []
    for key, want in INTENDED_SAMPLING.items():
        got = gen.get(key)
        if got != want or isinstance(got, bool):
            mism.append(f"{key}: want {want!r}, got {got!r}")
    tc = gen.get("thinking_config")
    if not (isinstance(tc, dict) and tc.get("include_thoughts") is False):
        mism.append(f"thinking_config.include_thoughts must be false, got {tc!r}")
    if isinstance(tc, dict) and set(tc) - {"include_thoughts"}:
        mism.append(f"thinking_config must contain only include_thoughts (no thinking_budget/thinking_level), extra: {sorted(set(tc) - {'include_thoughts'})}")
    res.add("Y07", "YAML", "S0 sampling: T=0.2, top_p=0.95, top_k=40, max_output_tokens=3072, thinking disabled with no budget",
            "FAIL" if mism else "PASS", "; ".join(mism) if mism else "values match the S0 specification exactly")

    # ---- eval_config
    try:
        ev = load_yaml_with_includes(files, "eval_config.yaml", [])
    except ContractError as exc:
        res.add("Y08", "YAML", "eval_config.yaml has the four documented fields in the documented layout", "FAIL", str(exc))
        return agent, trace
    problems = []
    if not isinstance(ev, dict):
        problems.append("eval_config.yaml is not a mapping")
        ev = {}
    if eval_layout == "nested":
        if set(ev) != {"evaluation"}:
            problems.append(f"documented layout needs exactly one root key 'evaluation'; found root keys {sorted(map(str, ev))}")
        block = ev.get("evaluation") if isinstance(ev.get("evaluation"), dict) else {}
    else:
        if set(ev) != set(INTENDED_EVAL):
            problems.append(f"flat layout needs exactly the four root keys; found {sorted(map(str, ev))}")
        block = ev
    if set(block) != set(INTENDED_EVAL):
        problems.append(f"fields must be exactly {sorted(INTENDED_EVAL)}; found {sorted(map(str, block))}")
    for key, want in INTENDED_EVAL.items():
        got = block.get(key)
        if not is_number(got) or got != want:
            problems.append(f"{key}: want {want}, got {got!r}")
    res.add("Y08", "YAML", f"eval_config.yaml has the four documented fields ({eval_layout} layout) with the S0 values",
            "FAIL" if problems else "PASS", "; ".join(problems) if problems else
            ("fields under the `evaluation:` key as documented in HARNESS_README 2.2 and 7.1" if eval_layout == "nested"
             else "four fields at the YAML root"))
    if eval_layout == "nested" and not problems:
        res.add("Y09", "YAML", "nested `evaluation:` layout follows the documented contract (task statement of 2026-10-17 confirms it)", "PASS",
                "HARNESS_README sections 2.2 and 7.1 (third-party copy) place the four fields under `evaluation:`; the latest task statement "
                "says not to change the wrapper without contradictory primary evidence. The official loader source has NOT been read here "
                "(see run-order cell 8) and the official sample_submission/eval_config.yaml was not available.")
    return agent, trace


def check_prompt(files: dict[str, bytes], agent: dict | None, res: Results):
    raw = files.get("prompts/system.md")
    if raw is None:
        res.add("P01", "PROMPT", "prompts/system.md present, UTF-8, non-empty", "FAIL", "file missing")
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        res.add("P01", "PROMPT", "prompts/system.md present, UTF-8, non-empty", "FAIL", f"not UTF-8: {exc}")
        return
    probs = []
    if not text.strip():
        probs.append("empty")
    if "\x00" in text:
        probs.append("NUL byte")
    if raw.startswith(b"\xef\xbb\xbf"):
        probs.append("UTF-8 BOM present")
    if "\r" in text:
        probs.append("CR characters (expected LF line endings)")
    if len(text) > MAX_INSTRUCTION_CHARS:
        probs.append("over 1,000,000 chars")
    if agent is not None and agent.get("instruction") != text:
        probs.append("agent instruction does not equal prompts/system.md after include resolution")
    words = len(text.split())
    res.add("P01", "PROMPT", "prompts/system.md present, UTF-8, LF, non-empty, equals the resolved instruction",
            "FAIL" if probs else "PASS", "; ".join(probs) if probs else f"{len(text)} chars, {words} words")

    n_open, n_close = text.count("{"), text.count("}")
    res.add("P02", "PROMPT", "no curly brace characters (ADK would treat {identifier} as a state key)",
            "PASS" if n_open == 0 and n_close == 0 else "FAIL", f"'{{' count={n_open}, '}}' count={n_close}")

    hits = []
    for pat in FORBIDDEN_PROMPT_TERMS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            hits.append(m.group(0))
    absent = [t for t in S0_TOOLS if t not in text]
    pr = []
    if hits:
        pr.append(f"mentions forbidden concepts: {sorted(set(hits))}")
    if absent:
        pr.append(f"does not name declared tools: {absent}")
    res.add("P03", "PROMPT", "names all six declared tools and refers to no graph/similarity/helper/skill/custom tools",
            "FAIL" if pr else "PASS", "; ".join(pr) if pr else "all six tools named; no forbidden terms")

    shell = []
    for pat, label in SHELL_LITERAL_PATTERNS:
        if re.search(pat, text):
            shell.append(label)
    res.add("P04", "PROMPT", "no literal shell-command examples (actions described in prose via run_command)",
            "FAIL" if shell else "PASS", f"found: {shell}" if shell else "no code fences, backticks, prompt lines, flagged commands, pipes or chaining")

    missing = [label for label, pat in BEHAVIOR_REQUIREMENTS if not re.search(pat, text)]
    res.add("P05", "PROMPT", f"all {len(BEHAVIOR_REQUIREMENTS)} required behaviours are stated (localization, context, reproduction, root-cause gate, verification, loops, submission, budget, turns, tool correctness)",
            "FAIL" if missing else "PASS", f"missing: {missing}" if missing else "every required behaviour phrase found")

    tokens = sorted(set(re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", text)))
    stray = [t for t in tokens if t not in S0_TOOLS]
    res.add("P06", "PROMPT", "every snake_case identifier in the prompt is one of the six declared tools (no undeclared tool-like names)",
            "FAIL" if stray else "PASS", f"undeclared tool-like tokens: {stray}" if stray else f"identifiers found: {tokens}")


def check_budget(files: dict[str, bytes], res: Results, eval_layout: str):
    try:
        ev = yaml.safe_load(files["eval_config.yaml"].decode("utf-8")) or {}
        block = ev.get("evaluation", ev) if eval_layout == "nested" else ev
        cap = float(block["max_time_minutes"])
    except Exception as exc:
        res.add("B01", "BUDGET", "12-hour worst-case projection", "FAIL", f"cannot read max_time_minutes: {exc}")
        return
    server_start_min, setup_min = 15.0, 0.1
    lines = []
    worst = 0.0
    for n in (120, 125):
        hours = (server_start_min + n * (cap + setup_min)) / 60.0
        worst = max(worst, hours)
        lines.append(f"N={n}: {hours:.2f} h")
    status = "PASS" if worst <= 11.0 else ("WARN" if worst <= 12.0 else "FAIL")
    res.add("B01", "BUDGET", "12-hour worst-case projection (every task hits its cap; third-party estimate model)", status,
            f"cap {cap:g} min/task, setup {setup_min} min/task, server start {server_start_min:g} min: " + "; ".join(lines) +
            " (limit 12 h; sequential execution; ESTIMATE, not an official figure)")
    try:
        gen = yaml.safe_load(files["configs/sampling.yaml"].decode("utf-8")) or {}
        mo = int(gen["max_output_tokens"])
        head = CONTEXT_CEILING - mo
        st = "PASS" if mo <= 4096 else "WARN"
        res.add("B02", "BUDGET", "context arithmetic: prompt + max_output_tokens must stay <= 32,768", st,
                f"max_output_tokens={mo} leaves {head} prompt tokens; ceiling {CONTEXT_CEILING}; "
                f"harness compaction threshold 14,336 (HARNESS_README 7.2); a request above the ceiling returns HTTP 400 (third-party reports)")
    except Exception as exc:
        res.add("B02", "BUDGET", "context arithmetic", "FAIL", f"cannot read max_output_tokens: {exc}")


def check_repro(zpath: Path, twin: Path | None, builder: Path | None, res: Results, eval_layout: str):
    notes = []
    status = "PASS"
    if twin is not None:
        if not twin.exists():
            res.add("R01", "REPRO", "twin archive is byte-identical", "FAIL", f"{twin} does not exist")
        else:
            same = filecmp.cmp(zpath, twin, shallow=False)
            res.add("R01", "REPRO", "twin archive is byte-identical", "PASS" if same else "FAIL",
                    f"sha256 {sha256_file(zpath)} vs {sha256_file(twin)}; cmp {'identical' if same else 'DIFFERENT'}")
    else:
        res.add("R01", "REPRO", "twin archive is byte-identical", "BLOCKED", "no --twin given")
    if builder is not None:
        digests = []
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(2):
                out = Path(tmp) / f"b{i}"
                proc = subprocess.run([sys.executable, str(builder), "--out-dir", str(out), "--eval-config-layout", eval_layout],
                                      capture_output=True, text=True)
                if proc.returncode != 0:
                    res.add("R02", "REPRO", "two clean rebuilds give the same SHA-256 as the archive under test", "FAIL",
                            f"builder failed: {proc.stderr.strip()[:300]}")
                    return
                digests.append(sha256_file(out / "submission.zip"))
        target = sha256_file(zpath)
        ok = digests[0] == digests[1] == target
        res.add("R02", "REPRO", "two clean rebuilds give the same SHA-256 as the archive under test", "PASS" if ok else "FAIL",
                f"rebuild1={digests[0]} rebuild2={digests[1]} target={target}")
    else:
        res.add("R02", "REPRO", "two clean rebuilds give the same SHA-256 as the archive under test", "BLOCKED", "no --builder given")


def check_official(res: Results):
    def spec(name: str):
        try:
            return importlib.util.find_spec(name) is not None
        except Exception:
            return False
    mods = {m: spec(m) for m in ("adk_submission", "swegemma", "adk_eval_core", "google.adk")}
    absent = [m for m, ok in mods.items() if not ok]
    env = f"python {sys.version.split()[0]}; importable: " + ", ".join(f"{m}={'yes' if ok else 'no'}" for m, ok in mods.items())
    if absent:
        res.add("O01", "OFFICIAL-COMPILE", "official validators and compile_submission", "BLOCKED",
                f"not run: {env}. The organizers' wheels are not installed here and the sandbox has no network. "
                "Next step: run official_harness_check.py in an environment with the competition wheelhouse installed.")
        res.add("F01", "FAKE-REPLAY", "scripted-model replay through the real harness", "BLOCKED",
                "not run: requires the official harness (swegemma, adk-submission, adk-eval-core) and a sandbox backend.")
    else:
        res.add("O01", "OFFICIAL-COMPILE", "official validators and compile_submission", "BLOCKED",
                f"official packages are importable ({env}) but this static validator does not invoke them; run official_harness_check.py")
        res.add("F01", "FAKE-REPLAY", "scripted-model replay through the real harness", "BLOCKED",
                "not run by this validator; see the report for the documented swegemma eval route")
    res.add("I01", "REAL-INFERENCE", "real Gemma 4 inference", "BLOCKED", "no GPU, no model weights, no inference server in this sandbox")
    res.add("H01", "HIDDEN-EVAL", "hidden-task evaluation / leaderboard score", "BLOCKED",
            "only Kaggle's scorer can run the hidden tasks; nothing here predicts the score")


def inventory(dirs: list[Path]) -> list[dict]:
    out = []
    for d in dirs:
        if not d.exists():
            out.append({"dir": str(d), "note": "directory does not exist"})
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file():
                entry = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
                if p.suffix.lower() == ".zip":
                    try:
                        with zipfile.ZipFile(p, "r") as zf:  # read-only
                            entry["zip_entries"] = zf.namelist()
                            entry["zip_crc_ok"] = zf.testzip() is None
                    except Exception as exc:
                        entry["zip_error"] = str(exc)
                out.append(entry)
    return out


def validate(zpath: Path, twin: Path | None = None, builder: Path | None = None, eval_layout: str = "nested") -> Results:
    res = Results()
    files, _ = check_zip(zpath, res)
    if files is not None:
        agent, trace = check_yaml_and_agent(files, res, eval_layout)
        check_prompt(files, agent, res)
        check_budget(files, res, eval_layout)
    check_repro(zpath, twin, builder, res, eval_layout)
    check_official(res)
    return res


# ----------------------------------------------------------------------------- mutation self-test
def _read_files(zpath: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(zpath) as zf:
        return {zi.filename: zf.read(zi.filename) for zi in zf.infolist() if not zi.filename.endswith("/")}


def _write_zip(files: dict[str, bytes], dest: Path, raw_names: dict[str, str] | None = None) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            zi = zipfile.ZipInfo((raw_names or {}).get(name, name), date_time=(1980, 1, 1, 0, 0, 0))
            zi.external_attr = 0o100644 << 16
            zf.writestr(zi, files[name])


def selftest(zpath: Path, eval_layout: str) -> tuple[bool, list[str]]:
    base = _read_files(zpath)
    lines, ok_all = [], True

    def case(label: str, expect_ids: list[str], mutate, raw_names=None):
        nonlocal ok_all
        files = dict(base)
        mutate(files)
        with tempfile.TemporaryDirectory() as tmp:
            z = Path(tmp) / "m.zip"
            _write_zip(files, z, raw_names(files) if raw_names else None)
            r = validate(z, eval_layout=eval_layout)
        hit = [i for i in expect_ids if r.status_of(i) == "FAIL"]
        ok = len(hit) == len(expect_ids)
        ok_all &= ok
        lines.append(f"{'CAUGHT ' if ok else 'MISSED '} {label}: expected FAIL on {expect_ids}, got "
                     f"{ {i: r.status_of(i) for i in expect_ids} }")

    sysmd = lambda f: f["prompts/system.md"].decode()
    case("curly brace in prompt", ["P02"], lambda f: f.__setitem__("prompts/system.md", (sysmd(f) + "\nUse {problem_description}.\n").encode()))
    case("extra graph tool declared", ["Y04"], lambda f: f.__setitem__("agent.yaml", f["agent.yaml"].decode().replace("  - submit_patch\n", "  - submit_patch\n  - search_similar_code\n").encode()))
    case("skills key added", ["Y05"], lambda f: f.__setitem__("agent.yaml", (f["agent.yaml"].decode() + "skills:\n  - skills/x\n").encode()))
    case("agent_tool entry added", ["Y02", "Y04"], lambda f: f.__setitem__("agent.yaml", (f["agent.yaml"].decode() + "  - agent_tool:\n      config_path: sub_agents/a.yaml\n").encode()))
    case("shell script shipped", ["Z03", "Z04"], lambda f: f.__setitem__("run.sh", b"echo hi\n"))
    case("nested root directory", ["Z04"], lambda f: None, raw_names=lambda f: {n: "submission/" + n for n in f})
    case("include with .. traversal", ["Y01"], lambda f: f.__setitem__("agent.yaml", f["agent.yaml"].decode().replace("!include prompts/system.md", "!include ../prompts/system.md").encode()))
    case("include target missing", ["Y01"], lambda f: f.__setitem__("agent.yaml", f["agent.yaml"].decode().replace("prompts/system.md", "prompts/missing.md").encode()))
    case("wrong model", ["Y03"], lambda f: f.__setitem__("agent.yaml", f["agent.yaml"].decode().replace("gemma-4-31b-it-qat-w4a16-ct", "gemma-4-31b-it").encode()))
    case("flat eval_config under nested expectation" if eval_layout == "nested" else "nested eval_config under flat expectation", ["Y08"],
         lambda f: f.__setitem__("eval_config.yaml", (b"timeout_seconds: 300\nmax_tool_calls: 50\nmax_time_minutes: 5\nmax_turns: 100\n" if eval_layout == "nested"
                                                      else b"evaluation:\n  timeout_seconds: 300\n  max_tool_calls: 50\n  max_time_minutes: 5\n  max_turns: 100\n")))
    case("budget values changed to 60 min / 100 calls / 500 turns", ["Y08"],
         lambda f: f.__setitem__("eval_config.yaml", f["eval_config.yaml"].decode().replace("max_time_minutes: 5", "max_time_minutes: 60").replace("max_tool_calls: 50", "max_tool_calls: 100").replace("max_turns: 100", "max_turns: 500").encode()))
    case("thinking budget added", ["Y07"], lambda f: f.__setitem__("configs/sampling.yaml", (f["configs/sampling.yaml"].decode() + "  thinking_budget: 4096\n").encode()))
    case("thinking enabled", ["Y07"], lambda f: f.__setitem__("configs/sampling.yaml", f["configs/sampling.yaml"].decode().replace("include_thoughts: false", "include_thoughts: true").encode()))
    case("max_output_tokens 16384", ["Y07"], lambda f: f.__setitem__("configs/sampling.yaml", f["configs/sampling.yaml"].decode().replace("3072", "16384").encode()))
    case("forbidden generation field", ["Y06"], lambda f: f.__setitem__("configs/sampling.yaml", (f["configs/sampling.yaml"].decode() + "system_instruction: hi\n").encode()))
    case("duplicate YAML key", ["Y01"], lambda f: f.__setitem__("configs/sampling.yaml", (f["configs/sampling.yaml"].decode() + "temperature: 0.5\n").encode()))
    case("shell literal in prompt", ["P04"], lambda f: f.__setitem__("prompts/system.md", (sysmd(f) + "\nExample: grep -rn foo src\n").encode()))
    case("graph tool mentioned in prompt", ["P03"], lambda f: f.__setitem__("prompts/system.md", (sysmd(f) + "\nYou may use get_code_neighbors.\n").encode()))
    case("required behaviour deleted from prompt", ["P05"], lambda f: f.__setitem__("prompts/system.md", sysmd(f).replace("NO MATCHES", "nothing").encode()))
    case("undeclared tool-like token in prompt", ["P06"], lambda f: f.__setitem__("prompts/system.md", (sysmd(f) + "\nThen call submit_patches when done.\n").encode()))
    case("agent_class set to SequentialAgent", ["Y02", "Y10"], lambda f: f.__setitem__("agent.yaml", ("agent_class: SequentialAgent\n" + f["agent.yaml"].decode()).encode()))
    case("absolute path entry", ["Z02"], lambda f: f.__setitem__("evil.txt", b"x"), raw_names=lambda f: {"evil.txt": "/etc/evil.txt"})
    case("hidden file", ["Z02", "Z04"], lambda f: f.__setitem__(".gitkeep", b""))
    return ok_all, lines


# ----------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", type=Path, help="submission ZIP to validate")
    ap.add_argument("--twin", type=Path, help="second archive that must be byte-identical")
    ap.add_argument("--builder", type=Path, help="path to build_s0_zip.py for the reproducible-rebuild check")
    ap.add_argument("--eval-config-layout", choices=["nested", "flat"], default="nested")
    ap.add_argument("--inventory", type=Path, action="append", default=[], help="directory to inventory read-only (repeatable)")
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--selftest", action="store_true", help="run mutation tests proving the checks catch defects")
    args = ap.parse_args()

    inv = inventory(args.inventory) if args.inventory else []
    res = validate(args.zip, args.twin, args.builder, args.eval_config_layout)

    print(f"archive : {args.zip}")
    if args.zip.exists():
        print(f"sha256  : {sha256_file(args.zip)}  ({args.zip.stat().st_size} bytes)")
    width = max(len(i["name"]) for i in res.items) if res.items else 10
    for it in res.items:
        print(f"[{it['status']:<7}] {it['id']:<4} {it['kind']:<16} {it['name']}")
        print(f"            {it['detail']}")
    counts = {s: sum(1 for i in res.items if i["status"] == s) for s in ("PASS", "WARN", "FAIL", "BLOCKED")}
    print("summary :", counts)

    if inv:
        print("\ninventory (read-only):")
        zips = [e for e in inv if e.get("path", "").lower().endswith(".zip")]
        for e in inv:
            print("  ", {k: v for k, v in e.items() if k != "zip_entries"})
        print(f"   supplied ZIP files found: {len(zips)}")

    selftest_report = None
    if args.selftest:
        ok, lines = selftest(args.zip, args.eval_config_layout)
        print("\nmutation self-test (each injected defect must be caught):")
        for ln in lines:
            print("  ", ln)
        print("   self-test:", "ALL CAUGHT" if ok else "SOME MISSED")
        selftest_report = {"all_caught": ok, "cases": lines}
        if not ok:
            res.add("T01", "STATIC-ZIP", "mutation self-test", "FAIL", "; ".join(l for l in lines if l.startswith("MISSED")))

    if args.json_out:
        args.json_out.write_text(json.dumps({"archive": str(args.zip), "sha256": sha256_file(args.zip) if args.zip.exists() else None,
                                             "checks": res.items, "summary": counts, "inventory": inv,
                                             "selftest": selftest_report}, indent=2), encoding="utf-8")
    return 1 if res.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
