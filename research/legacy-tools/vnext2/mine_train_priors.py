#!/usr/bin/env python3
"""Mine recurring repair patterns from the TRAIN split only (counts and shapes, no text).

usage:
  python mine_train_priors.py --tasks tasks.jsonl --train-ids train_ids.txt \
      [--val-ids val_ids.txt] [--heldout-ids heldout_ids.txt] [--id-field task_id] [--out priors_report.md]
  python mine_train_priors.py --selftest

LEAK GUARD
- Only tasks whose id is in --train-ids are parsed beyond their id; all other rows are skipped untouched.
- If --val-ids / --heldout-ids are given and overlap train ids, the run aborts.
- The report holds counts, medians and task ids only: no problem text, no patch text.
Heuristic family tags are a starting point for a human to audit the shipped playbook, not ground truth.
"""
import argparse, json, re, statistics as st, sys, tempfile, os
from collections import Counter, defaultdict

FAMILIES = {
    "dependency-callable": r"\bDepends\b|dependenc|functools\.partial|\bpartial\b|callable|__call__|inspect\.signature|iscoroutinefunction|__wrapped__",
    "types-annotations": r"Annotated|Optional\[|Union\[|type hint|annotation|ForwardRef|get_type_hints|Literal\[|TypeVar|Generic\[",
    "compat-versions": r"pydantic|deprecat|version_info|typing_extensions|ImportError|python ?3\.\d+|PYDANTIC_V",
    "parse-serialize": r"json|serializ|encod|decod|schema|openapi|multipart|form[- ]data|\bparse|header",
    "http-request": r"redirect|cookie|proxy|proxies|\bauth|\burl\b|session|timeout|status_code|request",
    "render-format": r"\bwidth|\bwrap|align|\bstyle|markup|ansi|colou?r|unicode|emoji|render|console|\bpad|truncate|ellipsis",
    "state-cache-lifecycle": r"cache|stale|global|lifespan|startup|shutdown|cleanup|teardown|context ?manager|\bstate\b|singleton",
    "contract-errors-validation": r"\braise\b|exception|\berror\b|status code|validat|\b4\d\d\b|backward|regression|deprecat",
    "async-sync": r"\basync\b|\bawait\b|coroutine|thread|anyio|asyncio|run_in_threadpool",
}
ID_KEYS = ("task_id", "instance_id", "id", "name")


def read_ids(p):
    ids = [l.strip() for l in open(p) if l.strip() and not l.startswith("#")]
    if len(ids) != len(set(ids)):
        sys.exit(f"duplicate ids in {p}")
    return set(ids)


