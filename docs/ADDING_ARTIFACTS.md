# Adding Research, Submission ZIPs, and Evaluation Results

This workflow is designed to avoid losing prior artifacts and to keep new additions easy to find.

## Add a research report

```powershell
python tools/register_artifact.py --kind research --source C:\path\to\report.md --date 2026-10-23 --label "prompt-8-smoke-test" --status received --notes "Claude output; official compiler status is recorded in report"
```

The tool copies the file into `research/reports/`, calculates SHA-256, and adds a row to `research/artifact_manifest.csv`. If the exact bytes are already registered, it will not create a duplicate. Preserve the original prompt separately in `research/prompts/` when applicable.

## Add a prompt

```powershell
python tools/register_artifact.py --kind prompt --source C:\path\to\prompt.txt --date 2026-10-23 --label "prompt-8-current-harness-smoke" --notes "Next bounded official preflight"
```

## Add a candidate submission ZIP

```powershell
python tools/register_artifact.py --kind submission --source C:\path\to\submission.zip --date 2026-10-23 --label "budget-aware-v3" --status built-not-submitted --notes "Static checks only; official compile not run"
```

The tool rejects non-ZIPs, corrupt archives, and ZIPs without a root-level `agent.yaml`. It records hash, bytes, member count, source alias, and notes in `submissions/manifest.csv`. It does not submit to Kaggle or claim official compatibility.

## Record a Kaggle outcome

After the submission finishes, append a new row to `evaluation/results/score_observations.csv`. Capture the Kaggle submission reference, exact artifact SHA-256, date/time, status, score, and error description if available. Leave `candidate_sha256` blank when exact linkage cannot be established. Use a new row; do not overwrite a previous run.

For results from a controlled experiment, also fill `evaluation/templates/experiment_record.csv` or append to `evaluation/results/experiment_registry.csv`, keeping candidate and harness versions fixed.

## Before a public push

1. Run `python tools/check_repo.py`.
2. Run `python -m unittest discover -s tests -v`.
3. Review `docs/DATA_POLICY.md`.
4. Inspect raw terminal dumps, screenshots, notebook outputs and original bundles for secrets or data whose redistribution may be disallowed.
5. Review `git status` before the first commit.

## Final repository checks

After adding files or changing documentation, run:

```powershell
python tools/update_build_manifest.py
python tools/check_repo.py
python -m unittest discover -s tests -v
```
