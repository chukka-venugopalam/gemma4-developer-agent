#!/usr/bin/env python3
"""Offline validator for a Gemma 4 Developer Agent submission (zip or directory).

It MIRRORS rules that are publicly documented (Kaggle rules page + third-party
reports of the official swegemma/adk-submission validator). It is NOT the official
compiler: a pass here does not prove the official compile passes.

usage:  python validate_submission.py PATH [--baseline OLD.zip] [--time-model]
"""
import io, os, re, stat, sys, zipfile, argparse
import yaml

MODEL = "gemma-4-31b-it-qat-w4a16-ct"
TOOLS = {"run_command", "read_file", "edit_file", "write_file", "get_status",
         "submit_patch", "search_similar_code", "get_code_neighbors", "get_code_subgraph"}
EXTS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
FM_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_BYTES = 3 * 1024 ** 3
GLOBAL_S = 12 * 3600

errors, warns, notes = [], [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)
def note(m): notes.append(m)


def load_files(path):
    """Return {relpath: bytes}; for zips, validate names before reading."""
    files = {}
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            for n in names:
                full = os.path.join(root, n)
                if os.path.islink(full):
                    err(f"symlink not allowed: {full}")
                    continue
                files[os.path.relpath(full, path).replace(os.sep, "/")] = open(full, "rb").read()
    else:
        z = zipfile.ZipFile(path)
        for i in z.infolist():
            if i.is_dir():
                continue
            n = i.filename
            if n.startswith("/") or ".." in n.split("/"):
                err(f"path traversal / absolute path in archive: {n}")
                continue
            if stat.S_ISLNK(i.external_attr >> 16):
                err(f"symlink in archive: {n}")
                continue
            if n in files:
                err(f"duplicate entry: {n}")
            files[n] = z.read(i)
    return files


class Loader(yaml.SafeLoader):
    pass


def make_loader(files, base_dir, depth):
    def include(loader, node):
        rel = loader.construct_scalar(node)
        if ".." in rel.split("/") or rel.startswith("/"):
            raise ValueError(f"!include path traversal: {rel}")
        if depth > 10:
            raise ValueError("!include depth > 10")
        target = os.path.normpath(os.path.join(base_dir, rel)).replace(os.sep, "/")
        if target not in files:
            raise ValueError(f"!include target missing: {target}")
        raw = files[target].decode("utf-8")
        if target.endswith((".yaml", ".yml")):
            sub = type("L", (Loader,), {})
            sub.add_constructor("!include", make_loader(files, os.path.dirname(target), depth + 1))
            return yaml.load(raw, Loader=sub)
        return raw
    return include


def parse_yaml(files, rel):
    L = type("L", (Loader,), {})
    L.add_constructor("!include", make_loader(files, os.path.dirname(rel), 1))
    return yaml.load(files[rel].decode("utf-8"), Loader=L)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return yaml.safe_load(m.group(1)) if m else None


def check(files):
    total = sum(len(b) for b in files.values())
    if total > MAX_BYTES:
        err(f"size {total} > 3 GiB")
    for n in files:
        ext = os.path.splitext(n)[1].lower()
        if ext not in EXTS:
            err(f"disallowed file type: {n}")
        if n.startswith("__MACOSX") or n.endswith(".DS_Store"):
            warn(f"junk file: {n}")
    if "agent.yaml" not in files:
        err("agent.yaml missing at archive root")
        return None, None
    try:
        cfg = parse_yaml(files, "agent.yaml")
    except Exception as e:  # noqa
        err(f"agent.yaml failed to parse/resolve: {e}")
        return None, None

    # exactly one root config; model everywhere
    roots = [n for n in files if n.endswith(("agent.yaml",)) and "/" not in n]
    if len(roots) != 1:
        err(f"expected exactly one root agent.yaml, found {roots}")
    models = set()
    for n in files:
        if n.endswith((".yaml", ".yml")):
            for m in re.findall(r"^\s*model:\s*(\S+)", files[n].decode(), re.M):
                models.add(m)
    if models != {MODEL}:
        err(f"declared models {models} != {{{MODEL}}}")

    # tools
    tools = cfg.get("tools", [])
    for t in tools:
        if isinstance(t, str):
            if t not in TOOLS:
                err(f"unknown tool: {t}")
        elif isinstance(t, dict) and "agent_tool" in t:
            cp = t["agent_tool"].get("config_path", "")
            if ".." in cp.split("/") or cp not in files:
                err(f"agent_tool config_path invalid: {cp}")
        else:
            err(f"unsupported tool entry: {t!r}")
    if len(tools) != len(set(map(str, tools))):
        err("duplicate tools")

    # instruction
    ins = cfg.get("instruction")
    if not isinstance(ins, str):
        err("instruction did not resolve to a string")
        ins = ""
    for ph in re.findall(r"\{+[^{}]*\}+", ins):
        if re.fullmatch(r"\{+\s*[A-Za-z_][A-Za-z0-9_:.]*\??\s*\}+", ph):
            err(f"ADK state placeholder in instruction would raise KeyError: {ph}")
        else:
            warn(f"braces in instruction (ADK leaves non-identifier braces alone): {ph}")

    # skills
    skills = cfg.get("skills", [])
    for sp in skills:
        sp = sp.rstrip("/")
        md = f"{sp}/SKILL.md"
        if md not in files:
            err(f"skill {sp}: SKILL.md missing")
            continue
        fm = frontmatter(files[md].decode())
        if not fm:
            err(f"skill {sp}: no YAML frontmatter")
            continue
        bad = set(fm) - FM_KEYS
        if bad:
            err(f"skill {sp}: unknown frontmatter keys {bad}")
        nm = fm.get("name", "")
        if nm != os.path.basename(sp):
            err(f"skill name {nm!r} != directory {os.path.basename(sp)!r}")
        if not KEBAB.match(nm) or len(nm) > 64:
            err(f"skill name not kebab-case/<=64: {nm!r}")
        d = fm.get("description", "")
        if not d or len(d) > 1024:
            err(f"skill {sp}: description empty or >1024 chars")
        refs = sorted(n for n in files if n.startswith(f"{sp}/references/") and n.endswith(".md"))
        note(f"skill {sp}: {len(refs)} reference files, "
             f"{sum(len(files[n]) for n in refs) + len(files[md])} bytes total")
        # router consistency: every reference must be named in the prompt router and SKILL.md
        for n in refs:
            fam = os.path.basename(n)[:-3]
            if fam not in ins:
                err(f"reference {fam} not named in system prompt router")
            if fam not in files[md].decode():
                err(f"reference {fam} not named in SKILL.md")
    gc = cfg.get("generate_content_config") or {}
    return cfg, gc


