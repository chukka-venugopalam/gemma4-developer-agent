# Submission History and Attribution

## Attribution policy

Candidate ZIPs are immutable artifacts indexed in `submissions/manifest.csv`. A score or error is not attributed to a candidate just because the dates, filenames, or order appear to match. If Kaggle does not expose an uploaded SHA-256, leave `candidate_sha256` blank and mark the observation `UNATTRIBUTED`.

## Observed score values

Screenshots show successful score values of 0.00, 0.03, and 0.06. The public task-count denominator is inferred from research, not guaranteed by the screenshot itself. The exact ZIP hash for most score rows is unknown. Multiple `Kaggle Error`, `Notebook Timeout`, and `Notebook Threw Exception` events are also visible.

## Latest event — 22 October 2026

The latest supplied screenshot shows a row named `submission.zip` with status **Notebook Threw Exception**. The detail panel states that the notebook hit an unhandled error while rerunning code. It exposes no traceback, submission ID, public score, or artifact hash. The screenshot is preserved at `research/evidence/screenshots/2026-10-22-notebook-threw-exception.png`, and the observation is recorded as `OBS-008` in `evaluation/results/score_observations.csv`.

The event may correspond to a recent Budget-Aware V2 upload, but this association is not cryptographically verified and is deliberately left unattributed.

## Candidate archive

`submissions/manifest.csv` records unique recovered candidate ZIPs, hashes, sizes, member counts, aliases, and evidence caveats. Byte-identical archives are stored once. Inclusion in the archive does not mean official compilation passed, the ZIP was submitted, or a score was achieved.

## Current canonical source

`submission/` is the editable source for the Budget-Aware V2 candidate dated 22 October 2026. Build it with `python tools/build_submission.py`. The produced `dist/submission.zip` is a generated local artifact and should not replace archived historical versions.
