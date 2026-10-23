# GEMMA S0 preflight report

**DECISION: BLOCKED — OFFICIAL COMPILER UNAVAILABLE**

Candidate: `submission.zip`, SHA-256 `359a50986e9c23926cd99da853ad30fa399291947a9e9fc68b5906339156cf1b`, 2,290 bytes, **unchanged** (no defect was found, so nothing was rebuilt).
Evidence timestamps come from the sandbox clock (environment probe 2026-10-18T04:19:08Z; validator run 2026-10-17). I did not submit anything to Kaggle and did not touch any notebook.

**Why blocked.** None of the official inputs the gate needs exist in this environment: no `gemma_reserach2_next.zip` or any other attachment, no mounted competition input, no `HARNESS_README.md`, no `wheels/`, no `sample_submission/`, no starter notebook, no 0.06 ZIP, no failed ZIP or Kaggle logs. `swegemma`, `adk_submission`, `adk_eval_core` and `google.adk` are not installed, and there is no network, no GPU and no `/kaggle` mount. The official validator and compiler, a fake-model replay and the real-model smoke test therefore could not run, and **S0 is not officially validated.** I delivered the strongest static evidence available, a tested helper pack, and an exact Kaggle run order that finishes the blocked checks.

## 1. What was available

| Item named in the task | Status here |
|---|---|
| `gemma_reserach2_next.zip` | **Not found.** The two S0 ZIPs from the previous deliverable are in the outputs folder; their SHA-256 equals the hash quoted in the task, so they are the same bytes |
| `PUBLIC_AGENT_RESEARCH.md` | Present from the previous turn (outputs folder); not re-attached |
| Previous 0.06 ZIP; failed ZIP; Kaggle error logs or screenshots | **Not supplied** |
| Official starter notebook; mounted `HARNESS_README.md`, `wheels/`, `sample_submission/` | **Not supplied.** Contract evidence below comes from a third-party copy of the 671-line harness guide (https://github.com/rishaviitd/kaggle.gemma.coding.agent/blob/main/context/harness.md, read in full this session), not from the mounted file |

## 2. Candidate identity (Phase 1.1, 1.2)

Both outputs are byte-identical (`cmp` reports IDENTICAL), CRC test passes ("Done testing"), and the shared hash equals the one in the task statement.

| Path in archive | Bytes | SHA-256 |
|---|---|---|
| `agent.yaml` | 337 | `60380de676031d4c6d0c28ed0251ac9a2d1a3f2a4a838e17f32087c17fc6747c` |
| `configs/sampling.yaml` | 106 | `b5c37e37fc280f333b1e8f17c003701b373a5cd06bd754cc6c959c3df9ee151a` |
| `eval_config.yaml` | 95 | `0f61b64a3879b25e9731b1de500a60a0f99cd329cc359466c8a7e60473e6f887` |
| `prompts/system.md` | 3043 | `03ec8aa8c16a8b6506be5ef5f08ff43b7252092bb9a37ef2d2468486ea78bfd1` |

## 3. Results by phase

| Phase | Status | Evidence |
|---|---|---|
| 1. Reproducible archive audit | **PASS** (static), with the official-loader parts **BLOCKED** | 26 PASS, 0 WARN, 0 FAIL, 4 BLOCKED; 23 of 23 injected defects caught by the validator (§4) |
| 1.3 / 1.7 real harness include loader and eval_config loader | **BLOCKED** | The emulated loader parses everything (Y01, Y08); the official loader was not available, so "limits actually loaded" is not proven |
| 2. Official validator and compiler | **BLOCKED** | `official_harness_check.py` ran and reported BLOCKED (exit 3): all four official packages are absent. Exact notebook cells to finish this: run-order Cells 5 to 9 |
| 3. Fake or scripted-model replay | **BLOCKED** | No harness here. The harness guide copy I read does not describe a fake-model option (it describes a model server at 127.0.0.1:8000), so Cell 10 checks the official CLI help for one instead of assuming it |
| 4. One-task Gemma smoke test | **BLOCKED** | No GPU, model or runtime. Run-order Cells 11 to 15 |
| 5. Change policy | **PASS** | S0 untouched; hash unchanged; no prompt, tool, token or thinking change; scripts, logs and notebook are outside the ZIP; no earlier file overwritten |

**Did official compilation pass? No, it did not run. Did real inference run? No.**

## 4. Static checks (all against the same-hash archive)

Kind separates static ZIP validation, YAML validation (my emulation of the documented include rules, not the official loader), official compilation, fake-model replay, real Gemma inference and hidden-task evaluation.

| ID | Kind | Check | Status |
|---|---|---|---|
| Z01 | Static ZIP | archive opens and CRC32 verifies | **PASS** |
| Z02 | Static ZIP | entry names are safe (no absolute/../symlink/hidden/duplicate) | **PASS** |
| Z03 | Static ZIP | only allowed file extensions (.yaml .yml .md .txt .py .json .safetensors) | **PASS** |
| Z04 | Static ZIP | minimal file set with agent.yaml at the archive root | **PASS** |
| Z05 | Static ZIP | size and count limits (<3 GiB, <=10,000 files, <=1,000 YAML files, YAML <=50 MiB) | **PASS** |
| Z06 | Static ZIP | exactly one root config file | **PASS** |
| Y01 | YAML (emulated loader) | YAML parses with the documented !include rules (relative, no .., depth<=10, no cycles, no duplicate keys) | **PASS** |
| Y02 | YAML (emulated loader) | exactly one root LlmAgent (no sub-agents, agent_tool or inline agents) | **PASS** |
| Y10 | YAML (emulated loader) | agent_class omitted: relies on the documented default (LlmAgent) | **PASS** |
| Y03 | YAML (emulated loader) | model is exactly gemma-4-31b-it-qat-w4a16-ct (single base model) | **PASS** |
| Y04 | YAML (emulated loader) | tools are exactly the six documented base tools (subset of the official registry) | **PASS** |
| Y05 | YAML (emulated loader) | agent fields are documented LlmAgent fields; S0 adds no skills/sub-agents/adapters | **PASS** |
| Y06 | YAML (emulated loader) | generate_content_config uses only documented fields within documented ranges | **PASS** |
| Y07 | YAML (emulated loader) | S0 sampling: T=0.2, top_p=0.95, top_k=40, max_output_tokens=3072, thinking disabled with no budget | **PASS** |
| Y08 | YAML (emulated loader) | eval_config.yaml has the four documented fields (nested layout) with the S0 values | **PASS** |
| Y09 | YAML (emulated loader) | nested `evaluation:` layout follows the documented contract (task statement of 2026-10-17 confirms it) | **PASS** |
| P01 | Prompt (static) | prompts/system.md present, UTF-8, LF, non-empty, equals the resolved instruction | **PASS** |
| P02 | Prompt (static) | no curly brace characters (ADK would treat {identifier} as a state key) | **PASS** |
| P03 | Prompt (static) | names all six declared tools and refers to no graph/similarity/helper/skill/custom tools | **PASS** |
| P04 | Prompt (static) | no literal shell-command examples (actions described in prose via run_command) | **PASS** |
| P05 | Prompt (static) | all 25 required behaviours are stated (localization, context, reproduction, root-cause gate, verification, loops, submission, budget, turns, tool correctness) | **PASS** |
| P06 | Prompt (static) | every snake_case identifier in the prompt is one of the six declared tools (no undeclared tool-like names) | **PASS** |
| B01 | Budget arithmetic | 12-hour worst-case projection (every task hits its cap; third-party estimate model) | **PASS** |
| B02 | Budget arithmetic | context arithmetic: prompt + max_output_tokens must stay <= 32,768 | **PASS** |
| R01 | Reproducibility | twin archive is byte-identical | **PASS** |
| R02 | Reproducibility | two clean rebuilds give the same SHA-256 as the archive under test | **PASS** |
| O01 | Official compile | official validators and compile_submission | **BLOCKED** |
| F01 | Fake-model replay | scripted-model replay through the real harness | **BLOCKED** |
| I01 | Real Gemma inference | real Gemma 4 inference | **BLOCKED** |
| H01 | Hidden-task evaluation | hidden-task evaluation / leaderboard score | **BLOCKED** |

**BLOCKED details**

| ID | Limitation |
|---|---|
| O01 | not run: python 3.12.3; importable: adk_submission=no, swegemma=no, adk_eval_core=no, google.adk=no. The organizers' wheels are not installed here and the sandbox has no network. Next step: run official_harness_check.py in an environment with the competition wheelhouse installed. |
| F01 | not run: requires the official harness (swegemma, adk-submission, adk-eval-core) and a sandbox backend. |
| I01 | no GPU, no model weights, no inference server in this sandbox |
| H01 | only Kaggle's scorer can run the hidden tasks; nothing here predicts the score |

Mutation self-test: 23 of 23 injected defects (brace in prompt, extra or undeclared tools, `agent_tool`, skills key, `.sh` file, nested root, `..` include, missing include target, wrong model, flat or altered `eval_config.yaml`, thinking on or budget added, 16,384 output tokens, forbidden generation field, duplicate YAML key, shell literal, graph tool named, deleted behaviour, undeclared tool-like token, `agent_class` changed, absolute path, hidden file) were each caught by the intended check. Helper module self-test: 18 of 18 on synthetic fixtures. Notebook rehearsal on synthetic Kaggle fixtures: every cell behaved as intended, including fail-closed cases and a negative control that flags harness-default budgets (this rehearses cell logic only).

## 5. The two corrections in the task statement

Both are accepted and neither is treated as a defect.

- **`evaluation:` wrapper.** The harness guide copy documents the four limits under an `evaluation:` key (sections 2.2 and 7.1), and S0 follows it. Nothing I read contradicts it.
- **Omitted `agent_class`.** The same copy (section 2.3) says the agent config defaults to `LlmAgent` when `agent_class` is omitted. Check Y10 records this as a documented-default PASS; the official loader has not confirmed it.

## 6. Findings

**6.1 Confirmed from the documentation copy (none is a defect in S0 as specified)**

- The first user message appends a section describing the three graph tools whenever graph data exist for the repo (section 5.2, item 6). S0 declares none of them, so a model could still call an undeclared tool, which third-party reports say loses the patch. The prompt tells the model to ignore other tools without naming them.
- The documented CLI (`swegemma eval`, section 9.1) takes `--submission-dir` and explicit `--max-tool-calls` / `--max-time-minutes` flags, while eval_config loading is attributed to `scripts/inference.py` (sections 2.2 and 7.1), and section 7.1 lists environment-variable overrides for the same limits. **A CLI-only run would therefore not prove that S0's `eval_config.yaml` is applied.** Cells 8 and 14 test it directly.
- `submit_patch` guidance: section 10 advises making it the final action and section 5.3 ends the loop once a turn completes after a submission; S0's prompt says to submit early and resubmit after edits. Whether the agent can keep working after the first submission is unverified (risk R3).

**6.2 Risks and hypotheses (not established)**

| ID | Risk or hypothesis | How the run order tests it |
|---|---|---|
| R1 | Undeclared graph-tool call triggered by the task message | Cell 14 lists tool names found in the trace |
| R2 | `eval_config.yaml` not applied, or overridden by environment variables | Cell 8 prints the official loader source; Cell 14 asserts the Task Budget lines (5.0 minutes, 50 calls, 100 turns) in the first user message |
| R3 | Early `submit_patch` ends the run, making the first plausible patch final | Cell 14 reports tool calls after the first `submit_patch` |
| R4 | Version drift: other labs report different `adk-submission` releases (0.2.11 and 0.2.12), and the guide has more than one revision | Cell 5 records the installed versions |
| R5 | A 3,072-token output cap truncates a large edit and triggers a continuation nudge | Trace and log review after the smoke run |
| R6 | Thinking off causes repeated or malformed calls (third-party measurements) | Trace review after the smoke run |
| R7 | Causes of the two earlier Kaggle Errors | Unknown. No log or failed ZIP was supplied. Nothing here shows either error is fixed |

## 7. Versions and commands actually run

Environment: Python 3.12.3; PyYAML 6.0.3; `swegemma`, `adk_submission`, `adk_eval_core`, `google.adk`, `litellm`, `vllm`, `pydantic` all fail to import; no `swegemma`, `kaggle`, `nvidia-smi` or `docker` binary; no network (name resolution fails). A third-party lab reports `swegemma` 0.2.7, `adk-submission` 0.2.12, `adk-eval-core` 0.1.0, `google-adk` 1.36.1 and vLLM 0.19.1 on a Kaggle worker (not verified here).

```
ls -laR /mnt/user-data/uploads                       # one file: the Researcher 2 prompt text
find /mnt/attach /mnt/transcripts /mnt/user-data/tool_results -type f      # nothing
find / ( -iname "*gemma_reserach2_next*" -o -iname "*swegemma*" -o -iname "*adk_submission*" -o -iname "*adk-submission*"
         -o -iname "*adk_eval_core*" -o -iname "*wheelhouse*" -o -iname "HARNESS_README*" -o -iname "sample_submission*" -o -iname "*.ipynb" ) ...   # nothing
python3 --version ; pip list | grep -i -E "^(pyyaml|google-adk|adk-submission|swegemma|adk-eval-core|litellm|vllm|pydantic) "
python3 - (import probes for the packages above)
sha256sum submission.zip submission-GEMMA-S0-BASELINE.zip ; cmp submission.zip submission-GEMMA-S0-BASELINE.zip
python3 -m zipfile -t submission.zip
python3 validate_s0_v2.py submission.zip --twin submission-GEMMA-S0-BASELINE.zip --builder build_s0_zip.py \
        --inventory /mnt/user-data/uploads --json-out validation_v2.json --selftest
python3 official_harness_check.py submission.zip                            # BLOCKED, exit 3
python3 official_harness_check.py --check-budget-prompt <synthetic files>   # PASS / FAIL as designed
python3 preflight_tools.py selftest                                         # 18 of 18
python3 make_notebook.py ; python3 rehearse.py                              # synthetic-fixture rehearsal
```

No official validation command could be executed. Full logs are in the pack's `logs/` folder.

## 8. Still unverified

Official include loader and compiler on this ZIP; that the limits are actually loaded; fake-model wiring; tool-call encoding; patch extraction through the official path; real Gemma behaviour; anything about score. The notebook cells are untested against the real harness (only rehearsed on synthetic fixtures), and the starter-edit instructions in Cell 11 rest on a third-party description of the starter.

## 9. Next single action

Upload `GEMMA_S0_PREFLIGHT_PACK.zip` as a **new private Kaggle Dataset**, make a **new** notebook by *Copy & Edit* on the official starter (never the notebook that is running), and run Cells 1 to 10 of `GEMMA_S0_KAGGLE_RUN_ORDER.md` (no GPU needed). Those outputs decide between `SAFE TO TRY` and `NOT READY`; do not upload anything to the competition before then.
