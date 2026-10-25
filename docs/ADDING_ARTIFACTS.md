# Adding research and submission artifacts

## Register a submission candidate

Run from the repository root:

```bash
python tools/register_artifact.py candidate /path/to/submission.zip --candidate-id budget-fit-v6 --notes "Describe exactly what changed"
```

Set `--compile-status`, `--inference-status`, and `--score` only when those results were actually observed. The tool copies the ZIP into `research/submission_archives/`, computes SHA-256, and appends a row to `manifest.csv`. It refuses to overwrite an existing candidate file or register an identical ZIP hash twice.

## Register a research report

```bash
python tools/register_artifact.py report /path/to/report.md --title "public agent comparison" --date 2026-10-25
```

The report is copied into `research/reports/` with a date-prefixed filename. Preserve source URLs, the retrieval date, evidence tier, uncertainties, and the distinction between source facts and inference. Add a short entry to `docs/EXPERIMENT_LOG.md` when a report changes a design decision.

## Record a Kaggle result

Append a row to `evaluation/results/score_observations.csv` and preserve the corresponding screenshot or metadata export. Only fill in a candidate hash when the exact uploaded archive can be linked to the result. Leave it blank otherwise. A `Kaggle Error` or `Notebook Threw Exception` without the actual logs is an unresolved event, not a root-cause diagnosis.

## Validate before committing

```bash
python tools/validate_submission.py submission
python -m unittest discover -s tests -v
python tools/build_submission.py
python tools/check_repo.py
```

These checks are local repository/package checks only. Current official wheelhouse compilation, real Gemma inference, and a hosted score must be reported separately.
