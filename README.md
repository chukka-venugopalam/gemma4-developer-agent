# Gemma 4 Developer Agent Research & Submission Toolkit

A reproducible workspace for researching, building, and auditing a software-engineering agent for the **Google – The Gemma 4 Developer Agent Competition**. The project keeps the submission source, research evidence, historical candidate archives, and evaluation records separate so results can be traced to the artifact and environment that produced them.

> **Status:** The October 23, 2026 candidate passes local structural validation only. It has not been compiled with the live competition wheelhouse or evaluated with real Gemma in this environment. No score is guaranteed.

## Current candidate

The canonical submission source is `submission/`. Build the competition artifact locally:

```bash
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py
python tools/build_submission.py
```

This creates `dist/submission.zip` with `agent.yaml` at the archive root. The ZIP contains only submission files; research reports and historical experiments are not included.

The current candidate is named **Budget-Fit-Inspired V3**. It uses the required 31B base model, one root agent, bounded reasoning, 28 tool calls, an 8-minute per-task limit, lexical-first localization, optional symbol-grounded graph calls, minimal source edits, targeted verification, and a final patch review. It is inspired by public reference evidence but is not the original author's byte-identical package.

## Validate and test the repository

```bash
python tools/validate_submission.py
python tools/check_repo.py
python -m unittest discover -s tests -v
python tools/build_submission.py --output dist/submission.zip
```

Local validation checks file layout, YAML structure, includes, model/tool names, evaluation fields, prompt-template hazards, allowed submission extensions, and ZIP integrity. **These checks are not the official Kaggle compiler.** Run the preflight notebook described under `notebooks/` in Kaggle with the live competition wheelhouse attached before using a submission opportunity.

## Repository layout

| Path | Purpose |
|---|---|
| `submission/` | Canonical editable source for the next submission. |
| `submissions/archive/` | Prior submission ZIPs retained for comparison. |
| `submissions/source_snapshots/` | Readable snapshots of previous source bundles. |
| `submissions/manifest.csv` | Archive hashes, sizes, aliases, and provenance notes. |
| `research/reports/` | Public research synthesis, forensic reports, and preflight reports. |
| `research/prompts/` | Prompts used for separate research and engineering missions. |
| `research/bundles/` | Original ZIP outputs supplied during research, including diagnostic packs. |
| `research/evidence/screenshots/` | Cropped screenshots documenting scores and Kaggle statuses. |
| `research/raw/` | Raw extracted source captures, retained as evidence rather than endorsed claims. |
| `evaluation/configs/` | Configurations for future controlled experiments. |
| `evaluation/results/` | Submission and experiment ledgers. |
| `notebooks/` | Kaggle preflight and evaluation notebook instructions. |
| `tools/` | Build, validation, hash, and artifact-registration utilities. |
| `docs/` | Competition requirements, design decisions, runbook, and contribution guidance. |
| `tests/` | Local tests for repository tooling. |

## What research has established

- The original VNEXT candidate had broken relative `!include` paths. Its additive repair passed an older third-party harness copy, not the current scorer.
- Several high-scoring public bundles use small, declarative archives and disciplined execution budgets. A public 2026-10-23 study reports a Budget-Fit single-agent reference with 28 calls, an 8-minute task limit, and a 4,096-token reasoning budget. This is useful evidence, not proof that copying its settings guarantees a better score.
- Long identical tool-call streaks and context/budget failures are measurable risks; prompts should change approach after empty/error results rather than repeat the same call.
- One supplied screenshot shows a successful score of 0.03; other screenshots show 0.06 and 0.00, plus notebook timeouts and exceptions. Screenshot records do not identify the exact ZIP hashes, so these scores are not attributed to particular bundles.
- The latest `Notebook Threw Exception` screenshot does not include the traceback. Its cause is still unknown.
- Static ZIP checks passed for multiple candidates, but that did not establish official compilation, real inference, or hidden-task performance.

See [`docs/STATUS_AND_NEXT_STEPS.md`](docs/STATUS_AND_NEXT_STEPS.md), [`docs/HARNESS.md`](docs/HARNESS.md), and [`research/reports/2026-10-23-budget-fit-reference-review.md`](research/reports/2026-10-23-budget-fit-reference-review.md).

## Research integrity

Every result should distinguish among:

- **Static validation:** archive, paths, YAML, and local assertions.
- **Official compilation:** live competition wheelhouse and official compiler.
- **Fake-model replay:** wiring and protocol only, not model quality.
- **Real Gemma run:** actual model inference on named development tasks.
- **Hosted score:** Kaggle evaluation result linked to a submission reference and exact local candidate hash where possible.

Never label a synthetic test, retrieval hit-rate, or non-empty patch rate as Gemma task success. Do not report a score for an artifact unless the submission can be identified. Record blocked checks as blocked instead of inferring a pass.

## Adding new research or submissions

See [`docs/ADDING_ARTIFACTS.md`](docs/ADDING_ARTIFACTS.md). In brief:

1. Add a dated, source-attributed report to `research/reports/`.
2. Preserve the unmodified original under `research/bundles/` when redistribution is permitted.
3. Add the candidate ZIP to `submissions/archive/` and register its SHA-256 in `submissions/manifest.csv`.
4. Record Kaggle status, score, observation date, submission reference, and exact hash if known in `evaluation/results/submission_history.csv`.
5. Update `docs/STATUS_AND_NEXT_STEPS.md` and add an experiment ID to `docs/EXPERIMENT_LOG.md`.
6. Run repository tests, inspect the diff, and commit a self-contained change.

## License and third-party work

This repository contains original prompts and tooling plus references, reports, and bundled materials supplied for project continuity. Public notebook/config artifacts retain their own license and attribution requirements. Review `docs/DATA_POLICY.md` before making the repository public; do not assume every upstream artifact may be redistributed merely because it is visible online.

## Competition references

- [Competition overview and rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Public harness guide](https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md)
- [Budget-Fit / evaluator-change research note (Oct 23, 2026)](https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/)