def lint_prompt(ins):
    rules = {
        "text-only reply ends run": r"text-only reply ENDS",
        "anytime submit_patch after first edit": r"submit_patch right after your first edit",
        "get_status used for pacing": r"get_status",
        "exact param names (filepath)": r"edit_file\(filepath, old_string, new_string\)",
        "scratch in /tmp not write_file": r"/tmp",
        "protected files": r"conftest\.py",
        "confidence HIGH/MEDIUM/LOW": r"HIGH.*MEDIUM.*LOW",
        "ledger fields": r"TARGET.*EVIDENCE.*ROOT CAUSE.*EXPECTED.*FIX.*TEST",
        "failure classes A-G": r"- A .*- B .*- C .*- D .*- E .*- F .*- G ",
        "repeat-failure stop rule": r"Same failure twice",
        "final gate command": r"git diff --check",
        "graph tools gated": r"get_code_subgraph only at LOW",
    }
    for k, rx in rules.items():
        (note if re.search(rx, ins, re.S) else warn)(f"prompt lint {'ok  ' if re.search(rx, ins, re.S) else 'MISS'}: {k}")


def budget(files):
    try:
        ev = yaml.safe_load(files["eval_config.yaml"].decode())["evaluation"]
    except Exception:
        warn("eval_config.yaml missing/unparsable -> harness defaults apply (unknown, possibly long)")
        return
    m = float(ev.get("max_time_minutes", 0)) * 60
    note(f"eval_config: {ev}")
    for n in (120, 125):
        row = []
        for setup in (15, 30, 60):
            h = n * (m + setup) / 3600
            row.append(f"setup {setup:>2}s -> {h:4.1f} h" + ("" if n * (m + setup) <= GLOBAL_S else " OVER"))
        note(f"12h worst case, N={n}: " + " | ".join(row))
    if ev.get("timeout_seconds", 0) < 300:
        warn("timeout_seconds < 300: a third-party reading of the harness says this also caps the grading test run")


def time_model():
    print("\nTIME MODEL (calculated from assumptions, NOT measured)")
    print("cap 270 s; prefill 1200 tok/s on ~1500 new tokens/turn; tool latency 3 s (read/grep) or 12 s (pytest)")
    print("decode tok/s | out tok/turn | s/turn | turns in 270 s")
    for dec in (15, 25, 40):
        for out in (120, 250, 400):
            for tool in (6,):
                s = 1500 / 1200 + out / dec + tool
                print(f"{dec:>12} | {out:>12} | {s:6.1f} | {270 / s:5.1f}")
    print("A prompt that first submits at call ~25-30 reaches submit_patch in few runs; one that checkpoints at call 5-8 does.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--baseline")
    ap.add_argument("--time-model", action="store_true")
    a = ap.parse_args()
    files = load_files(a.path)
    cfg, gc = check(files)
    if cfg:
        ins = cfg.get("instruction", "")
        note(f"system prompt: {len(ins.encode())} bytes, ~{len(ins) // 4} tokens (chars/4)")
        note(f"generate_content_config: {gc}")
        if (gc.get("thinking_config") or {}).get("include_thoughts") is not False:
            warn("thinking not explicitly disabled")
        lint_prompt(ins)
    budget(files)
    if a.baseline:
        old = load_files(a.baseline)
        note("added: " + ", ".join(sorted(set(files) - set(old))))
        note("changed: " + ", ".join(sorted(n for n in files if n in old and files[n] != old[n])))
        note("removed: " + (", ".join(sorted(set(old) - set(files))) or "none"))
    tot = sum(len(b) for b in files.values())
    note(f"total uncompressed: {tot} bytes in {len(files)} files")
    for t, L in (("NOTE", notes), ("WARN", warns), ("ERROR", errors)):
        for m in L:
            print(f"[{t}] {m}")
    if a.time_model:
        time_model()
    print("\nRESULT:", "FAIL" if errors else "PASS (mirror of documented rules; not the official compiler)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
