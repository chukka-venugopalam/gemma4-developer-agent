#!/usr/bin/env python3
"""fetch_submission_metadata.py - credential-safe export of YOUR submission rows for one Kaggle competition.

    python fetch_submission_metadata.py [--competition gemma-4-developer-agent] [--out-dir .]
                                        [--manifest candidate_manifest.csv] [--previous OLD.json]
                                        [--page-size 100] [--redact-identity]

WHAT IT DOES
  * Calls the installed Kaggle API (kaggle >= 2.x, or 1.x as a best effort) READ-ONLY: competition_submissions().
  * Writes submission_metadata.json, submission_metadata.csv and SUBMISSION_METADATA_SUMMARY.md in --out-dir.
  * Records the object keys that Kaggle actually returned (observed_keys), so nothing is assumed.
  * Associates each row's uploaded byte count (totalBytes) with candidate_manifest.csv sizes.
    That association is SIZE-ONLY (INFERRED).  It becomes a cryptographic claim only if Kaggle returns a hash
    field; the script checks the observed keys for one and says so.
  * --previous OLD.json: diff against an earlier export and flag rows whose status/score/error changed (RESCORED).

WHAT IT NEVER DOES
  * It never submits, uploads, or spends a submission slot.
  * It never opens or prints kaggle.json / access_token files or KAGGLE_* environment values; authentication is
    delegated entirely to the Kaggle library.  Keys that look secret are dropped; env values and Bearer strings are
    scrubbed from any error text.

EXIT CODES  0 ok | 3 BLOCKED (no credentials / no network / Kaggle package missing) | 4 API error | 5 zero rows
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

SECRET_KEY_RE = re.compile(r"token|secret|password|passwd|cookie|authorization|api[_-]?key|credential", re.I)
HASH_KEY_RE = re.compile(r"hash|sha|md5|checksum|digest", re.I)
IDENTITY_KEYS = {"team_name", "submitted_by", "submitted_by_ref", "teamName", "submittedBy", "submittedByRef"}
BEARER_RE = re.compile(r"(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
CANON = [  # canonical column, accepted source keys (camelCase from kaggle 2.x to_dict, snake_case from 1.x/attrs)
    ("ref", ("ref", "id")),
    ("date_utc", ("date", "dateTime", "date_time")),
    ("status", ("status",)),
    ("public_score", ("publicScore", "public_score")),
    ("private_score", ("privateScore", "private_score")),
    ("total_bytes", ("totalBytes", "total_bytes", "size")),
    ("file_name", ("fileName", "file_name")),
    ("error_description", ("errorDescription", "error_description")),
    ("description", ("description", "message")),
    ("team_name", ("teamName", "team_name")),
    ("submitted_by", ("submittedBy", "submitted_by")),
    ("url", ("url",)),
]


# Phrases seen in errorDescription by OTHER competitors in this competition (third-party notes, not Kaggle documentation).
ERROR_HINTS = [
    (re.compile(r"system error", re.I), "HINT: Kaggle-side system error text; third-party rows with it were later rescored. Not proof of a package fault."),
    (re.compile(r"unhandled error while rerunning", re.I), "HINT: exception during the scoring rerun (cause not stated by Kaggle)."),
    (re.compile(r"more CPU, GPU or TPU resources|exceeded allowed compute", re.I), "HINT: resource/compute-limit text (third-party reading: may or may not be the 12 h cap)."),
    (re.compile(r"timeout|timed out", re.I), "HINT: timeout wording."),
]


def error_hint(text) -> str:
    t = str(text or "")
    if not t.strip():
        return "no errorDescription text returned: cause UNKNOWN"
    for rx, h in ERROR_HINTS:
        if rx.search(t):
            return h
    return "unrecognised text: read it verbatim; cause UNKNOWN"


def scrub(text: str) -> str:
    """Remove env-var values (any KAGGLE_*) and Bearer/Basic strings from text before printing."""
    text = str(text)
    for k, v in os.environ.items():
        if k.upper().startswith("KAGGLE") and v and len(v) >= 4:
            text = text.replace(v, "<redacted-env>")
    return BEARER_RE.sub(r"\1 <redacted>", text)


def blocked(reason: str, detail: str = "") -> int:
    print("STATUS: BLOCKED - live retrieval did not happen. No token was read or printed.")
    print(f"REASON: {reason}")
    if detail:
        print(f"DETAIL: {scrub(detail)[:600]}")
    print("READY-TO-RUN (authenticated machine, e.g. your Windows PowerShell):")
    print("  pip install --upgrade kaggle")
    print("  # Kaggle > Settings > API > create token; Kaggle's own docs say where it is stored. Do not paste it anywhere.")
    print("  python fetch_submission_metadata.py --out-dir .\\meta_run1")
    return 3


def to_plain(obj) -> dict:
    """ApiSubmission (kaggle 2.x) -> dict. Falls back to public attributes for 1.x style objects."""
    if hasattr(obj, "to_dict"):
        try:
            d = obj.to_dict()
            if isinstance(d, dict):
                return d
        except Exception:  # noqa: BLE001
            pass
    d = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            v = getattr(obj, name)
        except Exception:  # noqa: BLE001
            continue
        if not callable(v):
            d[name] = v
    return d


def norm_date(v):
    """-> (iso_utc_string_or_None, note)"""
    if v in (None, ""):
        return None, ""
    if isinstance(v, dt.datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "naive datetime assumed UTC"
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ""
    s = str(v)
    try:
        p = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if p.tzinfo is None:
            return p.replace(tzinfo=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "naive string assumed UTC"
        return p.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ""
    except ValueError:
        return s, "unparsed date string kept verbatim"


def jsonable(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    return str(v)  # enums etc.


def clean_status(v) -> str:
    s = str(v)
    return s.split(".")[-1].upper() if s else ""


def build_row(raw: dict, redact_identity: bool) -> dict:
    safe = {k: jsonable(v) for k, v in raw.items() if not SECRET_KEY_RE.search(str(k))}
    if redact_identity:
        safe = {k: ("<redacted>" if k in IDENTITY_KEYS else v) for k, v in safe.items()}
    row = {}
    for col, srcs in CANON:
        val = next((safe[s] for s in srcs if s in safe), None)
        row[col] = val
    iso, note = norm_date(raw.get("date", raw.get("dateTime")))
    row["date_utc"], row["date_note"] = iso, note
    row["status"] = clean_status(row["status"]) if row["status"] is not None else None
    if row["total_bytes"] not in (None, ""):
        try:
            row["total_bytes"] = int(row["total_bytes"])
        except (TypeError, ValueError):
            pass
    row["error_class_hint"] = error_hint(row.get("error_description")) if row.get("status") in ("ERROR", "FAILED") or row.get("error_description") else ""
    row["raw_fields"] = safe
    return row


def load_manifest(path: str):
    out = []
    if path and os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    out.append({"label": r["label"], "bytes": int(r["bytes"]), "sha256": r["sha256"]})
                except (KeyError, ValueError):
                    continue
    return out


def associate(row: dict, cands: list, hash_keys: list) -> dict:
    nb = row.get("total_bytes")
    hits = [c for c in cands if isinstance(nb, int) and c["bytes"] == nb]
    if hash_keys:
        basis = f"Kaggle returned hash-like key(s) {hash_keys}: compare them to candidate SHA-256 values by hand; size match alone is not proof"
    else:
        basis = "SIZE-ONLY (INFERRED): Kaggle returned no hash field, so byte equality cannot prove identical content"
    if not cands:
        verdict = "NO MANIFEST LOADED"
    elif len(hits) == 1:
        verdict = f"size matches {hits[0]['label']}"
    elif len(hits) > 1:
        verdict = "AMBIGUOUS: " + ", ".join(h["label"] for h in hits)
    else:
        verdict = "UNKNOWN: no local candidate has this byte count"
    return {"candidate_by_size": verdict, "association_basis": basis,
            "candidate_sha256": [h["sha256"] for h in hits]}


def diff_previous(rows: list, prev_path: str) -> list:
    with open(prev_path, encoding="utf-8") as f:
        prev = {str(r.get("ref")): r for r in json.load(f).get("rows", [])}
    notes = []
    for r in rows:
        p = prev.get(str(r.get("ref")))
        if p is None:
            r["refresh_note"] = "NEW since previous export"
            continue
        ch = [f"{k}: {p.get(k)!r} -> {r.get(k)!r}" for k in ("status", "public_score", "error_description", "total_bytes")
              if (p.get(k) if p.get(k) is not None else "") != (r.get(k) if r.get(k) is not None else "")]
        if ch:
            tag = "RESCORED/CHANGED"
            r["refresh_note"] = tag + " (" + "; ".join(ch) + ")"
            notes.append(f"ref {r.get('ref')}: {r['refresh_note']}")
        else:
            r["refresh_note"] = "unchanged"
    return notes


def write_outputs(out_dir, meta, rows, notes):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "submission_metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "rows": rows}, f, indent=2, ensure_ascii=False)
    cols = [c for c, _ in CANON] + ["date_note", "error_class_hint", "candidate_by_size", "association_basis", "refresh_note"]
    with open(os.path.join(out_dir, "submission_metadata.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    md = [f"# Submission metadata - {meta['competition']}", "",
          f"Retrieved (UTC): {meta['retrieved_utc']} | kaggle {meta['kaggle_version']} | python {meta['python']}",
          f"Rows: {len(rows)} | observed keys: `{', '.join(meta['observed_keys'])}`",
          f"Hash-like key exposed by Kaggle: {meta['hash_like_keys'] or 'NONE'}", "",
          "| ref | date (UTC) | status | public | bytes | file | error text | non-authoritative hint | size-association |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        err = str(r.get("error_description") or "").replace("|", "/").replace("\n", " ")[:160]
        md.append(f"| {r.get('ref')} | {r.get('date_utc')} | {r.get('status')} | {r.get('public_score')} | "
                  f"{r.get('total_bytes')} | {r.get('file_name')} | {err} | {str(r.get('error_class_hint') or '').replace('|', '/')} | {r.get('candidate_by_size')} |")
    md += ["", "Size association is SIZE-ONLY unless a hash key is listed above. A status of ERROR with an empty",
           "error_description does not identify a cause; do not infer one without Kaggle's own text or logs."]
    if notes:
        md += ["", "## Changes since previous export", *[f"- {n}" for n in notes]]
    with open(os.path.join(out_dir, "SUBMISSION_METADATA_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--competition", default="gemma-4-developer-agent")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--manifest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidate_manifest.csv"))
    ap.add_argument("--previous", default="")
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--redact-identity", action="store_true")
    a = ap.parse_args()

    try:
        import importlib.metadata as md
        kver = md.version("kaggle")
    except Exception:  # noqa: BLE001
        kver = "NOT INSTALLED"
    print(f"python {sys.version.split()[0]} | kaggle {kver}")
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except BaseException as e:  # noqa: BLE001 - kaggle may sys.exit() on import without credentials
        return blocked("kaggle package unavailable or exited at import", f"{type(e).__name__}: {e}")
    try:
        api = KaggleApi()
        api.authenticate()
    except BaseException as e:  # noqa: BLE001
        return blocked("authentication failed or no credentials found", f"{type(e).__name__}: {e}")

    try:
        subs = api.competition_submissions(a.competition, page_size=a.page_size)
    except TypeError:
        subs = api.competition_submissions(a.competition)  # kaggle 1.x signature
    except BaseException as e:  # noqa: BLE001
        msg = scrub(f"{type(e).__name__}: {e}")
        if re.search(r"401|403|unauthor|forbidden|credential|auth", msg, re.I):
            return blocked("Kaggle rejected the request (auth/permission/rules not accepted?)", msg)
        if re.search(r"connect|resolve|timed? ?out|proxy|network|ssl|tunnel", msg, re.I):
            return blocked("network unreachable", msg)
        print("STATUS: API ERROR\nDETAIL:", msg[:600])
        return 4
    subs = [s for s in (subs or []) if s is not None]
    if not subs:
        print("STATUS: zero rows returned (no submissions, or wrong competition slug).")
        return 5
    if len(subs) >= a.page_size:
        print(f"WARNING: got {len(subs)} rows = page size; older rows may exist. Re-run with a larger --page-size.")

    raws = [to_plain(s) for s in subs]
    observed = sorted({k for r in raws for k in r if not SECRET_KEY_RE.search(str(k))})
    hash_keys = [k for k in observed if HASH_KEY_RE.search(k)]
    cands = load_manifest(a.manifest)
    rows = []
    for r in raws:
        row = build_row(r, a.redact_identity)
        row.update(associate(row, cands, hash_keys))
        rows.append(row)
    notes = diff_previous(rows, a.previous) if a.previous else []
    meta = {"competition": a.competition, "retrieved_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "python": sys.version.split()[0], "kaggle_version": kver, "observed_keys": observed,
            "hash_like_keys": hash_keys, "manifest_loaded": bool(cands), "redact_identity": a.redact_identity,
            "note": "No credentials are stored in this file."}
    write_outputs(a.out_dir, meta, rows, notes)
    print(f"STATUS: OK - {len(rows)} rows written to {os.path.abspath(a.out_dir)}")
    print("observed keys:", ", ".join(observed))
    for r in rows:
        print(r.get("ref"), (r.get("date_utc") or ""), r.get("status"), r.get("public_score"), r.get("total_bytes"),
              r.get("file_name"), "|", r.get("error_description"), "|", r.get("candidate_by_size"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