def shape(patch):
    files = re.findall(r"^diff --git a/(\S+) b/", patch, re.M)
    added = [l[1:].strip() for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
    twins = sum(1 for _, c in Counter(a for a in added if len(a) > 20).items() if c >= 2)
    return dict(files=files, hunks=len(re.findall(r"^@@", patch, re.M)), added=len(added), removed=len(removed),
                new_files=len(re.findall(r"^new file mode", patch, re.M)), twins=twins,
                test_like=[f for f in files if re.search(r"(^|/)tests?/|test_", f)],
                text=" ".join(added + removed))


def mine(tasks_path, train, id_field):
    rows, skipped = [], 0
    for line in open(tasks_path):
        if not line.strip():
            continue
        d = json.loads(line)
        tid = next((str(d[k]) for k in ([id_field] if id_field else ID_KEYS) if k in d), None)
        if tid is None:
            sys.exit("no id field found; pass --id-field")
        if tid not in train:
            skipped += 1                      # never look at anything else in this row
            continue
        sh = shape(d.get("implementation_patch") or "")
        blob = (d.get("problem_statement") or "") + " " + sh["text"]
        tags = [f for f, rx in FAMILIES.items() if re.search(rx, blob, re.I)]
        if len(sh["files"]) >= 2:
            tags.append("multi-file-propagation")
        rows.append(dict(id=tid, repo=d.get("repo", "?"), tags=tags, **{k: v for k, v in sh.items() if k != "text"}))
    missing = train - {r["id"] for r in rows}
    return rows, skipped, missing


def report(rows, skipped, missing):
    n = len(rows)
    o = [f"# Train-split prior audit (n={n}; {skipped} non-train rows skipped unread; {len(missing)} train ids not found)\n"]
    o.append("repo mix: " + ", ".join(f"{k} {v}" for k, v in Counter(r["repo"] for r in rows).most_common()))
    if n:
        ch = [r["added"] + r["removed"] for r in rows]
        o.append(f"patch shape: one-file {sum(len(r['files']) == 1 for r in rows)}/{n}; median files "
                 f"{st.median(len(r['files']) for r in rows)}, hunks {st.median(r['hunks'] for r in rows)}, "
                 f"changed lines {st.median(ch)}; new-file patches {sum(r['new_files'] > 0 for r in rows)}; "
                 f"patches repeating a line in 2+ places (twin edits) {sum(r['twins'] > 0 for r in rows)}")
    bad = [r["id"] for r in rows if r["test_like"]]
    if bad:
        o.append(f"WARNING implementation_patch touches test-like files in: {', '.join(bad)}")
    fam = defaultdict(list)
    for r in rows:
        for t in r["tags"]:
            fam[t].append(r)
    o.append("\n| family | tasks | share | median changed lines | repos |\n|---|---|---|---|---|")
    for f in list(FAMILIES) + ["multi-file-propagation"]:
        rs = fam.get(f, [])
        med = st.median(r["added"] + r["removed"] for r in rs) if rs else "-"
        repos = ", ".join(f"{k}:{v}" for k, v in Counter(r["repo"] for r in rs).most_common(3))
        o.append(f"| {f} | {len(rs)} | {len(rs) / n:.0%} | {med} | {repos} |" if n else f"| {f} | 0 | - | - | - |")
    none = [r["id"] for r in rows if not r["tags"]]
    o.append(f"\nuntagged tasks (read these by hand; maybe a missing family): {len(none)} {none[:20]}")
    thin = [f for f in list(FAMILIES) + ["multi-file-propagation"] if len(fam.get(f, [])) < 3]
    o.append(f"families with <3 train tasks (candidates to merge or drop from the playbook): {thin or 'none'}")
    o.append("\nNext: reorder/trim skills/repo-repair-playbook and the FAMILIES block in prompts/system.md by these counts; "
             "keep each reference file under ~500 bytes.")
    return "\n".join(o)


def selftest():
    tmp = tempfile.mkdtemp()
    P = "diff --git a/lib/a.py b/lib/a.py\n--- a/lib/a.py\n+++ b/lib/a.py\n@@ -1 +1,2 @@\n-x = 1\n+y = functools.partial(f)  # callable dependency here\n+y = functools.partial(f)  # callable dependency here\n"
    rows = [dict(task_id="t1", repo="r", problem_statement="Depends with partial fails", implementation_patch=P),
            dict(task_id="t2", repo="r", problem_statement="wrap width wrong in console", implementation_patch=P.replace("a.py", "b.py")),
            dict(task_id="v1", repo="r", problem_statement=None, implementation_patch=12345)]   # poison: must never be parsed
    tp = os.path.join(tmp, "tasks.jsonl")
    open(tp, "w").write("\n".join(json.dumps(r) for r in rows))
    r, skipped, missing = mine(tp, {"t1", "t2"}, None)
    assert skipped == 1 and not missing and len(r) == 2, (skipped, missing, len(r))
    assert "dependency-callable" in r[0]["tags"] and "render-format" in r[1]["tags"] and r[0]["twins"] == 1
    print(report(r, skipped, missing))
    print("\nselftest OK (synthetic rows only; poison val row was skipped unread)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks"); ap.add_argument("--train-ids"); ap.add_argument("--val-ids")
    ap.add_argument("--heldout-ids"); ap.add_argument("--id-field"); ap.add_argument("--out"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.tasks and a.train_ids):
        ap.error("--tasks and --train-ids are required")
    train = read_ids(a.train_ids)
    for name, p in (("val", a.val_ids), ("heldout", a.heldout_ids)):
        if p and (train & read_ids(p)):
            sys.exit(f"ABORT: train ids overlap {name} ids: {sorted(train & read_ids(p))[:5]}")
    rows, skipped, missing = mine(a.tasks, train, a.id_field)
    text = report(rows, skipped, missing)
    print(text)
    if a.out:
        open(a.out, "w").write(text + "\n")


if __name__ == "__main__":
    main()
