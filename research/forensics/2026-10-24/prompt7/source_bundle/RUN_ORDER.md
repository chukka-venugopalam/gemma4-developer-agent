# RUN_ORDER - nothing here submits to Kaggle or overwrites your existing notebooks/submissions

All commands are single-line PowerShell. Your Kaggle token stays on your machine: never paste it into a chat, notebook or file.

1. Unpack into a NEW folder (leaves everything you already have untouched):
   `Expand-Archive -Path .\GEMMA_FORENSICS_FOLLOWUP.zip -DestinationPath .\GEMMA_FORENSICS_FOLLOWUP ; Set-Location .\GEMMA_FORENSICS_FOLLOWUP`

2. Verify the package and the candidate archives against the shipped hashes:
   `Get-Content .\SHA256SUMS.txt | ForEach-Object { $h,$f = $_ -split '\s+\*?',2; if ($f -and (Test-Path $f)) { '{0} {1}' -f ((Get-FileHash $f -Algorithm SHA256).Hash.ToLower() -eq $h), $f } }`

3. Free, read-only: export your submission rows (needs a working Kaggle login on your machine; makes no submission):
   `python -m pip install --upgrade kaggle ; python .\fetch_submission_metadata.py --out-dir .\meta_run1`
   Exit 3 = BLOCKED (no/invalid credentials or no network; follow the printed hint). Then open `.\meta_run1\SUBMISSION_METADATA_SUMMARY.md`: it lists ref, UTC time, status, score, uploaded bytes, `errorDescription`, and a SIZE-ONLY match to `candidate_manifest.csv`.
   Refresh later to catch rescored rows: `python .\fetch_submission_metadata.py --previous .\meta_run1\submission_metadata.json --out-dir .\meta_run2`

4. The gate: current-wheelhouse preflight on Kaggle (no submission slot, no GPU needed for the default cells).
   - Kaggle > New Notebook > File > Import notebook > `KAGGLE_CURRENT_WHEELHOUSE_PREFLIGHT.ipynb`.
   - Add data: competition `gemma-4-developer-agent` and dataset `metric/gemma-4-developer-agent-wheelhouse`. Internet OFF.
   - Read cell 2's warning: compare it with the organizer starter's current install cell; use theirs if different.
   - Optional: upload your Prompt-6 "S0" zip as a private dataset and attach it; cell 5 finds any zip with `agent.yaml` at its root.
   - Run all. Download `preflight_logs.zip` from the Output tab (no secrets in it) and read the table printed by the last cell.
   - Optional deeper check: set `RUN_OFFICIAL_EVALUATOR_SMOKE = True` in cell 1 (one task, scripted fake model, real Evaluator).

5. Decide from the evidence, not from this package:
   - Any candidate whose `compile_submission` is FAIL on the current wheels: REJECT.
   - Candidate compiles AND the thinking-variant table shows `enable_thinking=false` on the wire for its settings: it can move from HOLD to ELIGIBLE FOR A USER-SUBMITTED SMOKE RUN. You press the button; no score is promised.
   - Anything else: HOLD.

Files you must keep as they are: `candidates\*.zip` (hash-pinned), `reference\preflight_compile.py` (the Mission-1 original, unmodified).
