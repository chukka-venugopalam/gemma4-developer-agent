# Budget-Fit reference review — 2026-10-23

## Purpose

This is a compact decision memo for today's agent candidate. It summarizes published findings; it is not a reproduction of the referenced bundle or a claim of local/hosted evaluation.

## New evidence reviewed

A public technical write-up published on 2026-10-23 reports the unchanged public **Budget-Fit Single Agent** reference with 28 tool calls, an eight-minute per-task/session budget, and a 4,096-token thinking budget. The author's observation history includes public scores from 0.15 to 0.18 across several reported host epochs, but the observations are not all same-environment repeats. The author explicitly retains the unchanged reference as its current working choice and cautions that identical ZIPs have scored differently.

The same report describes a paired 22-task local comparison where a 512-token reasoning cap reduced repeated-call streaks versus the historical thinking-disabled configuration; resolved tasks moved from 5 to 7, which was not statistically compelling by itself. This supports bounded reasoning as a plausible intervention, not a guaranteed score gain. The reported reference's 4,096-token budget gives us a stronger configuration lead than our previous S0 candidate, which explicitly disabled thinking.

The current public harness guide documents the root `evaluation:` key in `eval_config.yaml`, the nine registered tools, a 32,768-token context ceiling, the supported `thinking_budget` field, and `submit_patch()` as a terminal action. It also specifies the `!include` path rules. These facts were checked against the public guide; the official live wheelhouse was not available in this environment.

## Today's candidate choice

`submission/` is an independently written, reference-informed single-agent candidate, not a byte-for-byte copy of the public reference package. It uses:

- Base model `gemma-4-31b-it-qat-w4a16-ct`.
- One root agent; no sub-agent, skill, LoRA, or custom tools.
- All nine documented tool names declared, so that code-intelligence tools mentioned in task context are not undeclared. Graph calls are optional and symbol-grounded.
- Temperature 0.2, top-p 0.95, top-k 40.
- Maximum output 8,192 tokens, thinking budget 4,096, `include_thoughts: true`.
- Per-task limits of 8 minutes, 28 counted tool calls, and 100 turns; command timeout 300 seconds.
- A concise evidence-first repair prompt with anti-loop behavior, minimal edits, targeted verification, final diff review, and one final `submit_patch()` call.

These settings align with the reported public reference's most salient envelope and bounded-reasoning values. We do not have the author's exact archive bytes; therefore we do not claim exact replication or inherit the 0.18 score.

## Important risk

Eight minutes is only a ceiling, not an average. The whole generation run has a 12-hour limit, and exceeding it can invalidate a run. Actual task-time distribution on Kaggle is not measured for our candidate. The 28-call cap helps contain repeat loops, but may truncate difficult issues. The current candidate has passed local structural checks only; official compilation and real Gemma inference remain untested here.

## Submission incident

The latest supplied Kaggle screenshot shows `Notebook Threw Exception` and the message that the notebook encountered an unhandled error during rerun. It contains no traceback, submission reference, exact uploaded archive hash, or public score. This incident remains **unattributed**. Do not conclude that a specific YAML key or the agent prompt caused it without the notebook output logs.

A separate screenshot shows a successful public score of 0.03; earlier screenshots show 0.06 and 0.00. Their uploaded artifact hashes are not exposed by the screenshots, so the scores cannot be assigned to exact candidate archives.

## Next gates

1. Run current official preflight in a Kaggle notebook with the competition wheelhouse mounted.
2. Capture the full exception traceback from the most recent failed notebook run before diagnosing it.
3. Run a bounded one- or two-task real Gemma smoke test without submitting it for scoring.
4. Preserve exact ZIP SHA-256, notebook version, wheel versions, and status/score for any subsequent hosted submission.
5. Do not claim a score improvement unless the hosted score is observed; interpret one-run differences cautiously.

## Sources

- Official public harness guide: https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md
- Pilkwang Kim, “Gemma 4 Developer Agent, Part 2: Measuring an Agent While Its Evaluator Moved,” 2026-10-23, CC BY 4.0: https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/
- Competition overview: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview

The public article is third-party measurement. Its observed scores are not independent guarantees and its private harness deployment timeline is not fully observable.
