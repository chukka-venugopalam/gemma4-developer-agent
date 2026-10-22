# Gemma 4 Developer Agent Research and Evaluation

An evidence-tracked repository for developing and evaluating a software-repair agent for the [Google – The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent).

The repository contains the editable agent configuration, reproducible packaging tools, public-agent research, evaluation plans, submission archives, preflight notebooks, and records of observed Kaggle outcomes. It is designed so that each candidate can be rebuilt, hashed, and compared without overwriting earlier artifacts.

> **Current evaluation status (22 October 2026):** the latest supplied Kaggle screenshot shows **Notebook Threw Exception**. The visible detail pane reports an unhandled notebook error but does not show a Python traceback, public score, submission reference, or archive hash. The exact cause and candidate-to-row linkage are therefore unresolved. Previous screenshots show scores of 0.00, 0.03, and 0.06, but most cannot be reliably attributed to the archived ZIPs.

## Current source and reproducibility

- `submission/` is the canonical editable agent source.
- `python tools/validate_submission.py submission` performs local static checks only.
- `python tools/build_submission.py` builds `dist/submission.zip` from that source.
- `python tools/validate_submission.py dist/submission.zip` checks the built archive.
- `python -m unittest discover -s tests -v` runs repository-level tests.
- `python tools/check_repo.py` verifies repository housekeeping, archived ZIP hashes and basic secret-pattern checks.

These local checks **do not replace the official competition compiler or a real Gemma run**. The current candidate has not been proven to compile or execute under the exact live Kaggle wheelhouse based on the artifacts available in this repository.

## Quick start

Python 3.10 or later is recommended for repository tooling. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py submission
python tools/build_submission.py
python tools/validate_submission.py dist/submission.zip
python -m unittest discover -s tests -v
python tools/check_repo.py
```

`requirements-dev.txt` installs only local development dependencies. It does not install or emulate the competition runtime.

## Repository map

| Path | Purpose |
|---|---|
| `submission/` | Canonical source for the current agent candidate. |
| `submissions/archive/` | Immutable ZIPs of recovered submission candidates. |
| `submissions/manifest.csv` | SHA-256, size, source aliases, and attribution notes for each unique candidate ZIP. |
| `research/reports/` | Research reports, forensic findings, and validation reports. |
| `research/prompts/` | Research and engineering prompts used to produce the archived reports. |
| `research/ablation/` | Development-set design, planned ablations, and supporting utilities. |
| `research/bundles/` | Original research-output bundles preserved for provenance. |
| `research/raw/` | Raw discovery output retained as source evidence; review before redistribution. |
| `research/evidence/screenshots/` | Submission status evidence, with score/archive linkage noted where unknown. |
| `notebooks/preflight-s0/` | Kaggle preflight notebook, run order, and execution instructions. |
| `evaluation/logs/` | Captured outputs from the preflight attempt. |
| `evaluation/results/` | Score observations and experiment registry. |
| `tools/` | Build, static validation, registration, and repository checks. |
| `docs/` | Project status, competition contract, research conclusions, data policy, and runbooks. |

## What the research currently supports

1. **Packaging correctness is necessary, not sufficient.** An earlier VNEXT candidate had broken relative `!include` targets in the tested older harness. Its additive repair passed that older compiler and a fake-model replay; this does not prove current Kaggle compatibility or explain the historical Kaggle errors.
2. **Budget and failure-path control deserve priority.** Public-agent research suggests using bounded execution, short outputs, explicit no-repeat rules, targeted verification, and a minimal final diff. Public leaderboard comparisons are noisy and not controlled component ablations.
3. **Retrieval complexity is not yet justified by measured success.** Symbol-grounded graph tools remain available in the current candidate, but the prompt restricts them to questions they can answer. There is no paired Gemma experiment here that establishes a score gain from graph search or a second agent.
4. **Local static tests are not model results.** Synthetic self-tests and YAML/archive checks must never be described as patch-resolution performance.

Detailed evidence and limitations are in [Research Findings](docs/RESEARCH_FINDINGS.md), [Submission History](docs/SUBMISSION_HISTORY.md), and [Project Status](docs/PROJECT_STATUS.md).

## Current open engineering work

1. Retrieve the actual traceback for the most recent **Notebook Threw Exception** event and record the full error context without credentials.
2. Use a fresh copy of the official Kaggle starter notebook and the actual current competition wheelhouse to compile the exact candidate archive.
3. Verify the live evaluation limits, tool registry, generation settings, and `submit_patch` behavior.
4. If preflight succeeds, run a bounded real Gemma smoke test on public development tasks and save the actual tool trace, patch, runtime, and verifier result.
5. Run paired, repeatable ablations before attributing a score improvement to any prompt or configuration change.
6. Register each new candidate and outcome with hashes; do not tie a public score to a ZIP merely because their dates or filenames look similar.

See [Next Steps](docs/NEXT_STEPS.md) and [Research Progress](docs/RESEARCH_PROGRESS.md).

## Adding research and recording results

Read [Adding Artifacts](docs/ADDING_ARTIFACTS.md) for commands and file conventions. In summary:

- Preserve the original report or bundle.
- Record the date, provenance, evidence level, and SHA-256.
- Add candidate ZIPs to `submissions/archive/` through `tools/register_artifact.py`.
- Append a new row to `evaluation/results/score_observations.csv` for every observed Kaggle outcome. Leave the candidate hash blank when exact archive linkage cannot be established.
- Keep original candidate ZIPs immutable; work from `submission/` for new versions.

## Evidence and data policy

This is a research record, not an official leaderboard claim. Statuses are treated as observations, not causal evidence. Claims are labeled confirmed, inferred, unknown, blocked, or not tested where appropriate. No hidden tasks, hidden patches, API tokens, browser cookies, or credentials should be committed. Review screenshots and raw logs before redistributing the repository; see [Data Policy](docs/DATA_POLICY.md).

## Contributing

Issues and pull requests are welcome for reproducibility fixes, documented harness changes, improved experiment tracking, and evaluation tooling. Every change to the agent should have a candidate ID, a rationale, an evaluation plan, and an outcome record. See [CONTRIBUTING.md](CONTRIBUTING.md).
