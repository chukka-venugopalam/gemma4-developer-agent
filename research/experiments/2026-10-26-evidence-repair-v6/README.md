# Evidence Repair V6 — 26 October 2026

## Hypothesis

V5's six-tool prompt/tool shape coincided with a screenshot score of 0.13 after two recent screenshot rows showed 0.18. The archive-to-score mapping is not available, so this is not a causal finding. V6 restores all nine registered tools while keeping graph tools conditional, keeps the best-documented Budget-Fit sampling envelope, and adds concise loop-recovery and `edit_file` mechanics informed by public trace research.

## Configuration

- Gemma 4 31B QAT; one root agent; no subagents, skills, adapters, or external models.
- Sampling: temperature 0.2, top-p 0.95, top-k 40, maximum output 8192, thinking budget 4096, thoughts retained.
- Evaluation: 8 minutes, 28 tool calls, 80 turns, 240-second command/verification timeout.
- Tools: nine documented tools, with graph calls only when they resolve a concrete uncertainty.

## Status

PASS: local YAML, include, prompt, registry-name, archive-integrity, manifest/build checks.
NOT TESTED: current official Kaggle compile, current-wheelhouse fake replay, real Gemma run.
UNKNOWN: hosted score and exact relation to any historical leaderboard row.

## Change from V5

- Restores the three code-intelligence tools to the declared registry (they remain conditional in the prompt).
- Replaces long repeated workflow wording with concise, enforceable anti-repeat recovery.
- Adds precise `edit_file` guidance: exact copied old string, short unique spans, split large edits, change approach after repeat failures.
- Keeps the 4096 reasoning budget used by the public Budget-Fit reference; it does not adopt the 512-token experiment because that was only a small paired local comparison against thinking-off, not against 4096.

## Decision

Hold for current-wheelhouse preflight. No official compile, real Gemma inference, or new Kaggle score is claimed. The target of beating 0.24 remains unproven.
