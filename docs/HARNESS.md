# Competition harness notes

**Last reviewed:** 2026-10-23. This is a concise, source-attributed summary, not a replacement for the current official harness or wheelhouse.

## Submission contract

- The ZIP root must contain exactly one supported root agent config, normally `agent.yaml`.
- The model used by the main agent is `gemma-4-31b-it-qat-w4a16-ct` for this candidate.
- Configuration, prompts, and optional sub-agent files can be referenced with relative `!include` paths. Do not use absolute paths or `..` traversal.
- `eval_config.yaml`, when present, uses an `evaluation:` wrapper.
- The current public guide lists nine sandbox tools: `run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`, `search_similar_code`, `get_code_neighbors`, and `get_code_subgraph`. Declare only documented tools; do not make up tool names.
- The public guide states that `submit_patch()` marks the patch submitted and ends the agent loop after the current turn completes. It does not count toward the normal tool-call budget. Use it after intended edits and checks, not early.

## Budgets and generation

`eval_config.yaml` fields are optional and sit under `evaluation:`. The public guide describes `max_time_minutes`, `max_tool_calls`, `max_turns`, and `timeout_seconds`. The last field also acts as the single-command timeout in the published reference. Environment overrides may take precedence in the notebook, so inspect the actual run configuration.

The published generation schema documents `max_output_tokens` and `thinking_config.thinking_budget`; the cited guide gives the context ceiling as 32,768 tokens. A public Oct 23 study reports a high-scoring single-agent reference using 28 tool calls, an eight-minute per-task limit, and 4,096 tokens of reasoning. Those settings are the evidence behind this candidate, not an official guarantee of performance.

A positive thinking budget enables bounded reasoning in the current bridge described by the Oct 23 study; `include_thoughts` controls whether earlier thought content is retained in history, rather than being the sole switch for reasoning. Because the exact deployed scorer version is not visible from this environment, test the candidate through the current wheelhouse before submission.

## Tool-use precautions

- Search exact identifiers, error text, parameters, constants, and test names before trying graph tools.
- Stop after an empty result and change the query; do not repeat the same empty call.
- Use `get_code_neighbors` on a known symbol. Use `search_similar_code` and `get_code_subgraph` only when their output can resolve a specific uncertainty. Do not treat graph completeness as guaranteed.
- Keep reads and command output small to control context use.
- Never leave temporary files in the workspace: patch extraction uses the repository diff.
- Run targeted verification and inspect the final diff before `submit_patch()`.

## Required pre-submission gate

1. Use a fresh Kaggle notebook copy; preserve any running notebook.
2. Attach the actual current competition wheelhouse and record Python/package versions.
3. Run official validation and compilation. Keep exact logs and exit codes.
4. Run fake-model wiring checks if supported.
5. Run a bounded one- or two-task real Gemma smoke test before a scored run.
6. Record exact candidate SHA-256, notebook version, submission reference, status, and score.

This repository's local validator is not the official compiler. Local structural checks alone must not be reported as “Kaggle-ready” or “officially passed.”

## Sources

- [Current public HARNESS_README mirror](https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md)
- [Gemma 4 Developer Agent, Part 2: Measuring an Agent While Its Evaluator Moved (2026-10-23)](https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/)
- [Competition overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
