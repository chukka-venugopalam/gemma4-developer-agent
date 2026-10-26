# Gemma Evidence Repair V6 — candidate report

Date: 2026-10-26

## Why this candidate

The submitted screenshots show scores of 0.18, 0.18, then 0.13. The screenshots do not bind these results to archive hashes, so the precise score-to-candidate mapping is unconfirmed. The newer public methods report records the Budget-Fit reference at 0.18 with a single agent, thinking enabled with a 4,096-token budget, 8,192 output tokens, 28 tool calls, an eight-minute cap, and a short task workflow. A recent independent analysis found that a 512-token reasoning setting sharply reduced repeat-call streaks against thinking-off in a small 22-task local comparison; it also notes that exact candidate score changes are noisy and that no available experiment establishes a causal path to the 0.24 leaders.

V6 retains the strongest documented public reference settings and all nine registered tools as in the user's V4-style candidate, while simplifying the prompt around concrete, evidence-based edits, exact `edit_file` mechanics, conditional symbol-based graph use, and immediate recovery from repeated calls. The `BUDGET-FIT` V5 variant had only six declared tools and received 0.13 in the screenshot timeline, but causality cannot be inferred because submissions are not mapped to ZIP hashes and leaderboard runs are noisy.

## Configuration

- Model: `gemma-4-31b-it-qat-w4a16-ct`
- Sampling: temperature 0.2; top-p 0.95; top-k 40
- Output: 8,192 tokens; thinking budget 4,096; include thoughts true
- Evaluation: 8 minutes; 28 tool calls; 80 turns; timeout 240 seconds
- Tools: nine documented registry tools
- No adapters, skills, or sub-agents

## Validation results

- ZIP integrity: PASS
- Required archive root and exactly one root agent config: PASS
- YAML syntax: PASS
- Include targets: PASS
- Required model and registered tool names: PASS
- Prompt contains no curly braces: PASS
- Extension/path policy: PASS
- Deterministic build: PASS
- Official current Kaggle compile: NOT TESTED
- Fake-model replay on current wheelhouse: NOT TESTED
- Real Gemma inference: NOT TESTED
- Hosted score: UNKNOWN

## Key risks

1. The public 0.24 leaderboard implementations remain unknown; this candidate is not a verified reconstruction of them.
2. The eight-minute per-task ceiling does not guarantee the whole run completes within 12 hours. No current per-task duration distribution is available here.
3. No archive hash has been matched to the shown 0.13 / 0.18 rows.
4. Nine tools avoid a mismatch between available tools and task-provided tool mentions, but optional graph use may add overhead; it is discouraged unless it resolves a concrete uncertainty.
5. Score variance and harness changes make a single public score an unreliable causal test.

## Recommendation

Run the current official wheelhouse preflight and bounded smoke test before spending a scored submission. If the live compile or fake-model tool wiring fails, do not submit. If it passes, retain the archive SHA-256 in the experiment ledger and compare the eventual result to previous scores. There is no guarantee this candidate exceeds 0.18 or 0.24.


## Final artifact

- Archive: `submission.zip`
- Size: 3215 bytes
- SHA-256: `e15b4cbcb48e6e66be625b840958fc27503a66598904dc66a2b3b4958df30a80`
- Named archive byte-identical: yes
