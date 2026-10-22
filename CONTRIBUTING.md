# Contributing to this research repository

## Adding reports

- Preserve the original report. If edits are necessary, store a separate reviewed copy rather than overwriting raw evidence.
- Prefer filenames like `YYYY-MM-DD__short-description.md`.
- Include scope, environment, commands, outputs, pass/fail/blocked status, evidence links, hash of tested candidate, limitations and next decision.
- Add the report to `research/artifact_manifest.csv` and link it from `docs/RESEARCH_FINDINGS.md`.

## Adding candidate ZIPs

- Never overwrite an existing archive.
- Record SHA-256, file size, agent design, config summary, validation level, run reference, score, and whether score linkage is proven.
- Do not write a score into the manifest merely because a nearby filename or screenshot date looks plausible.
- Run the current-harness compiler before describing an archive as ready.

## Experiments

- Keep a fixed task set and record seed/settings when the harness supports them.
- Save per-task success and process metrics. Separate real validation outcomes from localization heuristics.
- Change one major factor per experiment.
- Write null or blocked outcomes explicitly; no result is better than fabricated evidence.

Before opening a pull request, run `python tools/update_build_manifest.py`, `python tools/check_repo.py`, and `python -m unittest discover -s tests -v`. These checks validate repository integrity only; they do not replace the official Kaggle compiler.
