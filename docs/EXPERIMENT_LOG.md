# Experiment Log

| ID | Change | Result | Decision |
|---|---|---|---|
| — | Baseline not started | — | — |

| 2026-10-24 V4 | Reference-calibrated single-agent candidate: 8 min, 28 calls, 4,096-token reasoning cap; lexical-first prompt, anti-loop rules, all nine documented tools | Static validation and deterministic build passed locally; current-wheelhouse compile, real Gemma inference, and hosted score not tested | Hold for current-wheelhouse preflight; do not claim improvement until a dated hosted result is linked to this archive hash |


## 2026-10-25 — Budget-Fit Reference-Aligned V5

- Source: public-method review recorded in `research/reports/2026-10-25-verified-methods-0.10-plus.md`.
- Candidate changes: six core tools, 80-turn cap, 240-second command timeout, and explicit edit-by-about-call-12 / one-check-one-repair policy. Sampling retains temperature 0.2, top-p 0.95, 4,096 thinking budget, and 8,192 output cap.
- Rationale: align with the best-documented public reference rather than adding unverified graph/subagent complexity.
- Status: static validation/build only; official current-wheel compile, real inference, and hosted score not tested.
- Screenshot observation: two successful user submissions displayed 0.18; leaderboard screenshot showed four teams at 0.24; archive identity for those rows unknown.
