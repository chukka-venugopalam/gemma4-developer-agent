# Adding research, submissions, and evaluation results

Keep source code and evidence separate. Never overwrite a historical candidate: add a new dated artifact and update the ledgers.

## Add a research report

1. Save the report under `research/reports/` using `YYYY-MM-DD-short-topic.md`.
2. Include source URLs, observation date, method, confidence/evidence status, and what could not be verified.
3. Preserve the original raw ZIP, log, or external artifact under `research/bundles/` when appropriate and legally redistributable.
4. Update `docs/STATUS_AND_NEXT_STEPS.md` if the decision changes.

## Add a submission candidate

1. Edit the canonical source in `submission/`.
2. Run `python tools/validate_submission.py` and `python tools/build_submission.py`.
3. Copy the generated archive into `submissions/archive/submission-YYYY-MM-DD-short-name.zip`.
4. Run `python tools/register_artifact.py --kind submission --source submissions/archive/submission-YYYY-MM-DD-short-name.zip --date YYYY-MM-DD --title "Short name" --status "built; not officially compiled"`.
5. Keep the exact SHA-256, bytes, source commit, configuration, validation evidence, and model version in `submissions/manifest.csv` or the experiment record.

## Record a Kaggle result

Add a row to `evaluation/results/submission_history.csv`. Include the observation date, Kaggle ref if available, status, score, notebook version, local ZIP hash, and log path. If the hash or mapping is not exposed, write `unknown`, not an inferred match. Do not assign a numeric score to errors/timeouts.

## Evidence labels

- `STATIC_PASS`: structure and local checks only.
- `OFFICIAL_COMPILE_PASS`: current official compiler accepted the exact archive.
- `FAKE_REPLAY_PASS`: wiring works with scripted responses; not a model-quality result.
- `GEMMA_SMOKE_PASS`: real inference ran on a stated task set; not a leaderboard score.
- `HOSTED_SCORED`: Kaggle published a score for the recorded submission.
- `BLOCKED` / `UNKNOWN`: evidence is unavailable.

## Before committing

Run `python tools/check_repo.py`, `python -m unittest discover -s tests -v`, `python tools/validate_submission.py`, and inspect `git diff --check` plus the candidate archive manifest. Keep credentials and private keys out of the repository.
