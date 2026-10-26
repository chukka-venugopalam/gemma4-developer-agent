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


## 2026-10-26 — Evidence Repair V6

- **Hypothesis:** V5's six-tool configuration coincided with a 0.13 screenshot row after two recent 0.18 rows; archive-to-score identity is unknown, so causality is not established. Restore all nine declared tools to align with the user's earlier nine-tool candidate, but make graph use conditional and symbol-grounded. Tighten repeated-call recovery and `edit_file` mechanics using recent trace research.
- **Sampling retained:** temperature 0.2, top-p 0.95, top-k 40, 8192 max output, thinking budget 4096 with thoughts retained. The 512-token local comparison was not substituted because it compared against thinking-off, not against the 4096 reference.
- **Budget:** 8 minutes, 28 tool calls, 80 turns, 240-second command/verification timeout. Eight minutes is a per-task ceiling, not a guarantee that the complete run fits the global 12-hour limit.
- **Result:** local static validation and reproducible build PASS. Current-wheelhouse compile, fake-model replay on current wheels, real Gemma inference, task-time distribution, and hosted score are NOT TESTED.
- **Decision:** hold for current official wheelhouse preflight. No score above 0.18 or 0.24 is claimed.
- **Research:** https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/ and https://github.com/8kta/kaggle-gemma4/blob/main/submission/prompts/system.md
