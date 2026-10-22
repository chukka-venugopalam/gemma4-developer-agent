# Next Steps

Work in this order. Do not spend another scored Kaggle submission until the current preflight gate passes.

## P0 — Diagnose the latest notebook exception

- [ ] Open the failed notebook run, not just the submission summary panel.
- [ ] Copy the full Python traceback and the failing cell/output. Redact tokens and secrets.
- [ ] Identify whether the exception occurs during wheelhouse setup, model startup, harness compilation, evaluation, or submission artifact creation.
- [ ] Record the exception in `evaluation/logs/` and update `evaluation/results/score_observations.csv` without guessing the candidate hash.

## P1 — Official current-harness preflight

- [ ] Run a fresh copy of the official starter notebook with the actual competition wheelhouse.
- [ ] Record Python, package, and wheel versions.
- [ ] Validate the model declaration, archive layout, all includes, allowed file extensions, tool declarations, and `eval_config.yaml`.
- [ ] Run the current official validator/compiler, discovering the real function signatures rather than assuming them.
- [ ] Confirm effective task budgets, thinking settings, and tool-call semantics in the current installed resolver.
- [ ] Test whether the agent calls undeclared graph tools if the task prompt mentions additional capabilities.
- [ ] Preserve the full command output under `evaluation/logs/`.

## P2 — Bounded real Gemma smoke test

- [ ] Only after P1 passes, run one public development task and then, if stable, one additional task.
- [ ] Record the final patch, verifier outcome, tool trace, elapsed time, token counts, and exceptions.
- [ ] Check for scratch files, test edits, or unrelated modifications in the submitted patch.

## P3 — Measure before changing architecture

- [ ] Build a reproducible, bounded development-task evaluation with resume support.
- [ ] Track valid tool calls, repeated calls, empty search results, non-empty patches, patch pollution, test verification, timeouts, and verified resolution.
- [ ] Compare candidate changes on paired tasks and seeds.
- [ ] Do not infer Gemma performance from synthetic tests, retrieval hit rate, or local static validation.

## P4 — Promote and record a candidate

- [ ] Build from `submission/`, run local validation and tests, and calculate SHA-256.
- [ ] Register the immutable ZIP in `submissions/archive/` and update the manifest.
- [ ] Have the owner submit the exact candidate manually after the safety gate passes.
- [ ] Record Kaggle submission ID, timestamp, status, score, error details, and candidate hash only when verified.
