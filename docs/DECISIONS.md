# Engineering decisions

## DEC-000 — Submission as source of truth

Status: ACTIVE

`submission/` is the canonical source used to build the competition archive. Research and notebooks are not copied into the submission ZIP.

## DEC-001 — Keep the scored package declarative and minimal

Status: ACTIVE

Use one LlmAgent, no custom Python entrypoint, no unnecessary sub-agent, no skills or unverified LoRA adapters. This reduces configuration surface and keeps the candidate easy to compile and compare.

## DEC-002 — Use bounded reasoning with a bounded tool budget

Status: EXPERIMENTAL

The October 23 public study reports the Budget-Fit reference using 28 tool calls, an eight-minute task budget, and a 4,096-token thinking budget. Current candidate settings follow that envelope. This is reference-informed, not a proven cause of better scores; paired evaluation is still required.

## DEC-003 — Lexical-first, evidence-driven graph tools

Status: ACTIVE

Use lexical search and focused file reads first. Call graph tools only when a named unresolved question justifies the call. Do not depend on incomplete graph outputs for correctness.

## DEC-004 — No score claims without artifact identity

Status: ACTIVE

Record the exact ZIP hash for hosted results. If a screenshot does not identify the candidate, retain the score as unattributed instead of joining it to a manifest row by date or filename alone.

## DEC-005 — Preflight before scored submissions

Status: ACTIVE

Every new candidate should pass the current official compiler and a bounded real-model smoke test before a user consumes a scored submission opportunity. Static validation is necessary but insufficient.
