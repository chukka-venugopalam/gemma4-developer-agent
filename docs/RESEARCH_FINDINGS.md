# Consolidated Research Findings

This file summarizes conclusions across the supplied reports; consult the original reports for full methods, caveats, and citations.

## Research 1 — Submission forensics

**Finding:** original `submission-VNEXT.zip` has two broken relative includes inside `sub_agents/code_analyzer.yaml`, confirmed by running the tested loader/compiler against that archive. `submission-VNEXT-INCLUDEFIX-ADDITIVE.zip` adds copies at expected locations and passed compilation plus scripted fake-model checks against an older harness copy.

**Limits:** this does not prove the older defect caused the historical Kaggle errors, nor does it prove current scorer compatibility. Submission metadata/error descriptions are required to diagnose the exact rows.

Source: [`submission-forensics-2026-10-10.md`](../research/reports/submission-forensics-2026-10-10.md).

## Research 2 — Public-agent/SOTA research

**Finding:** the visible 0.10–0.12 examples were small, generally used thinking off and no LoRA, and included both single-agent and coder/analyzer shapes. Reported stronger 0.17–0.24 entries were not all source-inspected. Budgets, hard-failure prevention, and loop behavior ranked above retrieval sophistication in the report's hypotheses.

**Limits:** no clean controlled ablation proves these features caused the scores; leaderboard noise and changes to the harness confound comparisons. Some underlying forum and source claims were third-party relays.

Source: [`public-agent-research-2026-10-10.md`](../research/reports/public-agent-research-2026-10-10.md).

## Research 3 — Development set and ablations

**Finding:** the package proposed a public-data split and a staged ablation plan, and included helper tools.

**Limits:** its tests were synthetic; no actual Gemma run or task-resolution result was produced. Offline localization heuristics are not end-to-end SWE patch success.

Source: [`development-set-and-ablation-plan.md`](../research/ablation/development-set-and-ablation-plan.md).

## Prompt 6 — S0 preflight

**Finding:** the report records 26 static checks passing, including archive/layout checks and synthetic test cases for the validation utilities.

**Limit:** official compiler, actual harness loader/config application, fake-model replay through the current harness, real Gemma inference, and hidden-task evaluation were blocked because the official packages/runtime were not installed in that environment.

Source: [`s0-preflight-2026-10-15.md`](../research/reports/s0-preflight-2026-10-15.md) and [`notebooks/preflight-s0/RUN_ORDER.md`](../notebooks/preflight-s0/RUN_ORDER.md).

## Current submission

Budget-Aware V2 combines one root agent, nine documented tools, lexical-first localization, conditional symbol-grounded graph calls, output cap 4096, thinking configuration with `include_thoughts: false` and `thinking_budget: 0`, and a 5-minute/50-call/100-turn task envelope. Static audit report is preserved. This candidate is not officially compiled or Gemma-evaluated in this environment.
