# GEMMA S0 Kaggle run order

Purpose: finish the checks that could not run elsewhere (official validators, eval_config loading, one-task smoke test) and **stop before any competition submission**. Nothing in this procedure touches the notebook version that is already running, and nothing in it submits.

Evidence status: the cells in `notebook/gemma_s0_preflight.ipynb` were rehearsed only against synthetic fixtures. The STARTER cells were not available to the author; instructions for them are edits to describe, not code.

## 0. Preparation (before opening Kaggle)

1. Verify the pack's candidate: `sha256sum candidate/submission.zip` must print `359a50986e9c23926cd99da853ad30fa399291947a9e9fc68b5906339156cf1b`.
2. Create a **new private Dataset** named `gemma-s0-preflight-pack` containing `GEMMA_S0_PREFLIGHT_PACK.zip` (or its extracted files). Do not add it to, or edit, any existing dataset.
3. Open the official starter notebook and choose **Copy & Edit**. This creates a new notebook. Do not open the running notebook for editing, save a version of it, stop it, or replace its output.
4. In the new notebook's Input panel confirm: the competition (Google - The Gemma 4 Developer Agent Competition), the model resource the starter uses, and your `gemma-s0-preflight-pack` dataset. Settings: **Internet off**, persistence off, accelerator as in the starter (you may set it to None for Cells 1 to 10).
5. Add the cells from `notebook/gemma_s0_preflight.ipynb` at the positions below (copy and paste, or upload that notebook and move the cells). Keep the starter's cells in their original order.

## 1. Cell order

"Ours" cells are in the pack's notebook. "STARTER" cells are the official starter's.

| Cell | Who | Name | What it does | Pass criterion | If it fails |
|---|---|---|---|---|---|
| 1 | ours | Safety rails | Defines output folder `/kaggle/working/preflight_out`, the expected S0 hash, and refuses to run if a `submission.zip` or `submission.parquet` exists in `/kaggle/working` | Prints the reminder, no assertion | Delete the stray file, restart; never reuse a session that produced a submission file |
| 2 | ours | Locate pack | Finds the pack in the mounted dataset, imports the helpers, runs their self-test | `selftest: ALL PASS` | Fix the dataset attachment; do not continue |
| 3 | ours | Mounted inputs | Lists where `HARNESS_README.md`, `sample_submission/`, `wheels/`, `tasks.jsonl`, `snapshots/` are mounted; prints Python and package versions | `harness_readme`, `sample_submission`, `wheels`, `tasks_jsonl` all found | Missing input means the matching later check is BLOCKED; attach the competition data |
| 4 | STARTER | Setup | Run the starter's offline wheel install and import cells **unchanged**. Stop before the cell that launches the model server. Never run its final zip or submission cell | Harness packages import | An install that wants the network means stop: this gate is offline-only |
| 5 | ours | Package versions | Records versions and file locations of `swegemma`, `adk_submission`, `adk_eval_core`, `google.adk` | All four import; versions saved | Do not continue; official checks cannot run |
| 6 | ours | Stage S0 | Checks the S0 hash, extracts it safely to `/kaggle/working/preflight/s0_agent`, runs the static audit | Hash equal; audit exit 0 | Any FAIL means NOT READY |
| 7 | ours | Compare with official sample | Compares layout with the official `sample_submission/`, `eval_config.yaml` nesting first | `VERDICT: MATCH` | `MISMATCH` means STOP and re-check the contract before anything else |
| 8 | ours | Official loader source | Finds `scripts/inference.py` and prints the source of `load_submission_eval_config` using `ast` only (nothing is executed) | Source read; it reads the `evaluation` key | File not found means this check is BLOCKED; a loader that does not read `evaluation` means NOT READY |
| 9 | ours | Official validators | Discovers `validate_directory`, `validate_single_declared_model`, `compile_submission`, `discover_declared_models` by introspection and calls only those whose signature takes just the archive directory | No FAIL; anything INCONCLUSIVE is read by a human | A FAIL means NOT READY |
| 10 | ours | Fake-model probe | Captures `swegemma eval --help` and scans for a documented fake, stub, scripted or mock model option | Result stated honestly | No documented option means fake-model replay stays BLOCKED; do not improvise one |
| | | *Switch point* | If you ran Cells 1 to 10 without a GPU, switch to the starter's GPU setting now and rerun Cells 1, 2, 3, 4, 5 | | |
| 11 | STARTER | Smoke-test edits | Read the instructions in the notebook cell, then apply exactly the five edits to the starter's server, evaluator and run cells | | |
| 12 | ours | Fixed task id | Reads only `instance_id` from `tasks.jsonl` and picks the first in sorted order; saves it | Prints the id | |
| 13 | STARTER | Run | Run the edited starter cells once for that single task. Interrupt after 15 minutes if the evaluator is still running | A results folder appears | Interrupt, then run Cell 14 to collect partial output |
| 14 | ours | Collect and check | Copies artifacts to `preflight_out/smoke`, prints scalar result fields (patch bodies omitted), extracts the first user message, asserts the Task Budget lines (5.0 minutes, 50 calls, 100 turns), lists tool names, counts calls after the first `submit_patch` | Budget lines PASS; no undeclared tool; run reached a first tool call | Budget lines at 60 / 100 / 500 mean `eval_config.yaml` was not applied: NOT READY |
| 15 | ours | Manifest and stop | Hashes every output, writes `s0_preflight_outputs.zip`, asserts that no submission file exists | Archive created; no submission file | Delete any submission file |

## 2. Reading the result

| Outcome | Meaning |
|---|---|
| Cells 5, 6, 7, 8, 9 pass; smoke run reached a first tool call; Cell 14 budget lines show 5.0 / 50 / 100; no undeclared tool in the trace | `SAFE TO TRY`: the official path accepted the exact S0 ZIP and applied its limits. It says nothing about score |
| Any official validator FAIL, a layout MISMATCH, budget lines at the defaults, or the agent not starting | `NOT READY` |
| Cells 5, 8 or 9 cannot run | Still `BLOCKED`; report which input is missing |

One task resolved or unresolved says nothing about the leaderboard score. Judge the wiring, not the outcome.

## 3. Stop rules

- Never press **Submit** on this notebook. Never run the starter's zip or submission cell.
- If `/kaggle/working/submission.zip` or `submission.parquet` exists at any point, delete it and do not use that session for anything else.
- Do not use *Save & Run All* or commit while the smoke test is incomplete.
- After Cell 15: download `s0_preflight_outputs.zip`, then end the session.
- Do not upload anything to the competition until the gate result is `SAFE TO TRY`. The competition upload steps are in the earlier `S0_VALIDATION_REPORT.md`, section 11.

## 4. Time and quota (third-party estimates)

Cells 1 to 10: minutes, no GPU. Model-server start-up reported at up to about 20 minutes; S0's own cap is 5 minutes for the single task. Plan about 40 minutes of GPU time.
