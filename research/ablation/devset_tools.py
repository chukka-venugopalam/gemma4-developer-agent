#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
devset_tools.py -- development-set profiling, leakage audit / grouped splits,
bundle leak scan, run summarisation, 12-hour budget planning and design (power)
calculations for the "Google - The Gemma 4 Developer Agent Competition".

Standard library only (Python >= 3.8).  Deterministic (fixed seeds, sorted iteration).
Streams JSONL; keeps only compact per-task features in memory.

WHAT THIS FILE IS / IS NOT
  * `profile`, `audit-split`, `scan-bundle` are DESCRIPTIVE analyses of tasks.jsonl.
    They read the reference `patch` / `test_patch` only to DESCRIBE the dataset or to
    detect leakage.  Nothing they print is a model score, and no heuristic here
    (mention indicators, symbol overlap, ...) is Gemma's patch-success score.
  * `summarize` and `budget` compute statistics from RESULT ROWS YOU SUPPLY (for example
    rows exported from real runs of the official harness).  Feed them synthetic rows and
    you get synthetic output.
  * `power` is a design calculation under stated assumptions, not a result.
  * `selftest` fabricates a tiny synthetic dataset to prove that the code runs and is
    deterministic.  Its numbers mean nothing for the competition.

Subcommands:  profile | audit-split | scan-bundle | summarize | budget | budget-arith | power | selftest
Run `python devset_tools.py <subcommand> -h` for options.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import tarfile
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# 0. generic helpers
# ----------------------------------------------------------------------------


def sha1(s):
    return hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    """Stream a JSONL file (one object per non-empty line)."""
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit("%s:%d: invalid JSON: %s" % (path, ln, e))


def read_rows(path):
    """JSONL or CSV -> iterator of dict rows."""
    if path.lower().endswith(".csv"):
        with open(path, "r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                yield r
    else:
        for r in read_jsonl(path):
            yield r


def write_text(path, text):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


def write_csv(path, header, rows):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def fmt(x):
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isnan(x):
            return "n/a"
        return ("%.3f" % x) if abs(x) < 100 else ("%.1f" % x)
    return str(x)


def md_table(headers, rows):
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(fmt(c) for c in r) + " |")
    return "\n".join(out)


def quantile(sorted_vals, q):
    """Linear-interpolation quantile (same convention as numpy's default)."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def describe(vals):
    v = sorted(x for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x)))
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": v[0], "q1": quantile(v, .25), "median": quantile(v, .5),
            "q3": quantile(v, .75), "p90": quantile(v, .9), "max": v[-1], "mean": sum(v) / len(v)}


def describe_cells(d):
    if d.get("n", 0) == 0:
        return ["0", "", "", "", "", "", ""]
    return [d["n"], d["min"], d["q1"], d["median"], d["q3"], d["max"], d["mean"]]


DESC_HEADERS = ["n", "min", "q1", "median", "q3", "max", "mean"]


def parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        try:
            d = datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


# ----------------------------------------------------------------------------
# 1. statistics (exact / bootstrap; no numpy needed)
# ----------------------------------------------------------------------------


def wilson(k, n, z=1.959963984540054):
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / float(n)
    den = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def binom_cdf_half(k, n):
    """P(X <= k) for X ~ Binomial(n, 1/2), exact (integer arithmetic)."""
    if n <= 0:
        return 1.0
    if k < 0:
        return 0.0
    return sum(math.comb(n, i) for i in range(0, min(k, n) + 1)) / (2 ** n)


def sign_test_p(b, c, alternative="two-sided"):
    """Exact sign test / exact McNemar on discordant pairs.
    b = #pairs where B wins, c = #pairs where A wins (ties already dropped)."""
    n = b + c
    if n == 0:
        return 1.0
    if alternative == "greater":      # H1: B better than A
        return sum(math.comb(n, i) for i in range(b, n + 1)) / (2 ** n)
    if alternative == "less":
        return binom_cdf_half(b, n)
    return min(1.0, 2.0 * binom_cdf_half(min(b, c), n))


def post_prob_b_better(b, c):
    """P(theta > 0.5 | b wins, c losses) under a uniform Beta(1,1) prior on
    theta = P(B wins | discordant).  Ties ignored.  Closed form via the Beta/Binomial identity."""
    return binom_cdf_half(b, b + c + 1)


