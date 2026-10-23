# Project status and next steps

**Review date:** 2026-10-23

## Current state

- Canonical source: `submission/` (Budget-Fit-Inspired V3).
- Base model: `gemma-4-31b-it-qat-w4a16-ct`.
- Candidate design: single agent, bounded reasoning (`thinking_budget: 4096`), 28 counted tool calls, 8 minutes, 100 turns, max output 8,192.
- Local static validator: passed in the packaging build for this snapshot.
- Repository unit tests: see test output in the release record; must be rerun in any new environment.
- Official compiler/current wheelhouse: not executed here.
- Real Gemma inference: not executed here.
- Current hosted score for this exact candidate: none.
- Latest incident: a screenshot shows `Notebook Threw Exception`; error details/traceback and exact submitted ZIP hash are unavailable.

## Decision

The October 23 candidate follows the envelope of a publicly reported higher-scoring single-agent reference. This is a candidate selection based on third-party observations, not a causal claim. The public study reports score variation for identical files across scorer epochs and does not establish that every difference is due to prompt or architecture changes.

## Priority order

### P0 — Diagnose the exception

Download the output of the Kaggle notebook version that produced the latest `Notebook Threw Exception`. Save the complete Python traceback, notebook version, elapsed runtime, and visible submission reference. Do not assign the error to the agent ZIP without that evidence.

### P1 — Compile with the current wheelhouse

Run `notebooks/preflight-s0/GEMMA_S0_PREFLIGHT_PACK.zip` instructions or create a clean preflight notebook from the official starter. Use the currently attached wheelhouse rather than the older mirrored package versions. Verify the exact current candidate ZIP and record versions, compiler output, and exit code.

### P2 — Run a bounded inference smoke test

On one or two non-lockbox public development tasks, save model/tool traces, token counts, call count, time, final patch, and verifier result. Do not run the full dataset or submit automatically.

### P3 — Decide whether to score

Submit only after compilation and smoke-test gates pass. Record the ZIP SHA-256. Because hosted score variance exists, do not interpret a small score movement from a single run as proof of improvement.

### P4 — Next research experiment

Use the same fixed tasks to compare this bounded-reasoning candidate against the previous thinking-disabled S0. Change one major factor at a time, track repeated-call streaks and patch capture, and retain task-level paired results. Do not introduce sub-agents, LoRA, or domain priors until an observed failure supports the change.

## Open questions

- What exact error caused the latest Notebook Threw Exception?
- Which historical ZIP hash generated the 0.03, 0.06, and 0.00 scores?
- Does the current Kaggle wheelhouse compile this candidate without changes?
- Does the current model/host complete the full public+private run inside 12 hours?
- Do capped reasoning and 28-call budget improve success over S0 on matched tasks?
