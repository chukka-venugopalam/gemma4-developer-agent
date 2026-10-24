# Gemma 4 Developer Agent

A reproducible research and submission workspace for the [Google – The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent). The project investigates prompt design, repository navigation, tool-use reliability, patch verification, runtime budgets, and evaluation reproducibility for an autonomous software-repair agent.

> **Status (24 October 2026):** `submission/` contains the Reference-Calibrated V4 candidate. It has passed local structural validation and deterministic packaging checks. The current competition wheelhouse compile, real Gemma inference, and a new hosted score have **not** been verified. The candidate must not be described as a confirmed Kaggle pass or as scoring above 0.06.

## What this repository contains

- `submission/` — the one canonical source used to build the current candidate archive.
- `tools/` — static validation and deterministic packaging utilities.
- `tests/` — automated tests for the repository's build and validation workflow.
- `research/experiments/` — preserved snapshots of prior source candidates and experiment notes.
- `research/submission_archives/` — dated candidate ZIPs, including preserved historical archives, with `manifest.csv` recording hashes and evidence status.
- `research/forensics/` — the Prompt 7 forensic output, logs, manifests, and preflight notebook from 24 October.
- `research/reports/` — dated research and submission reports.
- `gemmapropmt3/` — development-set and ablation planning utilities.
- `evaluation/` and `notebooks/` — evaluation and notebook documentation.
- `docs/` — competition constraints, engineering decisions, and experiment history.

Research artifacts and historical archives are not automatically included in `submission.zip`.

## Current design

The current candidate uses the required `gemma-4-31b-it-qat-w4a16-ct` model, one root agent, the nine documented tools, a 4,096-token reasoning cap, 8,192 maximum output tokens, and a per-task limit of 8 minutes / 28 tool calls / 100 turns. Its prompt uses lexical-first localization, conditional graph navigation, anti-loop rules, minimal compatible edits, targeted verification, and a final diff review.

These settings are informed by a public Budget-Fit single-agent reference and an independent study of repeated tool calls and evaluation changes. This repository's candidate is an independent implementation; it is **not** claimed to be the exact public reference ZIP or to reproduce its score. The competition's overall 12-hour limit remains a major constraint.

## Build and validate

Use Python 3.10+ and install the development dependency:

```bash
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py
python -m unittest discover -s tests -v
python tools/build_submission.py
```

The build script creates `dist/submission.zip`. Its root contains `agent.yaml`, `eval_config.yaml`, and the included prompt/configuration files directly; there is no extra parent directory. Builds use stable file order and timestamps so identical source yields an identical ZIP.

### Official Kaggle validation

Local checks are only a preflight. To establish compatibility with the actual scorer:

1. Open a new copy of the organizer's current starter notebook.
2. Attach the current competition wheelhouse and competition data.
3. Run the current-wheelhouse preflight in `research/forensics/2026-10-24/prompt7/source_bundle/KAGGLE_CURRENT_WHEELHOUSE_PREFLIGHT.ipynb`.
4. Compare the notebook's install procedure with the current organizer starter before executing it.
5. Check the actual compiler result and tool/agent configuration trace. Run a bounded real Gemma task only after compilation succeeds.
6. Submit manually only after the preflight and smoke test pass. Do not treat fake-model replay as a Gemma score.

The current forensic report explains why prior old-mirror compilation is not sufficient proof of current scorer compatibility.

## Evidence and experiment policy

- Every score must be linked to a dated Kaggle result and a candidate hash when available.
- Separate structural validation, old-mirror compile, current-wheel compile, fake-model replay, real inference, and hosted score.
- Do not label synthetic tests, localization heuristics, or fake-model replay as real patch success.
- Keep historical candidates immutable. Add each new candidate under a dated folder in `research/experiments/` and register it in `docs/EXPERIMENT_LOG.md`.
- Do not claim an improvement from one noisy hosted score without paired evidence; the public score may vary across runs and evaluator versions.
- Never store Kaggle tokens, private credentials, or secrets in source control.

## Competition constraints

See [`docs/COMPETITION.md`](docs/COMPETITION.md), [`docs/HARNESS.md`](docs/HARNESS.md), and the official [competition page](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview). Treat the official page and currently mounted wheelhouse as authoritative if older research notes disagree.

## License and attribution

This repository contains independently written agent prompts and tooling plus dated research records. Public reference work is linked in research notes; a reference score or configuration is not represented as our result. Confirm upstream license terms before redistributing third-party artifacts or source excerpts.
