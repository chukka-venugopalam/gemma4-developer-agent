# 2026-10-25 — Budget-Fit Reference-Aligned V5

## Decision

This candidate is a controlled implementation of the best-documented public configuration described in `2026-10-25-verified-methods-0.10-plus.md`. It is not the source author's original ZIP. It is intended to change the prior Reference-Calibrated V4 in the dimensions that the report says were mismatched: six core tools rather than nine, an 80-turn limit rather than 100, a 240-second command timeout rather than 300, and an explicit edit-by-about-call-12 policy with bounded verification.

The research shows a public score of 0.18 for a documented Budget-Fit single-agent configuration, another publication matching the configuration with its own reported score of 0.13, and leaderboard entries at 0.24. The source of the 0.20–0.24 methods was not accessible in this research. The attached screenshots show two recent successful user submissions at 0.18 and the leaderboard top at 0.24, but no candidate archive hash is linked to those rows.

## Configuration

- Base model: `gemma-4-31b-it-qat-w4a16-ct`
- Architecture: one `LlmAgent`, no subagent, no LoRA
- Tools: `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`
- Sampling: temperature 0.2; top-p 0.95; top-k 40
- Max output: 8,192 tokens
- Thinking: on; budget 4,096; include thoughts
- Per-task limits: 8 minutes; 28 tool calls; 80 turns
- Command timeout: 240 seconds

## Prompt policy

1. Contract-first: extract required behavior, symbols, signatures, error/return contract, and constraints.
2. Bounded lexical localization and short file reads.
3. Make an evidence-backed source edit by about call 12; this is a pressure heuristic, not permission to guess.
4. One focused check, at most one repair attempt, and one repeat of that check after repair.
5. No broad refactors, test edits, dependency installs, network use, or scratch files in the patch.
6. Anti-loop rules and explicit classification after repeated failure.
7. Inspect status and diff before a final `submit_patch` call.

## Validation

Locally, the repository validator checks the six core tools, closed tool registry, required files and includes, model, allowed extensions, thinking budget range, output-token range, evaluation schema, and prompt brace scan. The deterministic build is checked for archive integrity and a root-level `agent.yaml`.

Status at creation: local static validation and unit tests are run in the packaging environment; official current-wheel compilation, fake-model replay against current wheels, real Gemma inference, and hosted score are NOT TESTED. No score is claimed for V5.

## Why this is the current choice

V4 already had the reported 8-minute / 28-call / 8,192-output / 4,096-thinking settings but declared all nine tools and allowed 100 turns, and its prompt did not strongly enforce the public reference's early-edit policy. V5 makes these specific changes rather than adding an untested sub-agent, skill, LoRA, or long graph-retrieval phase.

This does not establish that V5 will beat 0.18 or the current 0.24 frontier. The next evidence gate is the current official Kaggle wheelhouse compiler and bounded real Gemma smoke test. Only after those pass should the user spend a scored submission opportunity.

## External sources checked 2026-10-25

- Public paper-track repository describing the 8-minute, 28-call, 80-turn, 8,192-output, 4,096-thinking, six-tool configuration and its reported 0.13 score: https://github.com/sourabghosh108-cc1/gemma4-budget-disciplined-agent
- Public Budget-Fit repository and local paired experiments (its 6,000-budget variant has no new Kaggle score): https://github.com/TheWayLost/gemmacodeagent
- Current visible public leaderboard: https://www.kaggle.com/competitions/gemma-4-developer-agent/leaderboard
- A recent Kaggle analysis notebook titled “Gemma 4 Agent — What Took LB 0.12 to 0.24”; full notebook content was not retrievable from the public page in this session, so its title is not treated as a verified method: https://www.kaggle.com/code/hitarthjain0/gemma-4-agent-what-took-lb-0-12-0-24
- Current publicly mirrored harness guide: https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md