def boot_mean_ci(values, B=2000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for the mean of `values` (resample units with replacement)."""
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    rnd = random.Random(seed)
    means = []
    for _ in range(B):
        s = 0.0
        for _i in range(n):
            s += values[rnd.randrange(n)]
        means.append(s / n)
    means.sort()
    return (quantile(means, alpha / 2.0), quantile(means, 1.0 - alpha / 2.0))


# ----------------------------------------------------------------------------
# 2. schema aliases (documented column -> accepted spellings)
# ----------------------------------------------------------------------------

# Kaggle Data page documents: instance_id, repo, base_commit, problem_statement,
# hints_text, patch, test_patch, created_at.  Some local notes call `patch`
# `implementation_patch`; both spellings are accepted.
DOC_COLUMNS = ["instance_id", "repo", "base_commit", "problem_statement", "hints_text",
               "patch", "test_patch", "created_at"]
ALIASES = {
    "instance_id": ["instance_id", "task_id", "id"],
    "repo": ["repo"],
    "base_commit": ["base_commit"],
    "problem_statement": ["problem_statement", "issue_text", "issue"],
    "hints_text": ["hints_text", "hints"],
    "patch": ["patch", "implementation_patch", "gold_patch", "reference_patch", "fix_patch"],
    "test_patch": ["test_patch", "tests_patch"],
    "created_at": ["created_at"],
}


def field(row, key, default=""):
    for k in ALIASES[key]:
        v = row.get(k)
        if v is not None:
            return v
    return default


# ----------------------------------------------------------------------------
# 3. unified-diff parser (hunk-count aware, so a removed line like "-- x" is safe)
# ----------------------------------------------------------------------------

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
GITHDR_RE = re.compile(r"^diff --git a/(.*?) b/(.*)$")


def _new_file_entry():
    return {"a": None, "b": None, "new": False, "deleted": False, "rename": False,
            "binary": False, "hunks": []}


def parse_diff(text):
    """Parse a unified diff into a list of file dicts:
       {path, a, b, new, deleted, rename, binary, hunks:[{old_start, old_len, new_start,
        new_len, ctx, removed:[(old_line_no, text)], added:[(new_line_no, text)]}]}"""
    files = []
    cur = None
    hunk = None
    rem_old = rem_new = 0
    old_ln = new_ln = 0
    for raw in (text or "").split("\n"):
        if hunk is not None and (rem_old > 0 or rem_new > 0):
            tag = raw[:1]
            if tag == "-":
                hunk["removed"].append((old_ln, raw[1:]))
                old_ln += 1
                rem_old -= 1
                continue
            if tag == "+":
                hunk["added"].append((new_ln, raw[1:]))
                new_ln += 1
                rem_new -= 1
                continue
            if tag == " " or raw == "":
                old_ln += 1
                new_ln += 1
                rem_old -= 1
                rem_new -= 1
                continue
            if tag == "\\":
                continue
            hunk = None  # malformed: fall through to header handling
        elif raw.startswith("\\"):
            continue
        m = GITHDR_RE.match(raw)
        if m:
            cur = _new_file_entry()
            cur["a"], cur["b"] = m.group(1), m.group(2)
            files.append(cur)
            hunk = None
            continue
        if cur is None:
            if raw.startswith("--- "):
                cur = _new_file_entry()
                files.append(cur)
            else:
                continue
        if raw.startswith("new file mode"):
            cur["new"] = True
        elif raw.startswith("deleted file mode"):
            cur["deleted"] = True
        elif raw.startswith("rename from "):
            cur["rename"] = True
            cur["a"] = raw[len("rename from "):]
        elif raw.startswith("rename to "):
            cur["rename"] = True
            cur["b"] = raw[len("rename to "):]
        elif raw.startswith("similarity index"):
            cur["rename"] = True
        elif raw.startswith("Binary files") or raw.startswith("GIT binary patch"):
            cur["binary"] = True
        elif raw.startswith("--- "):
            p = raw[4:].split("\t")[0]
            if p == "/dev/null":
                cur["new"] = True
            elif p.startswith("a/"):
                cur["a"] = p[2:]
            elif cur["a"] is None:
                cur["a"] = p
        elif raw.startswith("+++ "):
            p = raw[4:].split("\t")[0]
            if p == "/dev/null":
                cur["deleted"] = True
            elif p.startswith("b/"):
                cur["b"] = p[2:]
            elif cur["b"] is None:
                cur["b"] = p
        else:
            hm = HUNK_RE.match(raw)
            if hm:
                os_, ol, ns, nl, ctx = hm.groups()
                ol = 1 if ol is None else int(ol)
                nl = 1 if nl is None else int(nl)
                hunk = {"old_start": int(os_), "old_len": ol, "new_start": int(ns), "new_len": nl,
                        "ctx": ctx or "", "removed": [], "added": []}
                cur["hunks"].append(hunk)
                rem_old, rem_new = ol, nl
                old_ln, new_ln = int(os_), int(ns)
    for f in files:
        if f["deleted"] and f["a"]:
            f["path"] = f["a"]
        else:
            f["path"] = f["b"] or f["a"] or ""
        f["n_added"] = sum(len(h["added"]) for h in f["hunks"])
        f["n_removed"] = sum(len(h["removed"]) for h in f["hunks"])
    return files


TEST_PATH_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_tests?\.py$|(^|/)conftest\.py$")


def path_kind(p):
    """test | docs_py | src | other  (src = python source that is not a test or docs example)."""
    p = p or ""
    if TEST_PATH_RE.search(p):
        return "test"
    if p.endswith(".py"):
        if p.startswith("docs_src/") or p.startswith("docs/") or p.startswith("examples/"):
            return "docs_py"
        return "src"
    return "other"


DEF_RE = re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_]\w*)")
TESTDEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w*)")


def approx_symbols(fd):
    """Symbols visible in the diff text itself (hunk-header context + changed def/class lines).
    APPROXIMATE: git's hunk header only names the nearest preceding top-level def/class."""
    syms = set()
    for h in fd["hunks"]:
        m = DEF_RE.match(h["ctx"] or "")
        if m:
            syms.add(m.group(1))
        for _, t in h["removed"] + h["added"]:
            m = DEF_RE.match(t)
            if m:
                syms.add(m.group(1))
    return syms


def enclosing_symbols(source, line_numbers):
    """Exact innermost enclosing def/class (qualified) for 1-indexed line numbers of `source`
    (the file at base_commit).  Returns None when the file does not parse."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    spans = []

    def visit(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = prefix + ch.name
                end = getattr(ch, "end_lineno", None) or ch.lineno
                spans.append((ch.lineno, end, q))
                visit(ch, q + ".")
            else:
                visit(ch, prefix)

    visit(tree, "")
    out = set()
    for ln in line_numbers:
        best = None
        for s, e, q in spans:
            if s <= ln <= e and (best is None or (e - s) < (best[1] - best[0])):
                best = (s, e, q)
        out.add(best[2] if best else "<module>")
    return out


def read_members_from_tgz(tgz_path, wanted):
    """Stream a .tgz and return {wanted_path: text}.  Matches a member whose name equals the
    wanted path or equals '<one top-level dir>/<wanted path>'.  Stops when all are found."""
    wanted = set(wanted)
    found = {}
    if not wanted:
        return found
    with tarfile.open(tgz_path, "r|gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            name = m.name
            while name.startswith("./"):
                name = name[2:]
            hit = None
            if name in wanted:
                hit = name
            elif "/" in name:
                tail = name.split("/", 1)[1]
                if tail in wanted:
                    hit = tail
            if hit is None or hit in found:
                continue
            fobj = tf.extractfile(m)
            if fobj is None:
                continue
            found[hit] = fobj.read().decode("utf-8", errors="replace")
            if len(found) == len(wanted):
                break
    return found


# ----------------------------------------------------------------------------
# 4. per-task features  (DESCRIPTIVE; uses reference patches only to describe the data)
# ----------------------------------------------------------------------------

TB_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+), in ([A-Za-z_<][\w<>]*)')
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")
FENCE_RE = re.compile(r"```(.*?)```", re.S)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
URL_RE = re.compile(r"https?://\S+")
TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)")
ERRWORD_RE = re.compile(r"\b\w+(?:Error|Exception)\b")

# symbol names too generic to count as an explicit mention in plain text
WEAK_STOP = {"self", "test", "init", "main", "call", "name", "type", "data", "info", "json", "text",
             "path", "file", "list", "dict", "with", "from", "none", "true", "false", "string",
             "value", "class", "args", "kwargs", "print", "open", "read", "write", "close",
             "send", "make", "load", "dump", "base", "item", "items", "keys", "values", "update"}

ISSUE_RULES = [  # first matching rule wins -> heuristic label, NOT ground truth
    ("traceback_or_exception", re.compile(r"Traceback \(most recent call last\)|\b\w+(?:Error|Exception)\b")),
    ("bug_behavior", re.compile(r"\b(bug|incorrect(?:ly)?|wrong(?:ly)?|unexpected(?:ly)?|broken|regression|"
                               r"fails?|failing|doesn't work|does not work|not working|instead of)\b", re.I)),
    ("feature_request", re.compile(r"\b(feature|support for|allow(?:s|ing)?|enable|would be (?:nice|great|useful)|"
                                   r"it would|propos(?:e|al)|option to|ability to|implement|add (?:a|an|the|support)\b)", re.I)),
    ("typing_docs_deprecation", re.compile(r"\b(typo|docs?|documentation|type hints?|typing|mypy|pyright|deprecat\w+)\b", re.I)),
]

TEST_STYLE_RES = {
    "parametrize": re.compile(r"@pytest\.mark\.parametrize"),
    "raises": re.compile(r"pytest\.raises|assertRaises"),
    "fixture_defined": re.compile(r"@pytest\.fixture"),
    "monkeypatch_or_mock": re.compile(r"monkeypatch|\bmock\b|MagicMock|\bpatch\("),
    "async_test": re.compile(r"^\s*async def test_", re.M),
    "class_based": re.compile(r"^\s*class Test\w*", re.M),
    "testclient": re.compile(r"TestClient"),
    "output_capture": re.compile(r"StringIO|capsys|capfd|record=True|export_text"),
}


def repo_short(instance_id, repo):
    if "_" in instance_id:
        return instance_id.rsplit("_", 1)[0]
    return (repo.split("/")[-1] if repo else "").lower()


def classify_issue(ps):
    head = ps[:4000]
    flags = {name: bool(rx.search(head)) for name, rx in ISSUE_RULES}
    label = "other"
    for name, _rx in ISSUE_RULES:
        if flags[name]:
            label = name
            break
    return label, flags


def _tokens_for_mentions(ps):
    strong, code, plain = set(), set(), set()
    for m in BACKTICK_RE.finditer(ps):
        strong.update(IDENT_RE.findall(m.group(1)))
    frames = TB_FRAME_RE.findall(ps)
    for _p, _ln, fn in frames:
        strong.add(fn)
    for m in FENCE_RE.finditer(ps):
        code.update(IDENT_RE.findall(m.group(1)))
    plain.update(IDENT_RE.findall(ps))
    return strong, code, plain, frames


def _dotted(path):
    p = path[:-3].replace("/", ".") if path.endswith(".py") else path.replace("/", ".")
    if p.endswith(".__init__"):
        p = p[: -len(".__init__")]
    out = {p}
    if p.startswith("src."):
        out.add(p[4:])
    return out


def mention_indicators(ps, gold_files, gold_symbols, frames, strong, code, plain):
    """How explicitly does the issue text name the files / symbols that the reference patch changes?
    Upper bound on 'text-only' localisation; says nothing about what an agent can do."""
    res = {}
    res["any_path_in_text"] = bool(re.search(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*\.py\b", ps))
    res["traceback_frames"] = len(frames)
    gf = list(gold_files)
    exact = any(g in ps for g in gf)
    tb = any(fp.replace("\\", "/").endswith(g) for fp, _l, _f in frames for g in gf)
    base = any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(os.path.basename(g)) + r"(?![A-Za-z0-9_])", ps) for g in gf)
    dotted = False
    for g in gf:
        for d in _dotted(g):
            if d and re.search(r"(?<![A-Za-z0-9_.])" + re.escape(d) + r"(?![A-Za-z0-9_])", ps):
                dotted = True
    res["file_exact_path"] = exact or tb
    res["file_basename"] = base
    res["file_dotted_module"] = dotted
    res["file_any"] = bool(exact or tb or base or dotted)
    parts = set()
    for q in gold_symbols:
        for c in q.split("."):
            if len(c) >= 4 and c != "<module>":
                parts.add(c)
    res["symbol_strong"] = bool(parts & strong)
    res["symbol_in_code_block"] = bool(parts & code)
    res["symbol_plain_weak"] = bool({p for p in parts if p.lower() not in WEAK_STOP} & plain)
    return res


def task_features(row, snapshots_dir=None):
    tid = str(field(row, "instance_id"))
    repo = str(field(row, "repo"))
    ps = str(field(row, "problem_statement"))
    hints = str(field(row, "hints_text"))
    patch = str(field(row, "patch"))
    tpatch = str(field(row, "test_patch"))
    created = parse_dt(field(row, "created_at"))
    pfiles = parse_diff(patch)
    tfiles = parse_diff(tpatch)
    kinds = [(f, path_kind(f["path"])) for f in pfiles]
    src = [f for f, k in kinds if k == "src"]
    tests_in_patch = [f for f, k in kinds if k == "test"]
    docs_py = [f for f, k in kinds if k == "docs_py"]
    other = [f for f, k in kinds if k == "other"]

    # symbols: exact (needs snapshots) or approximate (diff text only)
    symbols_mode = "approx"
    sym_pairs = set()
    new_files = [f["path"] for f in src if f["new"]]
    exact_ok = False
    if snapshots_dir:
        tgz = os.path.join(snapshots_dir, tid + ".tgz")
        if os.path.exists(tgz):
            wanted = [f["path"] for f in src if not f["new"]]
            try:
                texts = read_members_from_tgz(tgz, wanted)
            except (tarfile.TarError, OSError, EOFError):
                texts = {}
            if texts or not wanted:
                exact_ok = True
                for f in src:
                    if f["new"]:
                        sym_pairs.add((f["path"], "<new_file>"))
                        continue
                    lines = []
                    for h in f["hunks"]:
                        if h["removed"]:
                            lines.extend(ln for ln, _t in h["removed"])
                        else:
                            lines.append(max(1, h["old_start"]))
                    syms = enclosing_symbols(texts[f["path"]], lines) if f["path"] in texts else None
                    if syms is None:
                        exact_ok = False
                        break
                    for s in syms:
                        sym_pairs.add((f["path"], s))
    if exact_ok:
        symbols_mode = "exact"
    else:
        sym_pairs = set()
        for f in src:
            if f["new"]:
                sym_pairs.add((f["path"], "<new_file>"))
            for s in approx_symbols(f):
                sym_pairs.add((f["path"], s))
    gold_symbols = {s for _p, s in sym_pairs if s not in ("<new_file>", "<module>")}

    added_test_text = "\n".join(t for f in tfiles for h in f["hunks"] for _n, t in h["added"])
    test_defs = []
    for f in tfiles:
        for h in f["hunks"]:
            for _n, t in h["added"]:
                m = TESTDEF_RE.match(t)
                if m:
                    test_defs.append((f["path"], m.group(1)))

    strong, code, plain, frames = _tokens_for_mentions(ps)
    ment = mention_indicators(ps, [f["path"] for f in src], gold_symbols, frames, strong, code, plain)
    itype, iflags = classify_issue(ps)
    added_src_text = "\n".join(t for f in src for h in f["hunks"] for _n, t in h["added"])
    removed_src_text = "\n".join(t for f in src for h in f["hunks"] for _n, t in h["removed"])
    new_defs = set(DEF_RE.match(l).group(1) for l in added_src_text.split("\n") if DEF_RE.match(l)) - \
        set(DEF_RE.match(l).group(1) for l in removed_src_text.split("\n") if DEF_RE.match(l))

    feats = {
        "instance_id": tid,
        "repo": repo,
        "repo_short": repo_short(tid, repo),
        "base_commit": str(field(row, "base_commit")),
        "created_at": created.isoformat() if created else "",
        "year": created.year if created else None,
        "issue_chars": len(ps),
        "issue_lines": ps.count("\n") + 1 if ps else 0,
        "hints_chars": len(hints),
        "has_traceback": bool(TRACEBACK_RE.search(ps)),
        "n_code_blocks": len(FENCE_RE.findall(ps)),
        "has_code_block": bool(FENCE_RE.search(ps)),
        "has_repro": any(("import " in b) or (">>>" in b) or ("def " in b) or ("print(" in b)
                         for b in FENCE_RE.findall(ps)),
        "n_urls": len(URL_RE.findall(ps)),
        "issue_type_heuristic": itype,
        "n_files_total": len(pfiles),
        "n_src_files": len(src),
        "n_test_files_in_patch": len(tests_in_patch),
        "n_docs_py_files": len(docs_py),
        "n_other_files": len(other),
        "n_src_dirs": len({os.path.dirname(f["path"]) for f in src}),
        "n_src_toplevel": len({f["path"].split("/")[0] for f in src}),
        "hunks_src": sum(len(f["hunks"]) for f in src),
        "lines_added_src": sum(f["n_added"] for f in src),
        "lines_removed_src": sum(f["n_removed"] for f in src),
        "lines_changed_src": sum(f["n_added"] + f["n_removed"] for f in src),
        "lines_changed_all": sum(f["n_added"] + f["n_removed"] for f in pfiles),
        "n_new_src_files": len(new_files),
        "n_symbols": len(gold_symbols),
        "symbols_mode": symbols_mode,
        "patch_adds_new_def": bool(new_defs),
        "patch_only_nonpy_or_tests": len(src) == 0,
        "n_test_files": sum(1 for f in tfiles if path_kind(f["path"]) == "test"),
        "n_new_test_defs": len(test_defs),
        "test_patch_lines_added": sum(f["n_added"] for f in tfiles),
        "n_gold_src_files_for_mentions": len(src),
    }
    for k, v in ment.items():
        feats["m_" + k] = v
    for k, rx in TEST_STYLE_RES.items():
        feats["ts_" + k] = bool(rx.search(added_test_text))
    for k, v in iflags.items():
        feats["it_" + k] = v
    # private (non-CSV) payload for the leakage audit
    feats["_src_files"] = {f["path"] for f in src}
    feats["_sym_pairs"] = {(p, s) for p, s in sym_pairs if s not in ("<module>",)}
    feats["_test_pairs"] = set(test_defs)
    feats["_text"] = ps
    feats["_patch_hash"] = sha1(patch) if patch else ""
    feats["_ps_hash"] = sha1(ps[:4000]) if ps else ""
    return feats


# ----------------------------------------------------------------------------
# 5. profile
# ----------------------------------------------------------------------------

NUMERIC_PROFILE = ["issue_chars", "n_files_total", "n_src_files", "n_src_dirs", "n_src_toplevel",
                   "hunks_src", "lines_changed_src", "n_symbols", "n_new_test_defs", "n_test_files"]
BOOL_PROFILE = ["has_traceback", "has_code_block", "has_repro", "patch_adds_new_def",
                "patch_only_nonpy_or_tests",
                "ts_parametrize", "ts_raises", "ts_fixture_defined", "ts_monkeypatch_or_mock",
                "ts_async_test", "ts_class_based", "ts_testclient", "ts_output_capture"]
MENTION_PROFILE = ["m_any_path_in_text", "m_file_exact_path", "m_file_basename", "m_file_dotted_module",
                   "m_file_any", "m_symbol_strong", "m_symbol_in_code_block", "m_symbol_plain_weak"]
CSV_COLS = (["instance_id", "repo", "repo_short", "base_commit", "created_at", "year", "issue_type_heuristic",
             "hints_chars", "n_code_blocks", "n_urls", "issue_lines", "n_docs_py_files", "n_other_files",
             "n_new_src_files", "lines_added_src", "lines_removed_src", "lines_changed_all",
             "test_patch_lines_added", "symbols_mode", "m_traceback_frames"]
            + NUMERIC_PROFILE + BOOL_PROFILE + MENTION_PROFILE)


def frac_cells(feats, key):
    n = len(feats)
    k = sum(1 for f in feats if f.get(key))
    return k, n, (k / n if n else float("nan"))


def cmd_profile(args):
    schema_seen, schema_nonempty, schema_types = Counter(), Counter(), defaultdict(Counter)
    feats = []
    n_rows = 0
    for row in read_jsonl(args.tasks):
        n_rows += 1
        for k, v in row.items():
            schema_seen[k] += 1
            schema_types[k][type(v).__name__] += 1
            if v not in (None, "", [], {}):
                schema_nonempty[k] += 1
        feats.append(task_features(row, args.snapshots_dir))
    if not feats:
        raise SystemExit("no rows in %s" % args.tasks)
    feats.sort(key=lambda f: f["instance_id"])
    out = args.out
    L = []
    L.append("# Dataset profile (DESCRIPTIVE ONLY -- not a model evaluation)\n")
    L.append("Input: `%s`  rows=%d  sha256=`%s`\n" % (os.path.basename(args.tasks), n_rows,
                                                      sha256_file(args.tasks)[:16]))
    L.append("Symbols mode counts: %s  (exact needs --snapshots-dir)\n" % dict(Counter(f["symbols_mode"] for f in feats)))
    # schema
    L.append("## 1. Schema check vs documented columns\n")
    rows = []
    for c in sorted(schema_seen):
        doc = "documented" if c in DOC_COLUMNS else "NOT in documented list"
        alias_of = [k for k, v in ALIASES.items() if c in v and c != k]
        if alias_of:
            doc = "alias of `%s`" % alias_of[0]
        rows.append([c, schema_seen[c], schema_nonempty[c], "/".join("%s:%d" % kv for kv in schema_types[c].most_common()), doc])
    L.append(md_table(["column", "rows present", "rows non-empty", "python types", "status"], rows))
    missing = [c for c in DOC_COLUMNS if not any(a in schema_seen for a in ALIASES[c])]
    L.append("\nDocumented columns missing from the file: %s\n" % (missing or "none"))
    # counts
    L.append("## 2. Task count by repository / year\n")
    by_repo = defaultdict(list)
    for f in feats:
        by_repo[f["repo_short"]].append(f)
    rows = [[r, len(v), len(v) / len(feats)] for r, v in sorted(by_repo.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    rows.append(["ALL", len(feats), 1.0])
    L.append(md_table(["repo_short", "tasks", "share"], rows))
    years = sorted({f["year"] for f in feats if f["year"]})
    rows = []
    for r, v in sorted(by_repo.items()):
        c = Counter(f["year"] for f in v)
        rows.append([r] + [c.get(y, 0) for y in years])
    L.append("\n" + md_table(["repo_short"] + [str(y) for y in years], rows))
    dts = sorted(f["created_at"] for f in feats if f["created_at"])
    if dts:
        L.append("\ncreated_at range: %s .. %s\n" % (dts[0][:10], dts[-1][:10]))
    # issue type
    L.append("## 3. Issue type (HEURISTIC keyword rules, not ground truth)\n")
    types = sorted({f["issue_type_heuristic"] for f in feats})
    rows = []
    for r, v in sorted(by_repo.items()):
        c = Counter(f["issue_type_heuristic"] for f in v)
        rows.append([r] + [c.get(t, 0) for t in types])
    c = Counter(f["issue_type_heuristic"] for f in feats)
    rows.append(["ALL"] + [c.get(t, 0) for t in types])
    L.append(md_table(["repo_short"] + types, rows))
    # numeric
    L.append("\n## 4. Size / complexity indicators (reference patch & tests; `src` = non-test .py outside docs/examples)\n")
    for key in NUMERIC_PROFILE:
        rows = []
        for r, v in sorted(by_repo.items()):
            rows.append([r] + describe_cells(describe([f[key] for f in v])))
        rows.append(["ALL"] + describe_cells(describe([f[key] for f in feats])))
        L.append("**%s**\n\n%s\n" % (key, md_table(["repo_short"] + DESC_HEADERS, rows)))
    # files touched distribution
    rows = []
    for r, v in sorted(by_repo.items()):
        c = Counter(min(f["n_src_files"], 3) for f in v)
        rows.append([r, c.get(0, 0), c.get(1, 0), c.get(2, 0), c.get(3, 0)])
    c = Counter(min(f["n_src_files"], 3) for f in feats)
    rows.append(["ALL", c.get(0, 0), c.get(1, 0), c.get(2, 0), c.get(3, 0)])
    L.append("**source files touched by the reference patch**\n\n" + md_table(["repo_short", "0", "1", "2", "3+"], rows) + "\n")
    # booleans
    L.append("## 5. Fractions: issue shape, patch shape, test style (k/n)\n")
    rows = []
    for key in BOOL_PROFILE:
        row = [key]
        for r, v in sorted(by_repo.items()):
            k, n, p = frac_cells(v, key)
            row.append("%d/%d (%.2f)" % (k, n, p))
        k, n, p = frac_cells(feats, key)
        row.append("%d/%d (%.2f)" % (k, n, p))
        rows.append(row)
    L.append(md_table(["flag"] + sorted(by_repo) + ["ALL"], rows))
    # mentions
    L.append("\n## 6. Does the issue text name the files/symbols the reference patch changes? (HEURISTIC; tasks with >=1 gold src file)\n")
    L.append("`file_*` use the gold src file paths; `symbol_*` use changed def/class names (exact if snapshots given, else approximate). "
             "`symbol_strong` = in backticks or traceback; `symbol_in_code_block` = inside ``` fences; `symbol_plain_weak` = any whole-word match "
             "after dropping generic names. These are *upper bounds on text-only localisation*, not agent results.\n")
    rows = []
    for key in MENTION_PROFILE:
        row = [key]
        for r, v in sorted(by_repo.items()):
            vv = [f for f in v if f["n_src_files"] > 0]
            k, n, p = frac_cells(vv, key)
            row.append("%d/%d (%.2f)" % (k, n, p))
        vv = [f for f in feats if f["n_src_files"] > 0]
        k, n, p = frac_cells(vv, key)
        row.append("%d/%d (%.2f)" % (k, n, p))
        rows.append(row)
    L.append(md_table(["indicator"] + sorted(by_repo) + ["ALL"], rows))
    # duplicates
    L.append("\n## 7. Duplicate / shared identifiers (inputs to the leakage audit)\n")
    dup = []
    for name, key in [("instance_id", "instance_id"), ("(repo, base_commit)", None), ("reference patch hash", "_patch_hash"),
                      ("problem_statement[:4000] hash", "_ps_hash")]:
        groups = defaultdict(list)
        for f in feats:
            kk = (f["repo"], f["base_commit"]) if key is None else f[key]
            if kk and kk != ("", ""):
                groups[kk].append(f["instance_id"])
        shared = {k: v for k, v in groups.items() if len(v) > 1}
        dup.append([name, len(groups), len(shared), sum(len(v) for v in shared.values())])
        if key is None and shared:
            L.append("Tasks sharing a (repo, base_commit): " + "; ".join(sorted(",".join(v) for v in shared.values())) + "\n")
    L.append(md_table(["key", "distinct", "keys shared by >1 task", "tasks involved"], dup))
    L.append("\nGenerated by devset_tools.py profile. Cross-check against third-party-reported values listed in the plan, but trust this output.\n")
    write_text(os.path.join(out, "profile.md"), "\n".join(L))
    write_csv(os.path.join(out, "task_features.csv"), CSV_COLS,
              [[f.get(c) if not isinstance(f.get(c), bool) else int(f.get(c)) for c in CSV_COLS] for f in feats])
    summary = {"n_tasks": len(feats), "by_repo": {r: len(v) for r, v in by_repo.items()},
               "numeric": {k: describe([f[k] for f in feats]) for k in NUMERIC_PROFILE},
               "bool_fractions": {k: frac_cells(feats, k)[2] for k in BOOL_PROFILE + MENTION_PROFILE},
               "symbols_mode": dict(Counter(f["symbols_mode"] for f in feats)),
               "input_sha256": sha256_file(args.tasks)}
    write_json(os.path.join(out, "profile.json"), summary)
    print("profile: wrote %s/{profile.md,profile.json,task_features.csv}  tasks=%d" % (out, len(feats)))


# ----------------------------------------------------------------------------
# 6. leakage audit + grouped, stratified split
# ----------------------------------------------------------------------------

STOPWORDS = set("the a an and or of to in is it this that for on with as at by be are was were not but if from "
                "have has had do does did when then than so can could should would will just also its into out "
                "up you we they he she them there here what which who how why all any some no yes use used using "
                "get got set one two new".split())


def strip_boilerplate(texts, frac=0.10, min_docs=3):
    """Drop lines that recur across many issues (issue-template headings / checkboxes) before text similarity,
    so that two issues are not 'similar' merely because they were filed with the same template."""
    n = len(texts)
    thresh = max(min_docs, int(math.ceil(frac * n)))
    df = Counter()
    per_doc = []
    for t in texts:
        ls = [re.sub(r"\s+", " ", l.strip().lower()) for l in t.split("\n")]
        ls = [l for l in ls if len(l) >= 3]
        per_doc.append(ls)
        df.update(set(ls))
    return ["\n".join(l for l in ls if df[l] < thresh) for ls in per_doc]


def tfidf_vectors(texts, max_df=0.30):
    """L2-normalised TF-IDF over lower-cased word tokens; terms present in > max_df of the documents are dropped."""
    docs, df = [], Counter()
    for t in texts:
        toks = [w for w in re.findall(r"[a-z][a-z0-9_]{2,}", t.lower()) if w not in STOPWORDS]
        tf = Counter(toks)
        docs.append(tf)
        df.update(tf.keys())
    n = len(texts)
    vecs = []
    for tf in docs:
        v = {w: (1.0 + math.log(c)) * math.log((n + 1.0) / (df[w] + 1.0)) for w, c in tf.items() if df[w] <= max_df * n}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def cosine(u, v):
    if len(u) > len(v):
        u, v = v, u
    return sum(x * v.get(w, 0.0) for w, x in u.items())


class DSU(object):
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


HARD_TYPES = ("same_base_commit", "same_symbol", "same_test_def", "text_near_duplicate")


def build_edges(feats, text_soft, text_hard):
    """Pairwise leakage evidence between tasks.  HARD edges force tasks into the same split group:
       same (repo, base_commit) | same (file, symbol) changed by the reference patch |
       same added test def in the same test file | near-identical issue text (cosine >= text_hard).
       SOFT edges are reported but do not group: similar issue text (cosine >= text_soft), shared src file."""
    vecs = tfidf_vectors(strip_boilerplate([f["_text"] for f in feats]))
    edges = []
    n = len(feats)
    for i in range(n):
        a = feats[i]
        for j in range(i + 1, n):
            b = feats[j]
            ev = []
            if a["base_commit"] and a["base_commit"] == b["base_commit"] and a["repo"] == b["repo"]:
                ev.append(("same_base_commit", 1.0))
            if a["repo"] == b["repo"]:
                s = a["_sym_pairs"] & b["_sym_pairs"]
                s = {x for x in s if x[1] != "<new_file>"}
                if s:
                    ev.append(("same_symbol", float(len(s))))
                t = a["_test_pairs"] & b["_test_pairs"]
                if t:
                    ev.append(("same_test_def", float(len(t))))
                sf = a["_src_files"] & b["_src_files"]
                if sf:
                    ev.append(("same_src_file", float(len(sf))))
            cs = cosine(vecs[i], vecs[j])
            if cs >= text_hard:
                ev.append(("text_near_duplicate", cs))
            elif cs >= text_soft:
                ev.append(("text_similar", cs))
            for typ, w in ev:
                edges.append({"i": i, "j": j, "a": a["instance_id"], "b": b["instance_id"], "type": typ,
                              "weight": round(w, 4), "hard": typ in HARD_TYPES})
    return edges


def components(feats, edges):
    dsu = DSU(len(feats))
    for e in edges:
        if e["hard"]:
            dsu.union(e["i"], e["j"])
    comp = defaultdict(list)
    for i in range(len(feats)):
        comp[dsu.find(i)].append(i)
    return [comp[k] for k in sorted(comp)]


def load_splits(path):
    """-> {instance_id: split_name}.  Accepts {"train":[ids],...}, {"splits":{...}}, {id: split}, CSV(instance_id,split)."""
    if path.lower().endswith(".csv"):
        m = {}
        for r in read_rows(path):
            tid = r.get("instance_id") or r.get("task_id") or r.get("id")
            m[str(tid)] = str(r.get("split")).lower()
        return m
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and isinstance(obj.get("splits"), dict):
        obj = obj["splits"]
    m = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list):
                for tid in v:
                    m[str(tid)] = str(k).lower()
            elif isinstance(v, str):
                m[str(k)] = v.lower()
    elif isinstance(obj, list):
        for r in obj:
            m[str(r.get("instance_id") or r.get("task_id"))] = str(r.get("split")).lower()
    return m


def parse_sizes(s):
    out = {}
    for part in s.split(","):
        k, v = part.split("=")
        out[k.strip().lower()] = int(v)
    return out


def assign_groups(groups, feats, sizes, seed, heldout_policy, heldout_name):
    rnd = random.Random(seed)
    names = list(sizes)
    n_total = sum(len(g) for g in groups)
    tot = sum(sizes.values())
    cap = dict(sizes)
    if tot != n_total:  # rescale targets to the number of tasks (largest remainder)
        raw = {s: sizes[s] * n_total / float(tot) for s in names}
        cap = {s: int(math.floor(raw[s])) for s in names}
        rem = n_total - sum(cap.values())
        for s in sorted(names, key=lambda s: (-(raw[s] - cap[s]), names.index(s)))[:rem]:
            cap[s] += 1
    repos = Counter(f["repo_short"] for f in feats)
    target = {s: {r: cap[s] * repos[r] / float(n_total) for r in repos} for s in names}
    cur = {s: Counter() for s in names}
    cur_n = Counter()
    assign = {}

    def place(gi, s):
        for m in groups[gi]:
            assign[m] = s
            cur[s][feats[m]["repo_short"]] += 1
        cur_n[s] += len(groups[gi])

    placed = set()
    if heldout_policy == "newest" and heldout_name in cap:
        def newest(gi):
            ds = [feats[m]["created_at"] for m in groups[gi] if feats[m]["created_at"]]
            return max(ds) if ds else ""
        for gi in sorted(range(len(groups)), key=lambda g: (newest(g), g), reverse=True):
            if cur_n[heldout_name] >= cap[heldout_name]:
                break
            if cur_n[heldout_name] + len(groups[gi]) <= cap[heldout_name]:
                place(gi, heldout_name)
                placed.add(gi)
    order = sorted((gi for gi in range(len(groups)) if gi not in placed),
                   key=lambda gi: (-len(groups[gi]), rnd.random()))
    for gi in order:
        g = groups[gi]
        cands = [s for s in names if cur_n[s] + len(g) <= cap[s]]
        if not cands:
            cands = [max(names, key=lambda s: (cap[s] - cur_n[s], -names.index(s)))]

        def score(s):
            sc = 0.0
            for m in g:
                r = feats[m]["repo_short"]
                sc += (target[s][r] - cur[s][r]) / max(1.0, target[s][r])
            return sc / len(g) + (cap[s] - cur_n[s]) / float(max(1, cap[s]))
        best = max(cands, key=lambda s: (round(score(s), 9), -names.index(s)))
        place(gi, best)
    return assign, cap


def cmd_audit_split(args):
    feats = [task_features(r, args.snapshots_dir) for r in read_jsonl(args.tasks)]
    feats.sort(key=lambda f: f["instance_id"])
    idx = {f["instance_id"]: i for i, f in enumerate(feats)}
    edges = build_edges(feats, args.text_soft, args.text_hard)
    groups = components(feats, edges)
    demoted = False
    if max(len(g) for g in groups) > args.max_component_frac * len(feats) and any(e["type"] == "text_near_duplicate" for e in edges):
        for e in edges:
            if e["type"] == "text_near_duplicate":
                e["hard"] = False
        groups = components(feats, edges)
        demoted = True
    out = args.out
    L = ["# Leakage audit / grouped split (DESCRIPTIVE; no model involved)\n"]
    if demoted:
        L.append("NOTE: hard text-near-duplicate edges produced a group larger than %.0f%% of the tasks, so they were DEMOTED to soft edges "
                 "(raise --text-hard or inspect the most similar pairs below).\n" % (100 * args.max_component_frac))
    L.append("tasks=%d  symbols_mode=%s  text thresholds: soft>=%.2f hard>=%.2f\n" % (
        len(feats), dict(Counter(f["symbols_mode"] for f in feats)), args.text_soft, args.text_hard))
    c = Counter((e["type"], "HARD" if e["hard"] else "soft") for e in edges)
    L.append("## 1. Task-pair evidence found\n")
    L.append(md_table(["edge type", "strength", "pairs"], [[k[0], k[1], v] for k, v in sorted(c.items())]) if c else "No edges found.")
    sizes = Counter(len(g) for g in groups)
    L.append("\n## 2. Hard-edge groups (tasks that must stay in the same split)\n")
    L.append(md_table(["group size", "groups"], [[k, v] for k, v in sorted(sizes.items())]))
    multi = [g for g in groups if len(g) > 1]
    for g in multi[:40]:
        L.append("- " + ", ".join(feats[m]["instance_id"] for m in g))
    if max(len(g) for g in groups) > 0.2 * len(feats):
        L.append("\nWARNING: the largest hard group holds >20%% of tasks; thresholds are probably too loose for this data.")
    top = sorted((e for e in edges if e["type"] in ("text_similar", "text_near_duplicate")), key=lambda e: -e["weight"])[:10]
    if top:
        L.append("\n## 3. Most similar issue texts (cosine) -- eyeball these\n")
        L.append(md_table(["task A", "task B", "cosine", "type"], [[e["a"], e["b"], e["weight"], e["type"]] for e in top]))
    write_csv(os.path.join(out, "edges.csv"), ["task_a", "task_b", "type", "weight", "hard"],
              [[e["a"], e["b"], e["type"], e["weight"], int(e["hard"])] for e in edges])
    write_json(os.path.join(out, "groups.json"), [[feats[m]["instance_id"] for m in g] for g in groups])
    verdict = "NOT_RUN"
    if args.splits:
        split_of = load_splits(args.splits)
        unknown = sorted(t for t in split_of if t not in idx)
        unassigned = sorted(t for t in idx if t not in split_of)
        train_rx = re.compile(args.train_regex)
        L.append("\n## 4. Audit of existing split `%s`\n" % os.path.basename(args.splits))
        L.append("split sizes: %s" % dict(Counter(split_of.get(t, "(unassigned)") for t in idx)))
        if unknown:
            L.append("\nIDs in the split file but not in tasks.jsonl: %s" % unknown[:20])
        if unassigned:
            L.append("\nTasks without a split: %s" % unassigned[:20])
        cross = defaultdict(Counter)
        quarantine = defaultdict(set)
        for e in edges:
            sa, sb = split_of.get(e["a"]), split_of.get(e["b"])
            if not sa or not sb or sa == sb:
                continue
            key = tuple(sorted((sa, sb)))
            cross[key][(e["type"], "HARD" if e["hard"] else "soft")] += 1
            if e["hard"]:
                for t, s in ((e["a"], sa), (e["b"], sb)):
                    if train_rx.search(s):
                        quarantine["train_side_of_cross_split_hard_edge"].add(t)
        rows = []
        n_fail = n_warn = 0
        for key, cnt in sorted(cross.items()):
            for (typ, strength), v in sorted(cnt.items()):
                train_involved = any(train_rx.search(s) for s in key)
                if strength == "HARD":
                    status = "FAIL (train-derived priors can leak into evaluation)" if train_involved else "WARN (dev tuning can leak into held-out)"
                    n_fail += 1 if train_involved else 0
                    n_warn += 0 if train_involved else 1
                else:
                    status = "info"
                rows.append([" <-> ".join(key), typ, strength, v, status])
        L.append("\n" + (md_table(["split pair", "evidence", "strength", "pairs", "status"], rows) if rows else "No cross-split evidence found."))
        spanning = [g for g in multi if len({split_of.get(feats[m]["instance_id"]) for m in g}) > 1]
        if spanning:
            L.append("\nHard groups that span splits (move or quarantine):")
            for g in spanning[:40]:
                L.append("- " + ", ".join("%s[%s]" % (feats[m]["instance_id"], split_of.get(feats[m]["instance_id"])) for m in g))
        q = sorted(quarantine["train_side_of_cross_split_hard_edge"])
        L.append("\nSuggested quarantine (train-side members: do NOT derive priors/playbooks/few-shots from these): %s" % (q or "none"))
        verdict = "FAIL" if n_fail else ("WARN" if n_warn else "PASS")
        L.append("\n**Verdict on hard evidence: %s**  (FAIL rows=%d, WARN rows=%d). Soft edges are informational.\n" % (verdict, n_fail, n_warn))
        rows = []
        for s in sorted(set(split_of.values())):
            ids = [t for t, v in split_of.items() if v == s and t in idx]
            ds = sorted(feats[idx[t]]["created_at"] for t in ids if feats[idx[t]]["created_at"])
            rc = Counter(feats[idx[t]]["repo_short"] for t in ids)
            rows.append([s, len(ids), ds[0][:10] if ds else "", ds[len(ds) // 2][:10] if ds else "", ds[-1][:10] if ds else "",
                         ", ".join("%s:%d" % kv for kv in sorted(rc.items()))])
        L.append(md_table(["split", "n", "oldest", "median", "newest", "repos"], rows))
        write_json(os.path.join(out, "audit_existing_split.json"),
                   {"verdict": verdict, "quarantine": q, "cross_split": {" <-> ".join(k): {"%s/%s" % kk: vv for kk, vv in v.items()} for k, v in cross.items()}})
    if args.make_split:
        sizes_t = parse_sizes(args.sizes)
        held = args.heldout_name.lower()
        assign, cap = assign_groups(groups, feats, sizes_t, args.seed, args.heldout_policy, held)
        splits = {s: sorted(feats[m]["instance_id"] for m, v in assign.items() if v == s) for s in sizes_t}
        write_json(os.path.join(out, "splits_new.json"), {"seed": args.seed, "policy": args.heldout_policy, "targets": cap, "splits": splits})
        L.append("\n## 5. New grouped, repo-stratified split (seed=%d, heldout policy=%s)\n" % (args.seed, args.heldout_policy))
        rows = []
        for s in sizes_t:
            rc = Counter(feats[m]["repo_short"] for m, v in assign.items() if v == s)
            ds = sorted(feats[m]["created_at"] for m, v in assign.items() if v == s and feats[m]["created_at"])
            rows.append([s, cap[s], len(splits[s]), ", ".join("%s:%d" % kv for kv in sorted(rc.items())),
                         ds[0][:10] if ds else "", ds[-1][:10] if ds else ""])
        L.append(md_table(["split", "target", "realised", "repos", "oldest", "newest"], rows))
        bad = 0
        for e in edges:
            if e["hard"] and assign[e["i"]] != assign[e["j"]]:
                bad += 1
        L.append("\nHard cross-split pairs in the new split: %d (must be 0)." % bad)
        soft_cross = Counter(e["type"] for e in edges if (not e["hard"]) and assign[e["i"]] != assign[e["j"]])
        L.append("Soft cross-split pairs (informational): %s" % dict(soft_cross))
    write_text(os.path.join(out, "audit_report.md"), "\n".join(L) + "\n")
    print("audit-split: wrote %s/audit_report.md  hard-groups=%d  verdict=%s" % (out, len(groups), verdict))


# ----------------------------------------------------------------------------
# 7. scan a submission bundle for copied reference patches / tests
# ----------------------------------------------------------------------------

TRIVIAL_RE = re.compile(r"^(import \S|from \S+ import |return$|pass$|else:$|try:$|[\)\]\}]+,?$|#)")
BUNDLE_EXT = (".yaml", ".yml", ".md", ".txt", ".py", ".json", ".toml", ".cfg", ".sh")


def significant(line, minlen):
    n = re.sub(r"\s+", " ", line.strip())
    if len(n) < minlen or TRIVIAL_RE.match(n):
        return None
    return n


def line_shingles(lines, k, minlen):
    sig = [(i + 1, significant(l, minlen)) for i, l in enumerate(lines)]
    sig = [(i, n) for i, n in sig if n]
    out = []
    for j in range(len(sig) - k + 1):
        key = "\n".join(n for _i, n in sig[j:j + k])
        out.append((sig[j][0], hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()))
    return out


def changed_lines(diff_text):
    out = []
    for l in (diff_text or "").split("\n"):
        if l.startswith("+++") or l.startswith("---"):
            continue
        if l.startswith("+") or l.startswith("-"):
            out.append(l[1:])
    return out


def iter_bundle_files(path):
    if os.path.isdir(path):
        for root, _d, files in sorted(os.walk(path)):
            for fn in sorted(files):
                if fn.lower().endswith(BUNDLE_EXT):
                    p = os.path.join(root, fn)
                    if os.path.getsize(p) <= 5 << 20:
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            yield os.path.relpath(p, path), f.read()
    else:
        with zipfile.ZipFile(path) as z:
            for info in sorted(z.infolist(), key=lambda i: i.filename):
                if info.filename.lower().endswith(BUNDLE_EXT) and info.file_size <= 5 << 20:
                    yield info.filename, z.read(info).decode("utf-8", errors="replace")


def cmd_scan_bundle(args):
    ids = None
    if args.ids:
        ids = set(x.strip() for x in args.ids.split(",") if x.strip())
    exclude = set()
    if args.exclude_ids_file:
        with open(args.exclude_ids_file, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        exclude = set(json.loads(txt)) if txt.startswith("[") else set(x.strip() for x in txt.splitlines() if x.strip())
    ref = defaultdict(set)  # shingle hash -> {task ids}
    n_tasks = 0
    for row in read_jsonl(args.tasks):
        tid = str(field(row, "instance_id"))
        if (ids is not None and tid not in ids) or tid in exclude:
            continue
        n_tasks += 1
        for src_name in ("patch", "test_patch"):
            for _ln, h in line_shingles(changed_lines(str(field(row, src_name))), args.k, args.min_len):
                ref[h].add(tid)
    hits = []
    n_files = 0
    for name, text in iter_bundle_files(args.bundle):
        n_files += 1
        for ln, h in line_shingles(text.split("\n"), args.k, args.min_len):
            if h in ref:
                hits.append((name, ln, sorted(ref[h])))
    L = ["# Bundle leak scan: reference patch/test-patch lines found in the submission bundle\n",
         "bundle=%s files_scanned=%d reference_tasks=%d reference_shingles=%d  (k=%d consecutive significant changed lines, min_len=%d)\n" % (
             args.bundle, n_files, n_tasks, len(ref), args.k, args.min_len)]
    if hits:
        L.append("**HITS: %d** -- review each; a hit means text from a reference fix/test of the listed task(s) is inside the bundle.\n" % len(hits))
        L.append(md_table(["file", "line", "matching task ids"], [[h[0], h[1], ",".join(h[2][:5])] for h in hits[:200]]))
    else:
        L.append("No hits.")
    write_text(os.path.join(args.out, "bundle_leak_scan.md"), "\n".join(L) + "\n")
    print("scan-bundle: hits=%d (report: %s/bundle_leak_scan.md)" % (len(hits), args.out))
    return 2 if hits else 0


# ----------------------------------------------------------------------------
# 8. run-result normalisation, failure classification, summarisation
#    (MEASURED only if the rows you feed in come from real runs of the official harness)
# ----------------------------------------------------------------------------

RES_ALIASES = {
    "task_id": ["task_id", "instance_id", "id"],
    "arm": ["arm", "variant", "config", "agent", "experiment"],
    "seed": ["seed", "replicate", "rep", "run"],
    "resolved": ["resolved", "passed", "success", "is_resolved"],
    "repo": ["repo_short", "repo"],
    "non_empty_patch": ["non_empty_patch", "nonempty_patch", "has_patch"],
    "touches_src": ["touches_src"],
    "patch_applies": ["patch_applies", "applies_cleanly"],
    "touched_tests": ["touched_tests", "touches_tests_or_config"],
    "submitted": ["submitted", "submitted_by_tool"],
    "hit_cap": ["hit_cap", "agent_timeout"],
    "context_overflow": ["context_overflow"],
    "verify_timeout": ["verify_timeout", "verification_timeout"],
    "ran_test_after_edit": ["ran_test_after_edit", "verified_after_edit"],
    "loc_file_hit": ["loc_file_hit"],
    "p2p_regressed": ["p2p_regressed"],
    "duration_s": ["duration_s", "wall_s", "agent_s", "t_agent_s", "duration"],
    "tool_calls": ["tool_calls", "n_tool_calls"],
    "turns": ["turns", "n_turns"],
    "patch_lines": ["patch_lines"],
    "malformed_calls": ["malformed_calls"],
    "error": ["error", "error_message"],
    "failure_class": ["failure_class", "outcome_class"],
}
BOOL_KEYS = ["resolved", "non_empty_patch", "touches_src", "patch_applies", "touched_tests", "submitted",
             "hit_cap", "context_overflow", "verify_timeout", "ran_test_after_edit", "loc_file_hit", "p2p_regressed"]
NUM_KEYS = ["duration_s", "tool_calls", "turns", "patch_lines", "malformed_calls", "seed"]
TRUE_SET = {"1", "true", "t", "yes", "y", "pass", "passed", "resolved"}
FALSE_SET = {"0", "false", "f", "no", "n", "fail", "failed", "unresolved"}


def to_bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None
        return bool(v)
    s = str(v).strip().lower()
    if s in TRUE_SET:
        return True
    if s in FALSE_SET:
        return False
    return None


def to_float(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def norm_result(row):
    out = {"_raw": row}
    for key, names in RES_ALIASES.items():
        val = None
        for n in names:
            if n in row and row[n] not in (None, ""):
                val = row[n]
                break
        if key in BOOL_KEYS:
            out[key] = to_bool(val)
        elif key in NUM_KEYS:
            out[key] = to_float(val)
        else:
            out[key] = None if val is None else str(val)
    if out["task_id"] is None or out["arm"] is None or out["resolved"] is None:
        raise SystemExit("result row needs task_id, arm and resolved (got keys: %s)" % sorted(row)[:15])
    err = (out["error"] or "").lower()
    if out["hit_cap"] is None and err:
        out["hit_cap"] = ("timeout" in err or "exceeded" in err)
    if out["context_overflow"] is None and err:
        if "context" in err and ("length" in err or "overflow" in err or "exceed" in err or "32768" in err):
            out["context_overflow"] = True
    return out


def has_src(r):
    if r.get("touches_src") is not None:
        return r["touches_src"]
    return r.get("non_empty_patch")


def valid_patch(r):
    hs = has_src(r)
    if hs is None:
        return None
    if not hs:
        return False
    return r.get("patch_applies") is not False


def no_patch(r):
    hs = has_src(r)
    return None if hs is None else (not hs)


# mutually exclusive PRIMARY outcome; process flags are separate and non-exclusive (see plan, section F)
OUTCOME_CLASSES = ["resolved", "context_overflow", "verification_timeout", "agent_timeout_no_patch",
                   "agent_timeout_patch_failed", "no_patch_other", "test_or_config_edit_only",
                   "patch_not_applicable", "wrong_files", "regression_p2p", "right_file_tests_fail",
                   "patch_failed_unknown"]


def classify(r):
    if r.get("failure_class"):
        return r["failure_class"]
    if r["resolved"]:
        return "resolved"
    if r.get("context_overflow"):
        return "context_overflow"
    if r.get("verify_timeout"):
        return "verification_timeout"
    hs = has_src(r)
    if r.get("hit_cap"):
        return "agent_timeout_patch_failed" if hs else "agent_timeout_no_patch"
    if hs is False:
        if r.get("touched_tests") and r.get("non_empty_patch"):
            return "test_or_config_edit_only"
        return "no_patch_other"
    if r.get("patch_applies") is False:
        return "patch_not_applicable"
    if r.get("loc_file_hit") is False:
        return "wrong_files"
    if r.get("p2p_regressed"):
        return "regression_p2p"
    if r.get("loc_file_hit"):
        return "right_file_tests_fail"
    return "patch_failed_unknown"


def process_flags(r, large_patch_lines):
    flags = []
    if has_src(r) and r.get("ran_test_after_edit") is False:
        flags.append("edit_without_verification")
    if (r.get("malformed_calls") or 0) > 0:
        flags.append("malformed_tool_calls")
    if (r.get("patch_lines") or 0) > large_patch_lines:
        flags.append("large_patch")
    if r.get("touched_tests"):
        flags.append("touched_tests_or_config")
    if r.get("submitted") is False and has_src(r):
        flags.append("patch_not_submitted_by_tool")
    return flags


def per_task_map(task_rows, fn):
    out = {}
    for t, rs in task_rows.items():
        xs = [fn(r) for r in rs]
        xs = [x for x in xs if x is not None]
        if xs:
            out[t] = sum(1.0 if x else 0.0 for x in xs) / len(xs)
    return out


def rate_cell(per_task, B, seed):
    vals = [per_task[t] for t in sorted(per_task)]
    if not vals:
        return "n/a"
    m = sum(vals) / len(vals)
    lo, hi = boot_mean_ci(vals, B=B, seed=seed)
    return "%.3f [%.3f, %.3f] (n=%d)" % (m, lo, hi, len(vals))


def paired(per_a, per_b, B, seed):
    common = sorted(set(per_a) & set(per_b))
    d = [per_b[t] - per_a[t] for t in common]
    wins = sum(1 for x in d if x > 1e-12)
    losses = sum(1 for x in d if x < -1e-12)
    lo, hi = boot_mean_ci(d, B=B, seed=seed) if d else (float("nan"), float("nan"))
    return {"n_common": len(common), "mean_diff": (sum(d) / len(d)) if d else float("nan"), "ci_lo": lo, "ci_hi": hi,
            "wins_B": wins, "losses_B": losses, "ties": len(d) - wins - losses,
            "p_two_sided": sign_test_p(wins, losses, "two-sided"), "p_B_better": sign_test_p(wins, losses, "greater"),
            "post_prob_B_better": post_prob_b_better(wins, losses)}


def load_feature_table(path):
    if not path:
        return {}
    out = {}
    for r in read_rows(path):
        out[str(r.get("instance_id"))] = r
    return out


def size_bucket(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "unknown"
    return "<=10" if x <= 10 else ("11-30" if x <= 30 else ">30")


def nsrc_bucket(v):
    try:
        x = int(float(v))
    except (TypeError, ValueError):
        return "unknown"
    return "0" if x == 0 else ("1" if x == 1 else "2+")


def cmd_summarize(args):
    rows = []
    for p in args.results:
        for r in read_rows(p):
            rows.append(norm_result(r))
    if not rows:
        raise SystemExit("no result rows")
    feat = load_feature_table(args.features)
    arms = sorted({r["arm"] for r in rows})
    data = {a: defaultdict(list) for a in arms}
    for r in rows:
        data[r["arm"]][r["task_id"]].append(r)
    B, seed = args.boot, args.seed
    L = ["# Run summary (statistics are only as real as the rows supplied)\n",
         "rows=%d  arms=%s  bootstrap=%d resamples over TASKS (seeds of one task are averaged first)\n" % (len(rows), arms, B)]
    L.append("Metric definitions: `dev_resolved` = official Phase-2 verifier on a DEV task (a proxy, NOT the leaderboard score); "
             "`nonempty_src_patch` = captured diff touches >=1 non-test .py source file; `valid_patch` = nonempty_src_patch AND applies cleanly; "
             "`no_patch` = no source change captured; `hit_cap` = agent loop ended by the time/call/turn cap.\n")
    # --- table 1
    hdr = ["arm", "tasks", "runs", "dev_resolved", "nonempty_src_patch", "valid_patch", "no_patch", "hit_cap", "ctx_overflow",
           "dur_s median/p90", "tool_calls median/p90"]
    t1 = []
    summary = {}
    for a in arms:
        tr = data[a]
        runs = [r for rs in tr.values() for r in rs]
        durs = describe([r["duration_s"] for r in runs])
        calls = describe([r["tool_calls"] for r in runs])
        row = [a, len(tr), len(runs),
               rate_cell(per_task_map(tr, lambda r: r["resolved"]), B, seed),
               rate_cell(per_task_map(tr, has_src), B, seed),
               rate_cell(per_task_map(tr, valid_patch), B, seed),
               rate_cell(per_task_map(tr, no_patch), B, seed),
               rate_cell(per_task_map(tr, lambda r: r.get("hit_cap")), B, seed),
               rate_cell(per_task_map(tr, lambda r: r.get("context_overflow")), B, seed),
               ("%s / %s" % (fmt(durs.get("median", float("nan"))), fmt(durs.get("p90", float("nan"))))) if durs.get("n") else "n/a",
               ("%s / %s" % (fmt(calls.get("median", float("nan"))), fmt(calls.get("p90", float("nan"))))) if calls.get("n") else "n/a"]
        t1.append(row)
        k = sum(1 for r in runs if r["resolved"])
        w = wilson(k, len(runs))
        summary[a] = {"tasks": len(tr), "runs": len(runs), "resolved_runs": k, "wilson_runs": [w[0], w[1]],
                      "duration": durs, "tool_calls": calls}
    L.append("## 1. Per-arm metrics (mean over tasks, task-bootstrap 95% CI)\n")
    L.append(md_table(hdr, t1))
    L.append("\nWilson 95% interval on pooled runs (assumes independent runs; anti-conservative with repeated seeds): " +
             "; ".join("%s %d/%d [%.3f, %.3f]" % (a, summary[a]["resolved_runs"], summary[a]["runs"], summary[a]["wilson_runs"][0], summary[a]["wilson_runs"][1]) for a in arms))
    # --- table 2: failure classes
    L.append("\n## 2. Primary outcome class per run (decision tree in the plan, section F)\n")
    cls_by_arm = {a: Counter(classify(r) for rs in data[a].values() for r in rs) for a in arms}
    all_cls = [c for c in OUTCOME_CLASSES if any(c in cls_by_arm[a] for a in arms)] + \
        sorted({c for a in arms for c in cls_by_arm[a]} - set(OUTCOME_CLASSES))
    L.append(md_table(["outcome_class"] + arms, [[c] + [cls_by_arm[a].get(c, 0) for a in arms] for c in all_cls]))
    flag_by_arm = {a: Counter(f for rs in data[a].values() for r in rs for f in process_flags(r, args.large_patch_lines)) for a in arms}
    all_flags = sorted({f for a in arms for f in flag_by_arm[a]})
    if all_flags:
        L.append("\nProcess flags (non-exclusive; large_patch = patch_lines > %d):\n" % args.large_patch_lines)
        L.append(md_table(["flag"] + arms, [[f] + [flag_by_arm[a].get(f, 0) for a in arms] for f in all_flags]))
    # --- table 3: strata
    strata = [("repo", lambda t, r: (feat.get(t, {}).get("repo_short") or r.get("repo") or "unknown")),
              ("issue_type_heuristic", lambda t, r: feat.get(t, {}).get("issue_type_heuristic") or "unknown"),
              ("src_files_in_reference_patch", lambda t, r: nsrc_bucket(feat.get(t, {}).get("n_src_files"))),
              ("reference_lines_changed", lambda t, r: size_bucket(feat.get(t, {}).get("lines_changed_src")))]
    L.append("\n## 3. dev_resolved by stratum (tasks resolved / tasks, per-task mean) and failure classes by repo\n")
    for sname, skey in strata:
        values = sorted({skey(t, rs[0]) for a in arms for t, rs in data[a].items()})
        if len(values) <= 1 and values == ["unknown"]:
            L.append("(stratum `%s` unavailable: pass --features task_features.csv from `profile`)\n" % sname)
            continue
        trs = []
        for v in values:
            row = [v]
            for a in arms:
                ts = [t for t, rs in data[a].items() if skey(t, rs[0]) == v]
                pm = per_task_map({t: data[a][t] for t in ts}, lambda r: r["resolved"])
                row.append("%.1f/%d" % (sum(pm.values()), len(pm)) if pm else "-")
            trs.append(row)
        L.append("**%s**\n\n%s\n" % (sname, md_table([sname] + arms, trs)))
    for sname, skey in strata[:2]:
        for a in arms:
            vals = sorted({skey(t, rs[0]) for t, rs in data[a].items()})
            if vals == ["unknown"]:
                continue
            cnt = {v: Counter(classify(r) for t, rs in data[a].items() if skey(t, rs[0]) == v for r in rs) for v in vals}
            cls_here = [c for c in all_cls if any(c in cnt[v] for v in vals)]
            L.append("**failure outcome classes by %s, arm `%s` (runs)**\n\n%s\n" % (
                sname, a, md_table(["outcome_class"] + vals, [[c] + [cnt[v].get(c, 0) for v in vals] for c in cls_here])))
    # --- table 4: paired comparisons
    base = args.baseline or arms[0]
    L.append("## 4. Paired comparisons vs baseline `%s` (same tasks, per-task mean over seeds)\n" % base)
    prow = []
    paired_out = {}
    pm_base = per_task_map(data[base], lambda r: r["resolved"])
    for a in arms:
        if a == base:
            continue
        pr = paired(pm_base, per_task_map(data[a], lambda r: r["resolved"]), B, seed)
        paired_out[a] = pr
        prow.append([a, pr["n_common"], pr["mean_diff"], "[%.3f, %.3f]" % (pr["ci_lo"], pr["ci_hi"]), pr["wins_B"], pr["losses_B"],
                     pr["ties"], pr["p_two_sided"], pr["p_B_better"], pr["post_prob_B_better"]])
    L.append(md_table(["arm B", "common tasks", "mean diff (B-A)", "95% CI (task bootstrap)", "B wins", "B losses", "ties",
                       "exact sign p (2-sided)", "exact p (B better)", "P(B better | uniform prior)"], prow) if prow else "Only one arm.")
    L.append("\nWith one seed per task this is the exact McNemar test. `P(B better)` ignores ties and is a screening quantity, not a significance claim.")
    if args.aa:
        a1, a2 = args.aa.split(",")
        pr = paired(per_task_map(data[a1], lambda r: r["resolved"]), per_task_map(data[a2], lambda r: r["resolved"]), B, seed)
        L.append("\n**A/A noise floor** (`%s` vs `%s`, identical configuration): wins=%d losses=%d ties=%d mean diff=%.3f. "
                 "Any ablation whose net wins are not clearly larger than this is indistinguishable from run-to-run noise." % (
                     a1, a2, pr["wins_B"], pr["losses_B"], pr["ties"], pr["mean_diff"]))
        paired_out["__AA__"] = pr
    write_text(os.path.join(args.out, "summary.md"), "\n".join(L) + "\n")
    write_json(os.path.join(args.out, "summary.json"), {"arms": summary, "paired_vs_baseline": paired_out, "baseline": base})
    print("summarize: wrote %s/summary.md arms=%s" % (args.out, arms))


# ----------------------------------------------------------------------------
# 9. 12-hour budget planner (inputs: measured per-task durations from a real long-cap run)
# ----------------------------------------------------------------------------


def cmd_budget(args):
    rows = []
    for p in args.results:
        for r in read_rows(p):
            nr = norm_result(r)
            if args.arm and nr["arm"] != args.arm:
                continue
            rows.append(nr)
    rows = [r for r in rows if r["duration_s"] is not None]
    if not rows:
        raise SystemExit("no rows with duration_s (and matching --arm)")
    M = len(rows)
    N = args.n_tasks
    S = args.server_start_min
    setup = args.setup_min
    setup_cols = [to_float(r["_raw"].get("setup_s")) for r in rows]
    if not args.setup_min_fixed and all(x is not None for x in setup_cols):
        setup = (sum(setup_cols) / len(setup_cols)) / 60.0
    limit = args.limit_min
    cap_meas_s = args.measured_cap_min * 60.0 if args.measured_cap_min else max(r["duration_s"] for r in rows)
    ra_cols = sorted({int(m.group(1)) for r in rows for k in r["_raw"] for m in [re.match(r"^resolved_at_(\d+)$", str(k))] if m})
    durs = [r["duration_s"] for r in rows]
    n_cap = sum(1 for r in rows if r.get("hit_cap"))
    L = ["# 12-hour budget planner\n",
         "Measured rows: %d (arm=%s). Planning inputs: N=%d tasks, server start S=%.1f min, per-task setup=%.2f min, limit=%.0f min, safety margin=%.0f min." % (
             M, args.arm or "all", N, S, setup, limit, args.margin_min),
         "Server start and setup are PLANNING PARAMETERS (third-party estimates unless you replace them with measured values); durations come from your rows.\n",
         "Observed: median duration %.0f s, mean %.0f s, hit_cap fraction %s, measured cap %.0f s.\n" % (
             quantile(sorted(durs), .5), sum(durs) / M, ("%.3f" % (n_cap / M)) if any(r.get("hit_cap") is not None for r in rows) else "n/a (no hit_cap/error column)", cap_meas_s)]
    caps = [float(x) for x in args.caps_min.split(",")]
    table = []
    res_by_cap = {}
    prev = None
    for c in caps:
        cs = c * 60.0
        if cs > cap_meas_s + 1e-6:
            table.append([c, "", "", "", "", "", "", "needs a run with cap >= %.1f min (no extrapolation)" % c])
            continue
        d = [min(x, cs) for x in durs]
        mean_d = sum(d) / M / 60.0
        e_t = S + N * (mean_d + setup)
        t_max = S + N * (c + setup)
        rnd = random.Random(args.seed + int(c * 100))
        ts = []
        for _b in range(args.boot):
            tot = 0.0
            for _i in range(N):
                tot += d[rnd.randrange(M)]
            ts.append(S + tot / 60.0 + N * setup)
        ts.sort()
        p_over = sum(1 for t in ts if t > limit) / float(len(ts))
        y = None
        if int(round(cs)) in ra_cols:
            vals = [to_float(r["_raw"].get("resolved_at_%d" % int(round(cs)))) for r in rows]
            vals = [v for v in vals if v is not None]
            y = sum(vals) / len(vals) if vals else None
        elif abs(cs - cap_meas_s) < 1.0:
            y = sum(1.0 if r["resolved"] else 0.0 for r in rows) / M
        k_fit = int(math.floor((limit - S) / (mean_d + setup))) if (mean_d + setup) > 0 else N
        graceful = (y * min(N, k_fit)) if y is not None else None
        feasible = (p_over <= args.eps) and (e_t + args.margin_min <= limit)
        marg = ""
        if prev is not None and y is not None and prev[1] is not None and e_t > prev[0]:
            marg = "%.2f" % ((y - prev[1]) * N / ((e_t - prev[0]) / 60.0))
        if y is not None:
            prev = (e_t, y)
        res_by_cap[c] = {"E_T_min": e_t, "T_max_min": t_max, "p95": quantile(ts, .95), "p99": quantile(ts, .99), "P_over": p_over,
                         "Y": y, "feasible": feasible, "tasks_fit": k_fit}
        table.append([c, "%.2f" % (t_max / 60.0), "%.2f" % (e_t / 60.0), "%.2f / %.2f" % (quantile(ts, .95) / 60.0, quantile(ts, .99) / 60.0),
                      "%.4f" % p_over, ("%.3f" % y) if y is not None else "n/a",
                      ("%.1f" % (y * N)) if y is not None else "n/a",
                      ("feasible" if feasible else "NOT feasible") + (", marginal resolved/extra-hour=%s" % marg if marg else "") +
                      (", graceful-objective E[resolved]=%.1f (tasks that fit=%d)" % (graceful, k_fit) if graceful is not None else "")])
    L.append(md_table(["cap (min)", "worst case T_max (h)", "E[T] (h)", "bootstrap p95 / p99 T (h)", "P(T > limit)", "Y(cap)=resolved frac",
                       "E[resolved] of N", "verdict"], table))
    L.append("\nT_max assumes every task runs to the cap. E[T] and the bootstrap resample the MEASURED duration distribution truncated at each cap "
             "(valid only if the agent's behaviour before the cap does not depend on the stated cap; the harness states the budget in the task message, "
             "so confirm any chosen cap with one real run). Y(cap) needs `resolved_at_<seconds>` columns from CPU re-grading of patch snapshots.")
    if len(ra_cols) >= 2:
        L.append("\n## Conditional yield (hazard) from patch snapshots re-graded at each time\n")
        hz = []
        for a, b in zip(ra_cols[:-1], ra_cols[1:]):
            unresolved = [r for r in rows if to_float(r["_raw"].get("resolved_at_%d" % a)) == 0.0]
            resolved = [r for r in rows if to_float(r["_raw"].get("resolved_at_%d" % a)) == 1.0]
            gain = sum(1 for r in unresolved if to_float(r["_raw"].get("resolved_at_%d" % b)) == 1.0)
            loss = sum(1 for r in resolved if to_float(r["_raw"].get("resolved_at_%d" % b)) == 0.0)
            lo, hi = wilson(gain, len(unresolved))
            hz.append(["%d-%d s" % (a, b), len(unresolved), gain, "%.3f [%.3f, %.3f]" % ((gain / len(unresolved)) if unresolved else float("nan"), lo, hi),
                       len(resolved), loss])
        L.append(md_table(["interval", "unresolved at start", "became resolved", "P(gain) [Wilson]", "resolved at start", "became unresolved"], hz))
        L.append("\nStop/continue rule: keep spending time only while the conditional yield per extra minute exceeds the shadow price "
                 "lambda = marginal resolved tasks per hour in the table above.")
    if args.evidence_time_col and args.evidence_resolved_col:
        ev = [(to_float(r["_raw"].get(args.evidence_time_col)), to_float(r["_raw"].get(args.evidence_resolved_col)), r) for r in rows]
        pos = [(t, y, r) for t, y, r in ev if t is not None and y is not None]
        L.append("\n## Stopping-rule predicate evaluation (`%s`, graded snapshot `%s`)\n" % (args.evidence_time_col, args.evidence_resolved_col))
        if pos:
            k = sum(1 for _t, y, _r in pos if y == 1.0)
            lo, hi = wilson(k, len(pos))
            saved = sorted(max(0.0, r["duration_s"] - t) for t, _y, r in pos)
            harm = sum(1 for t, y, r in pos if y == 1.0 and not r["resolved"])
            gain = sum(1 for t, y, r in pos if y == 0.0 and r["resolved"])
            L.append(md_table(["predicate true in", "precision at stop [Wilson]", "median time saved (s)", "total time saved (min)",
                               "final resolved but stop-time not (continuing helped)", "stop-time resolved but final not (continuing hurt)"],
                              [["%d/%d tasks" % (len(pos), M), "%d/%d = %.3f [%.3f, %.3f]" % (k, len(pos), k / len(pos), lo, hi),
                                quantile(saved, .5), sum(saved) / 60.0, gain, harm]]))
        else:
            L.append("predicate never true / columns empty")
    write_text(os.path.join(args.out, "budget.md"), "\n".join(L) + "\n")
    write_json(os.path.join(args.out, "budget.json"), {"N": N, "S_min": S, "setup_min": setup, "limit_min": limit, "by_cap": {str(k): v for k, v in res_by_cap.items()}})
    print("budget: wrote %s/budget.md" % args.out)


def cmd_budget_arith(args):
    """Pure arithmetic from the stated constraints (no measurements): worst-case wall clock per cap and how many tasks may hit the cap."""
    S, s, lim, mar = args.server_start_min, args.setup_min, args.limit_min, args.margin_min
    caps = [float(x) for x in args.caps_min.split(",")]
    L = ["# Budget arithmetic (planning formulas; parameters are inputs, not measurements)\n",
         "T_max(c) = S + N*(c + s)   [every task runs to the cap]   with S=%.1f min server start, s=%.2f min setup per task, limit=%.0f min, margin=%.0f min.\n" % (S, s, lim, mar)]
    rows = []
    for n in [int(x) for x in args.n_tasks.split(",")]:
        rows.append([n] + ["%.2f" % ((S + n * (c + s)) / 60.0) for c in caps])
    L.append("Worst-case wall clock in HOURS:\n\n" + md_table(["N tasks"] + ["cap %g min" % c for c in caps], rows))
    L.append("\nh_max(c, m) = (limit - margin - S - N*(m + s)) / (c - m): the largest number of tasks that may run to the cap c while the remaining tasks "
             "average m minutes, if the total must stay inside limit - margin.\n")
    for n in [int(x) for x in args.n_tasks.split(",")]:
        rows = []
        for m in [float(x) for x in args.mean_other_min.split(",")]:
            rows.append(["m=%g min" % m] + [max(0.0, (lim - mar - S - n * (m + s)) / (c - m)) if c > m else float("nan") for c in caps])
        L.append("N=%d\n\n%s\n" % (n, md_table(["mean of the other tasks"] + ["cap %g min" % c for c in caps], rows)))
    write_text(os.path.join(args.out, "budget_arith.md"), "\n".join(L) + "\n")
    print("budget-arith: wrote %s/budget_arith.md" % args.out)


# ----------------------------------------------------------------------------
# 10. design calculation: power / false-promotion rate of paired ablations (ASSUMPTION-DRIVEN)
# ----------------------------------------------------------------------------


def _expit(x):
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def sim_power(n, k, p0, icc, odds_ratio, alpha, screen_alpha, min_wins, sims, seed):
    rnd = random.Random(seed)
    kappa = (1.0 - icc) / icc
    a, b = p0 * kappa, (1.0 - p0) * kappa
    lor = math.log(odds_ratio)
    rej = scr = 0
    disc = 0
    for _ in range(sims):
        wins = losses = 0
        for _t in range(n):
            q = rnd.betavariate(a, b)
            qb = _expit(_logit(q) + lor)
            sa = sum(1 for _s in range(k) if rnd.random() < q)
            sb = sum(1 for _s in range(k) if rnd.random() < qb)
            if sb > sa:
                wins += 1
            elif sb < sa:
                losses += 1
        disc += wins + losses
        if wins > losses and sign_test_p(wins, losses, "two-sided") <= alpha:
            rej += 1
        if wins >= min_wins and sign_test_p(wins, losses, "greater") <= screen_alpha:
            scr += 1
    return rej / float(sims), scr / float(sims), disc / float(sims)


def cmd_power(args):
    ns = [int(x) for x in args.n.split(",")]
    ks = [int(x) for x in args.seeds.split(",")]
    p0s = [float(x) for x in args.p0.split(",")]
    iccs = [float(x) for x in args.icc.split(",")]
    ors = [float(x) for x in args.odds_ratio.split(",")]
    L = ["# Design calculation: how many tasks does a paired ablation need? (SIMULATION UNDER ASSUMPTIONS; not a result about Gemma)\n",
         "Model: each task has a latent solve probability q ~ Beta with mean p0 and intra-task correlation ICC (higher ICC = more tasks that are "
         "always/never solved); arm B multiplies the odds by OR; outcomes are Bernoulli per seed; per-task win/loss = which arm solved more seeds; "
         "ties dropped; exact sign test. `power` = P(two-sided p<=%.2f and B better); `screen` = P(one-sided p<=%.2f and wins>=%d) -- the lenient "
         "screening rule proposed in the plan; at OR=1 `screen` is the false-promotion rate. sims=%d per cell, seed=%d.\n" % (
             args.alpha, args.screen_alpha, args.min_wins, args.sims, args.seed)]
    rows = []
    for n in ns:
        for k in ks:
            for p0 in p0s:
                for icc in iccs:
                    for orr in ors:
                        pw, sc, disc = sim_power(n, k, p0, icc, orr, args.alpha, args.screen_alpha, args.min_wins, args.sims,
                                                 args.seed + n * 7 + k * 13 + int(p0 * 1000) + int(icc * 100) + int(orr * 10))
                        rows.append([n, k, p0, icc, orr, "%.2f" % disc, "%.3f" % pw, "%.3f" % sc])
    L.append(md_table(["tasks n", "seeds k", "baseline p0", "ICC", "odds ratio", "mean discordant tasks", "power", "screen"], rows))
    write_text(os.path.join(args.out, "power.md"), "\n".join(L) + "\n")
    print("power: wrote %s/power.md (%d cells)" % (args.out, len(rows)))


# ----------------------------------------------------------------------------
# 11. selftest on a SYNTHETIC fixture (proves the code runs; numbers are meaningless)
# ----------------------------------------------------------------------------

_BASE_PY = ("import os\n\nclass Router:\n    def add(self, x):\n        return x + 1\n\n    def remove(self, x):\n"
            "        y = x - 1\n        return y\n\n\ndef helper(a):\n    return a * 2\n")


def _mk_diff(path, old, new, ctx=None):
    import difflib
    ud = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "a/" + path, "b/" + path, lineterm="", n=2))
    if ctx:
        ud = [(l + " " + ctx) if l.startswith("@@") else l for l in ud]
    return "diff --git a/%s b/%s\n" % (path, path) + "\n".join(ud) + "\n"


def make_synthetic(root, n=40, seed=7):
    rnd = random.Random(seed)
    os.makedirs(root, exist_ok=True)
    repos = [("fastapi/fastapi", "fastapi"), ("Textualize/rich", "rich"), ("psf/requests", "requests"), ("encode/httpx", "httpx")]
    weights = [0.5, 0.35, 0.12, 0.03]
    tasks = []
    for i in range(n):
        repo, short = rnd.choices(repos, weights)[0]
        mod = "%s/mod_%d.py" % (short, rnd.randrange(6))
        fn = "func_%d" % rnd.randrange(12)
        old = "def %s(a, b):\n    result_value = a + b + base_offset\n    return result_value\n\n\ndef other_%d():\n    return %d\n" % (fn, i, i)
        new = old.replace("base_offset\n", "base_offset + %d\n" % (i + 1))
        patch = _mk_diff(mod, old, new, ctx="def %s(a, b):" % fn)
        tname = "test_case_%d" % i
        test_old = "import pytest\n\n\ndef test_base():\n    assert True\n"
        test_new = test_old + "\n\n@pytest.mark.parametrize('v', [1, 2])\ndef %s(v):\n    assert %s.%s(v, 1) > 0\n" % (tname, short, fn)
        tpatch = _mk_diff("tests/test_%s.py" % short, test_old, test_new)
        filler = " ".join("w%04d" % rnd.randrange(3000) for _ in range(30))
        text = ("Issue %d in %s: calling `%s` gives a wrong value. Steps: set a and b then call %s from %s.\n```python\nimport %s\n%s.%s(1, 2)\n```\n"
                "It raises ValueError sometimes and the numbers %d look unexpected. %s" % (i, short, fn, fn, mod, short, short, fn, i * 31, filler))
        tasks.append({"instance_id": "%s_%d" % (short, 1000 + i), "repo": repo, "base_commit": "%040x" % rnd.getrandbits(160),
                      "problem_statement": text, "hints_text": "", "patch": patch, "test_patch": tpatch,
                      "created_at": "202%d-%02d-%02dT10:00:00Z" % (3 + rnd.randrange(3), 1 + rnd.randrange(12), 1 + rnd.randrange(28))})
    # planted leakage
    tasks[1]["base_commit"] = tasks[0]["base_commit"]; tasks[1]["repo"] = tasks[0]["repo"]
    tasks[1]["instance_id"] = tasks[0]["instance_id"].rsplit("_", 1)[0] + "_2001"
    sym_old = "def shared_fn(a):\n    return a\n"
    for k, tid in ((2, 3), (3, 4)):
        tasks[k]["repo"] = "psf/requests"
        tasks[k]["instance_id"] = "requests_20%d" % k
        tasks[k]["patch"] = _mk_diff("requests/shared.py", sym_old, sym_old.replace("return a", "return a + %d" % k), ctx="def shared_fn(a):")
    tasks[5]["problem_statement"] = tasks[4]["problem_statement"].replace("wrong", "incorrect")
    tasks[5]["repo"] = tasks[4]["repo"]
    tasks[7]["test_patch"] = tasks[6]["test_patch"]
    tasks[7]["repo"] = tasks[6]["repo"]
    # exact-symbol task with a snapshot archive
    old = _BASE_PY
    new = _BASE_PY.replace("y = x - 1", "y = x - 2")
    tasks[8]["repo"] = "psf/requests"
    tasks[8]["instance_id"] = "requests_2008"
    tasks[8]["patch"] = _mk_diff("pkg/shared.py", old, new)
    snaps = os.path.join(root, "snapshots")
    os.makedirs(snaps, exist_ok=True)
    with tarfile.open(os.path.join(snaps, "requests_2008.tgz"), "w:gz") as tf:
        data = old.encode("utf-8")
        info = tarfile.TarInfo("repo-top/pkg/shared.py")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    with open(os.path.join(root, "tasks.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for t in tasks:
            f.write(json.dumps(t, sort_keys=True) + "\n")
    return tasks


def make_synthetic_results(root, tasks, seed=5):
    rnd = random.Random(seed)
    rows = []
    for arm, lift in (("A0", 0.0), ("A0b", 0.0), ("A1", 0.25)):
        for t in tasks:
            base = 0.15 + 0.5 * (int(sha1(t["instance_id"])[:8], 16) % 3 == 0) * 0.3
            for sd in (0, 1):
                pr = min(0.95, base + lift * base)
                res = rnd.random() < pr
                cap = rnd.random() < 0.3
                has = res or rnd.random() < 0.6
                rows.append({"task_id": t["instance_id"], "arm": arm, "seed": sd, "resolved": res, "non_empty_patch": has, "touches_src": has,
                             "patch_applies": has and rnd.random() < 0.95, "touched_tests": rnd.random() < 0.05, "submitted": not cap,
                             "hit_cap": cap, "duration_s": 600.0 if cap else round(rnd.uniform(60, 500), 1),
                             "tool_calls": rnd.randrange(8, 90), "patch_lines": rnd.randrange(2, 120), "ran_test_after_edit": rnd.random() < 0.6,
                             "loc_file_hit": res or rnd.random() < 0.5,
                             "error": "Agent exceeded session timeout" if cap else "",
                             "resolved_at_180": rnd.random() < pr * 0.5, "resolved_at_300": rnd.random() < pr * 0.8, "resolved_at_600": res,
                             "evidence_time_s": round(rnd.uniform(60, 400), 1) if res else None,
                             "resolved_at_evidence": res if rnd.random() < 0.9 else (not res)})
    with open(os.path.join(root, "results.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return rows


def _digest_dir(path):
    h = hashlib.sha256()
    for root, _d, files in sorted(os.walk(path)):
        for fn in sorted(files):
            h.update(fn.encode())
            with open(os.path.join(root, fn), "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def cmd_selftest(args):
    tmp = args.keep_dir or tempfile.mkdtemp(prefix="devset_selftest_")
    os.makedirs(tmp, exist_ok=True)
    # --- unit checks
    d = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,4 +1,4 @@ def f():\n a = 1\n--- a comment\n+++ new comment\n b = 2\n"
         "\\ No newline at end of file\n"
         "diff --git a/n.py b/n.py\nnew file mode 100644\n--- /dev/null\n+++ b/n.py\n@@ -0,0 +1,2 @@\n+one\n+two\n"
         "diff --git a/gone.py b/gone.py\ndeleted file mode 100644\n--- a/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-bye\n"
         "diff --git a/old.py b/new.py\nsimilarity index 90%\nrename from old.py\nrename to new.py\n")
    fs = parse_diff(d)
    assert [f["path"] for f in fs] == ["x.py", "n.py", "gone.py", "new.py"], [f["path"] for f in fs]
    assert fs[0]["n_added"] == 1 and fs[0]["n_removed"] == 1, (fs[0]["n_added"], fs[0]["n_removed"])
    assert fs[0]["hunks"][0]["removed"][0][1] == "-- a comment" and fs[0]["hunks"][0]["ctx"] == "def f():"
    assert fs[1]["new"] and fs[1]["n_added"] == 2 and fs[2]["deleted"] and fs[2]["n_removed"] == 1 and fs[3]["rename"]
    lo, hi = wilson(5, 10)
    assert abs(lo - 0.2366) < 1e-3 and abs(hi - 0.7634) < 1e-3, (lo, hi)
    assert abs(sign_test_p(6, 0) - 0.03125) < 1e-12 and abs(sign_test_p(6, 2) - 74 / 256.0) < 1e-12
    assert abs(sign_test_p(7, 1, "greater") - 9 / 256.0) < 1e-12 and abs(post_prob_b_better(5, 0) - 0.984375) < 1e-12
    assert enclosing_symbols(_BASE_PY, [8]) == {"Router.remove"} and enclosing_symbols(_BASE_PY, [12]) == {"helper"}
    assert enclosing_symbols(_BASE_PY, [1]) == {"<module>"}
    # --- synthetic dataset
    ds = os.path.join(tmp, "data")
    tasks = make_synthetic(ds)
    tp = os.path.join(ds, "tasks.jsonl")
    out1, out2 = os.path.join(tmp, "o1"), os.path.join(tmp, "o2")
    for out in (out1, out2):
        cmd_profile(argparse.Namespace(tasks=tp, snapshots_dir=os.path.join(ds, "snapshots"), out=os.path.join(out, "profile")))
    prof = json.load(open(os.path.join(out1, "profile", "profile.json")))
    assert prof["n_tasks"] == len(tasks) and prof["symbols_mode"].get("exact", 0) == 1, prof["symbols_mode"]
    feats = {f["instance_id"]: f for f in (task_features(r, os.path.join(ds, "snapshots")) for r in read_jsonl(tp))}
    assert feats["requests_2008"]["symbols_mode"] == "exact" and feats["requests_2008"]["_sym_pairs"] == {("pkg/shared.py", "Router.remove")}
    # --- audit + split
    for out in (out1, out2):
        cmd_audit_split(argparse.Namespace(tasks=tp, snapshots_dir=None, out=os.path.join(out, "split"), splits=None, train_regex="train",
                                           text_soft=0.5, text_hard=0.8, max_component_frac=0.2, make_split=True, sizes="train=24,dev=8,heldout=8", seed=17,
                                           heldout_policy="random", heldout_name="heldout"))
    edges = {(r[0], r[1], r[2]) for r in csv.reader(open(os.path.join(out1, "split", "edges.csv")))}
    types = {e[2] for e in edges}
    for needed in ("same_base_commit", "same_symbol", "text_near_duplicate", "same_test_def"):
        assert needed in types, (needed, sorted(types))
    sp = json.load(open(os.path.join(out1, "split", "splits_new.json")))["splits"]
    assert sum(len(v) for v in sp.values()) == len(tasks) and [len(sp[k]) for k in ("train", "dev", "heldout")] == [24, 8, 8]
    where = {t: s for s, ids in sp.items() for t in ids}
    groups = json.load(open(os.path.join(out1, "split", "groups.json")))
    assert all(len({where[t] for t in g}) == 1 for g in groups), "hard group split across partitions"
    # existing split that separates a planted pair must FAIL the audit
    bad = {"train": [t["instance_id"] for t in tasks[:20]], "dev": [t["instance_id"] for t in tasks[20:]]}
    bad["train"].remove("fastapi_2001") if "fastapi_2001" in bad["train"] else None
    ids_all = [t["instance_id"] for t in tasks]
    a_id, b_id = tasks[0]["instance_id"], tasks[1]["instance_id"]
    bad = {"train": [i for i in ids_all if i != b_id], "dev": [b_id]}
    sp_path = os.path.join(tmp, "bad_split.json")
    json.dump(bad, open(sp_path, "w"))
    cmd_audit_split(argparse.Namespace(tasks=tp, snapshots_dir=None, out=os.path.join(tmp, "audit_bad"), splits=sp_path, train_regex="train",
                                       text_soft=0.5, text_hard=0.8, max_component_frac=0.2, make_split=False, sizes="", seed=0, heldout_policy="random", heldout_name="heldout"))
    assert json.load(open(os.path.join(tmp, "audit_bad", "audit_existing_split.json")))["verdict"] == "FAIL"
    # --- bundle scan
    bdir = os.path.join(tmp, "bundle")
    os.makedirs(bdir)
    leak_lines = [l for l in changed_lines(tasks[10]["patch"]) if significant(l, 20)][:2]
    open(os.path.join(bdir, "prompt.md"), "w").write("Some advice.\n" + "\n".join(leak_lines) + "\nMore advice.\n")
    os.makedirs(os.path.join(tmp, "clean"))
    open(os.path.join(tmp, "clean", "prompt.md"), "w").write("Read the issue. Make a minimal edit. Run the targeted test.\n")
    ns = dict(tasks=tp, ids=None, exclude_ids_file=None, k=2, min_len=20)
    assert cmd_scan_bundle(argparse.Namespace(bundle=bdir, out=os.path.join(tmp, "scan1"), **ns)) == 2
    assert cmd_scan_bundle(argparse.Namespace(bundle=os.path.join(tmp, "clean"), out=os.path.join(tmp, "scan2"), **ns)) == 0
    # --- summarize (micro-check of paired statistics + synthetic pipeline)
    micro = [{"task_id": "t%d" % i, "arm": "X", "resolved": i < 3} for i in range(10)] + \
            [{"task_id": "t%d" % i, "arm": "Y", "resolved": i < 9} for i in range(10)]
    pr = paired(per_task_map({r["task_id"]: [norm_result(r)] for r in micro if r["arm"] == "X"}, lambda r: r["resolved"]),
                per_task_map({r["task_id"]: [norm_result(r)] for r in micro if r["arm"] == "Y"}, lambda r: r["resolved"]), 200, 0)
    assert pr["wins_B"] == 6 and pr["losses_B"] == 0 and pr["ties"] == 4 and abs(pr["p_two_sided"] - 0.03125) < 1e-12
    make_synthetic_results(ds, tasks)
    rp = os.path.join(ds, "results.jsonl")
    feat_csv = os.path.join(out1, "profile", "task_features.csv")
    for out in (out1, out2):
        cmd_summarize(argparse.Namespace(results=[rp], features=feat_csv, out=os.path.join(out, "summary"), boot=300, seed=1,
                                         baseline="A0", aa="A0,A0b", large_patch_lines=200))
        cmd_budget(argparse.Namespace(results=[rp], arm="A0", out=os.path.join(out, "budget"), n_tasks=120, server_start_min=15.0,
                                      setup_min=0.1, setup_min_fixed=True, limit_min=720.0, margin_min=45.0, caps_min="3,5,8,10",
                                      measured_cap_min=10.0, boot=300, seed=2, eps=0.01, evidence_time_col="evidence_time_s",
                                      evidence_resolved_col="resolved_at_evidence"))
        cmd_power(argparse.Namespace(n="20", seeds="1", p0="0.2", icc="0.5", odds_ratio="1,3", alpha=0.05, screen_alpha=0.10, min_wins=3,
                                     sims=60, seed=3, out=os.path.join(out, "power")))
    b = json.load(open(os.path.join(out1, "budget", "budget.json")))["by_cap"]
    assert b["3.0"]["E_T_min"] <= b["5.0"]["E_T_min"] <= b["8.0"]["E_T_min"] <= b["10.0"]["E_T_min"]
    assert abs(b["10.0"]["T_max_min"] - (15 + 120 * 10.1)) < 1e-6
    assert _digest_dir(out1) == _digest_dir(out2), "outputs are not deterministic"
    print("SELFTEST OK  (synthetic fixtures; outputs in %s; no number printed here says anything about Gemma)" % tmp)


# ----------------------------------------------------------------------------
# 12. CLI
# ----------------------------------------------------------------------------


def build_parser():
    ap = argparse.ArgumentParser(prog="devset_tools.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile", help="descriptive profile of tasks.jsonl")
    p.add_argument("--tasks", required=True, help="path to tasks.jsonl (columns: instance_id, repo, base_commit, problem_statement, hints_text, patch, test_patch, created_at)")
    p.add_argument("--snapshots-dir", default=None, help="optional dir with <instance_id>.tgz (base_commit working trees) for EXACT enclosing-symbol analysis")
    p.add_argument("--out", default="devset_out/profile")
    p.set_defaults(fn=cmd_profile)
    p = sub.add_parser("audit-split", help="leakage audit of an existing split and/or build a grouped, repo-stratified split")
    p.add_argument("--tasks", required=True)
    p.add_argument("--snapshots-dir", default=None)
    p.add_argument("--splits", default=None, help="existing split: JSON {name:[ids]} or {id:name}, or CSV instance_id,split")
    p.add_argument("--train-regex", default="train", help="regex identifying train-like split names")
    p.add_argument("--text-soft", type=float, default=0.50, help="TF-IDF cosine for a SOFT 'similar issue' edge")
    p.add_argument("--text-hard", type=float, default=0.80, help="TF-IDF cosine for a HARD near-duplicate edge")
    p.add_argument("--max-component-frac", type=float, default=0.20, help="if a hard group exceeds this fraction of tasks, text edges are demoted to soft")
    p.add_argument("--make-split", action="store_true")
    p.add_argument("--sizes", default="train=84,dev=22,heldout=23")
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--heldout-policy", choices=["random", "newest"], default="random")
    p.add_argument("--heldout-name", default="heldout")
    p.add_argument("--out", default="devset_out/split")
    p.set_defaults(fn=cmd_audit_split)
    p = sub.add_parser("scan-bundle", help="find reference patch/test lines inside a submission bundle (dir or .zip)")
    p.add_argument("--tasks", required=True)
    p.add_argument("--bundle", required=True)
    p.add_argument("--ids", default=None, help="comma-separated task ids to guard (default: all)")
    p.add_argument("--exclude-ids-file", default=None, help="ids that MAY legitimately appear (e.g. the training split)")
    p.add_argument("--k", type=int, default=2, help="consecutive significant changed lines that must match")
    p.add_argument("--min-len", type=int, default=30)
    p.add_argument("--out", default="devset_out/scan")
    p.set_defaults(fn=cmd_scan_bundle)
    p = sub.add_parser("summarize", help="metrics, CIs, paired comparisons, failure classes from run-result rows")
    p.add_argument("--results", nargs="+", required=True, help="JSONL/CSV rows: task_id, arm, resolved (+ optional fields; see RES_ALIASES)")
    p.add_argument("--features", default=None, help="task_features.csv from `profile` (enables repo / issue-type / size strata)")
    p.add_argument("--baseline", default=None)
    p.add_argument("--aa", default=None, help="'armA,armA2': two replicates of the SAME configuration (noise floor)")
    p.add_argument("--boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--large-patch-lines", type=int, default=200)
    p.add_argument("--out", default="devset_out/summary")
    p.set_defaults(fn=cmd_summarize)
    p = sub.add_parser("budget", help="12-hour budget planner from measured per-task durations")
    p.add_argument("--results", nargs="+", required=True)
    p.add_argument("--arm", default=None)
    p.add_argument("--n-tasks", type=int, default=120, help="hidden test size (reported ~120; use 125 for margin)")
    p.add_argument("--server-start-min", type=float, default=15.0, help="PLANNING parameter (third-party estimate); replace with a measurement")
    p.add_argument("--setup-min", type=float, default=0.1, help="per-task sandbox setup minutes; PLANNING parameter unless a setup_s column exists")
    p.add_argument("--setup-min-fixed", action="store_true", help="ignore a setup_s column and use --setup-min")
    p.add_argument("--limit-min", type=float, default=720.0)
    p.add_argument("--margin-min", type=float, default=45.0)
    p.add_argument("--caps-min", default="3,4,5,6,8,10")
    p.add_argument("--measured-cap-min", type=float, default=None, help="cap used in the measurement run (default: max duration)")
    p.add_argument("--eps", type=float, default=0.01, help="max tolerated P(T > limit)")
    p.add_argument("--boot", type=int, default=5000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--evidence-time-col", default=None)
    p.add_argument("--evidence-resolved-col", default=None)
    p.add_argument("--out", default="devset_out/budget")
    p.set_defaults(fn=cmd_budget)
    p = sub.add_parser("budget-arith", help="planning arithmetic for the 12-hour limit (no measurements needed)")
    p.add_argument("--n-tasks", default="120,125")
    p.add_argument("--server-start-min", type=float, default=15.0)
    p.add_argument("--setup-min", type=float, default=0.1)
    p.add_argument("--limit-min", type=float, default=720.0)
    p.add_argument("--margin-min", type=float, default=45.0)
    p.add_argument("--caps-min", default="4,5,5.5,6,8,10,15,30,60")
    p.add_argument("--mean-other-min", default="2,3,4,5")
    p.add_argument("--out", default="devset_out/budget_arith")
    p.set_defaults(fn=cmd_budget_arith)
    p = sub.add_parser("power", help="simulate power / false-promotion rate of paired ablations (assumption-driven)")
    p.add_argument("--n", default="22,45,58,129")
    p.add_argument("--seeds", default="1,3")
    p.add_argument("--p0", default="0.10,0.20")
    p.add_argument("--icc", default="0.3,0.6")
    p.add_argument("--odds-ratio", default="1,2,3,5")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--screen-alpha", type=float, default=0.10)
    p.add_argument("--min-wins", type=int, default=3)
    p.add_argument("--sims", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="devset_out/power")
    p.set_defaults(fn=cmd_power)
    p = sub.add_parser("selftest", help="synthetic smoke test of every subcommand")
    p.add_argument("--keep-dir", default=None, help="write the synthetic fixture and outputs here instead of a temp dir")
    p.set_defaults(fn=cmd_selftest)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    rc = args.fn(args)
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main())
