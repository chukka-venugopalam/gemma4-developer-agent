# Gemma 4 Developer Agent

A reproducible research and submission workspace for the [Google – The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent). The project studies tool-use reliability, repository localization, patch quality, bounded verification, and the reproducibility of agent evaluations.

> **Status (26 October 2026):** `submission/` now contains the Evidence Repair V6 candidate. It passes local static validation and deterministic packaging checks. Current official-wheelhouse compilation, a current-harness fake-model replay, real Gemma inference, and a hosted score have **not** been established for V6. The latest user-supplied submissions screenshot shows 0.13 and two earlier 0.18 rows; those rows are not bound to known archive hashes. A separate leaderboard screenshot showed four entries at 0.24.

## What this repository contains

- `submission/` — canonical editable source for the current candidate.
- `tools/` and `tests/` — local static validation, deterministic packaging, artifact registration, integrity checks, and unit tests.
- `research/experiments/` — immutable source snapshots, submission ZIPs, and experiment notes for each candidate.
- `research/submission_archives/` — historical ZIPs and a manifest with hashes, provenance, and validation status.
- `research/forensics/` — submission forensics, current-harness preflight notebooks, reports, and logs.
- `research/reports/` — public-agent research and dated candidate reports.
- `gemmapropmt3/` — development-set and ablation planning utilities.
- `evaluation/` and `notebooks/` — score observations, experiment result schema, and notebook documentation.
- `docs/` — competition constraints, engineering decisions, experiment history, and update instructions.

Research artifacts are deliberately kept outside `submission/` and are not included in the competition ZIP.

## Current candidate: Evidence Repair V6

V6 uses the required `gemma-4-31b-it-qat-w4a16-ct` model, one root agent, and all nine documented tools. The three code-intelligence tools are declared to avoid registry mismatch, but the prompt keeps their use conditional and symbol-grounded. The prompt emphasizes concise contract extraction, exact lexical localization, small `edit_file` replacements, anti-repetition recovery, a single focused verification cycle, and final diff review.

Sampling: temperature 0.2, top-p 0.95, top-k 40, 8,192 maximum output tokens, thinking enabled with a 4,096-token budget. Per-task caps: eight minutes, 28 tool calls, 80 turns, and a 240-second command/verification timeout. This candidate is informed by public reference research and observed user scores; it is not a reconstruction of an inaccessible 0.24 leader, and no score improvement is claimed before a hosted evaluation.

## Build and validate

Use Python 3.10+ and install the development dependency:

```bash
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py
python -m unittest discover -s tests -v
python tools/build_submission.py
python tools/check_repo.py
```

The build script creates `dist/submission.zip`, with `agent.yaml` at the archive root. Stable ordering and timestamps make builds reproducible from identical source.

### Official Kaggle validation

Local checks are only a preflight. To establish compatibility with the actual scorer:

1. Open a new copy of the organizer's current starter notebook.
2. Attach the current competition wheelhouse and competition data.
3. Run the latest `KAGGLE_CURRENT_WHEELHOUSE_PREFLIGHT_V4.ipynb` from the preserved Mission 10 preflight package, using the current starter installation cell.
4. Check current compiler output, tool wiring, reasoning configuration, and timeout semantics.
5. Run a bounded real Gemma smoke test only after compilation and fake-model replay pass.
6. Preserve the exact ZIP SHA-256, runtime version, logs, and score together. Submit manually only after reviewing the gate.

Older-mirror compilation and synthetic tests are not proof of current scorer compatibility.

## Evidence and experiment policy

- Every score must link to a dated Kaggle observation and candidate hash when available.
- Separate static validation, old-mirror compile, current-wheel compile, fake-model replay, real inference, and hosted score.
- Never label synthetic checks, localization heuristics, or fake-model replay as real patch success.
- Preserve each candidate immutably under a dated directory in `research/experiments/` and register its hash in `research/submission_archives/manifest.csv`.
- Do not claim causality from one noisy leaderboard result. The public board can vary across runs and evaluator versions.
- Do not store Kaggle tokens, private credentials, or secrets in source control.

## Selected public references

- [Competition overview and model/runtime rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Harness reference](https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md)
- [Measuring an agent while its evaluator moved (updated 24 October 2026)](https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/)
- [Edit mechanics and anti-repeat prompt example](https://github.com/8kta/kaggle-gemma4/blob/main/submission/prompts/system.md)

## License and attribution

Prompts and tooling in this repository are independently written. Public findings are linked and their limitations recorded. Public scores and reference configurations are not represented as our own results. Confirm upstream license terms before redistributing third-party source or artifacts.
