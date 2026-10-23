# Gemma 4 Developer Agent — Today's Submission Audit

**Candidate:** GEMMA-BUDGET-AWARE-V2
**Date:** 2026-10-22
**Submission archive:** `submission.zip`
**Named copy:** `submission-GEMMA-BUDGET-AWARE-V2-2026-10-22.zip`

## Decision

**Static package checks PASS. Official current-harness compilation and real Gemma execution are NOT TESTED in this environment.** This package is structurally clean, but must not be represented as officially compiled, smoke-tested, or score-validated.

## Research-driven changes

1. **Single root agent, no sub-agent.** The reported public evidence does not show that multi-agent architecture is required; a public single-agent notebook is listed at 0.18, although its implementation details and reproducibility are limited.
2. **Thinking explicitly disabled for the reported current wheel line.** `thinking_budget: 0` plus `include_thoughts: false` is used because the October 2026 wheel research reports that `include_thoughts: false` alone may not disable generation-time reasoning with `adk-submission 0.2.13`. This must be rechecked against Kaggle's actual mounted wheels.
3. **Bounded execution.** `max_time_minutes: 5`, `max_tool_calls: 50`, `max_turns: 100`, and `timeout_seconds: 300`. Five minutes times approximately 120 sequential tasks is 10 hours before setup overhead, leaving some margin under the 12-hour global budget; actual per-task overhead remains unknown.
4. **All nine documented tools declared, graph tools gated.** The older S0 declared only six tools even though task messages may describe graph tools. This candidate declares all nine to reduce the risk of attempting an undeclared graph tool. The prompt requires lexical-first search and permits graph inspection only when it answers a concrete uncertainty. `search_similar_code` must receive an exact symbol/node name, never an issue description or behavioral phrase.
5. **Controlled output ceiling.** `max_output_tokens: 4096` gives more room for a patch than the earlier 3072-token S0 while retaining approximately 28,672 tokens of context headroom against a 32,768-token model limit.
6. **Submission at the end.** The prompt requests a single final `submit_patch` after testing and diff review, avoiding reliance on the unverified assumption that work may continue after an early submit.
7. **No LoRA, skills, custom code, external model, or network installs.** Unverified adapters and unsupported extensions are excluded.

## Contents

- `agent.yaml`
- `eval_config.yaml`
- `configs/sampling.yaml`
- `prompts/system.md`

## Static check results

| Check | Result | Evidence |
|---|---|---|
| ZIP opens and CRC test passes | PASS | `zipfile.testzip()` returned no error |
| Archive contains exactly four expected files | PASS | Exact entry list checked |
| Exactly one root `agent.yaml` | PASS | ZIP inventory |
| Safe relative archive paths; no traversal or absolute paths | PASS | Entry-name scan |
| File extensions are allowed by published guide | PASS | `.yaml` and `.md` only |
| YAML parses using a custom `!include` constructor | PASS | Python/PyYAML parse |
| Include targets exist | PASS | Both referenced files found in archive source tree |
| Required base model exact | PASS | `gemma-4-31b-it-qat-w4a16-ct` |
| Nine tool names match the documented tool set | PASS | Set comparison |
| `eval_config.yaml` uses `evaluation:` wrapper | PASS | Parsed and values checked |
| Output and thinking settings match candidate design | PASS | Parsed and values checked |
| Prompt contains no curly braces | PASS | Character scan |
| Standard and named ZIPs identical | PASS | Byte-for-byte comparison |

## Effective configuration authored

```yaml
evaluation:
  timeout_seconds: 300
  max_tool_calls: 50
  max_time_minutes: 5
  max_turns: 100
```

```yaml
temperature: 0.2
top_p: 0.95
top_k: 40
max_output_tokens: 4096
thinking_config:
  include_thoughts: false
  thinking_budget: 0
```

## Not tested / blockers

- Official compile using the exact wheelhouse currently mounted by Kaggle.
- Whether the live wrapper actually applies the ZIP's `eval_config.yaml` or overrides limits from notebook settings.
- Live tool-call encoding and behavior after `submit_patch`.
- Real Gemma model startup or a one-task smoke run.
- Hidden-task evaluation, public score, or any improvement over prior submissions.

No official compiler, scorer, or GPU inference stack is installed in this container. The archive was not submitted to Kaggle.

## SHA-256 manifest

- `submission.zip`: `093531a857497faa04e15b618b708c0459ad813e9783df39a38654a3d70705e8`
- `submission-GEMMA-BUDGET-AWARE-V2-2026-10-22.zip`: same hash, byte-identical.

| File | SHA-256 |
|---|---|
| `agent.yaml` | `987dc3d0114fba465e933cef599453843346843a1c36b810654bf3a12bd760d7` |
| `eval_config.yaml` | `0f61b64a3879b25e9731b1de500a60a0f99cd329cc359466c8a7e60473e6f887` |
| `configs/sampling.yaml` | `6242110ce3e639e7ccc095b8024211e297965a6819f44131f7c56ba5737ced07` |
| `prompts/system.md` | `8e1aa3ead86638376db6c3afa39cab6584f7db9535aa401c3bf8c3c4f6c61b31` |

## Evidence used

- Official competition overview: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview — requires the specified Gemma model; score depends on validation tests; overall run budget is 12 hours and per-task `eval_config.yaml` limits are optional.
- Public harness guide (third-party mirror/source copy): https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md — documented tool registry, YAML/include contract, output/context limits, `eval_config.yaml` structure.
- October 2026 wheel/version analysis: https://github.com/cherrera0001/Agents_Learning_Loops/blob/main/STATE_OF_COMPETITION.md — reports `adk-submission 0.2.13`, reasoning-budget behavior and noisy leaderboard repeats. This is third-party research, not a guarantee about the exact current Kaggle scorer.
- Public single-agent notebook listing at 0.18: https://www.kaggle.com/code/samvalladares/gemma-4-agent-budget-fit-single-agent — score listing is a research lead, not evidence this candidate will match it.
