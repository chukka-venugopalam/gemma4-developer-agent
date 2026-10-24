# Today's submission report — October 24, 2026

## Candidate

**GEMMA Reference-Calibrated V4** (reference-informed independent implementation; not the byte-identical public Budget-Fit bundle).

- File: `submission.zip`
- Size: 2,892 bytes
- SHA-256: `2394bbdec0fcd0700effb5f4f79de3f338f3fd4a8df5c1f1d5882da2d54457fa`
- Archive root: `agent.yaml`, `configs/sampling.yaml`, `eval_config.yaml`, `prompts/system.md`

## What the attached Prompt 7 forensic report establishes

- The original `submission-VNEXT.zip` fails on the tested old mirror because two relative `!include` targets are missing.
- `submission-VNEXT-INCLUDEFIX-ADDITIVE.zip`, EVIDENCE-V1, HYBRID-V2-ADAPTIVE and GRAPH-FUSION-V2 compiled and completed scripted fake-model replay against the **old mirror only** (`swegemma 0.2.7`, `adk-submission 0.2.11`). Those are not current Kaggle compiler or Gemma results.
- Prompt 7 could not query the user's live Kaggle submission metadata because Kaggle access/credentials were unavailable. Historical error causes remain unresolved.
- Prompt 7 says no candidate is eligible yet for a user-submitted run until the current wheelhouse preflight is completed.

## Why this candidate uses this envelope

A public independent study updated October 24 reports a Budget-Fit single-agent reference with a recorded best public score of 0.18 and settings of 28 tool calls, 8 minutes, and a 4,096-token reasoning cap. The article reports that its own unchanged files had scores across several observed host epochs, so this is evidence for a reference point, not a score guarantee. The report describes a small reasoning allowance as reducing repeated tool-call loops in one 22-task comparison, but does not establish a universal optimum.

Today's candidate adopts that **budget envelope** and retains a single root agent. It adds an independently written, bounded repair prompt emphasizing exact lexical localization, conditional graph use, no repeated failed calls, minimum edits, targeted tests, and a final diff review. It is not claimed to reproduce the reference's exact source or score.

Sources:
- Competition rules and required model: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview
- October 24 research review: https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/
- Public Budget-Fit notebook: https://www.kaggle.com/code/verracodeguacas/gemma-4-agent-budget-fit-single-agent

## Settings

| Setting | Value |
|---|---|
| Model | `gemma-4-31b-it-qat-w4a16-ct` |
| Root agent | Single `LlmAgent` |
| Declared tools | 9 official tools |
| Temperature / top-p / top-k | 0.2 / 0.95 / 40 |
| Max output tokens | 8192 |
| Thinking config | `thinking_budget: 4096`, `include_thoughts: true` |
| Per-task time | 8 minutes |
| Tool-call limit | 28 |
| Turn limit | 100 |
| Command / verification timeout | 300 seconds |

`eval_config.yaml` preserves the `evaluation:` wrapper accepted by the old-mirror preflight. The active competition wheelhouse was not available in this authoring environment, so current-scorer compatibility remains unproven.

## Checks actually run here

- ZIP integrity and exact four-file root layout: PASS
- Required model and nine tool names: PASS (static)
- YAML parse and expected fields: PASS
- `!include` target existence: PASS (static path check)
- Prompt curly-brace scan: PASS
- Archive traversal/absolute-path scan: PASS
- Deterministic artifact copy: PASS

## Not run / unresolved

- Current competition wheelhouse compilation: NOT TESTED
- Real Gemma 4 inference: NOT TESTED
- Real evaluator smoke test: NOT TESTED
- Any new hidden-task / public leaderboard result: UNKNOWN
- Exact causes of the historical Kaggle Error and Notebook Threw Exception rows: UNKNOWN without their individual `errorDescription` or traceback.

## Recommendation

Treat this ZIP as a **candidate**, not as a verified pass. The next safe gate is to run the supplied Prompt-7/Prompt-6 current-wheelhouse preflight in Kaggle with internet disabled, using a new notebook copy and no competition submission. Only submit after the current compiler accepts this exact hash and the bounded smoke test works.
