# SUBMISSION_FORENSIC_REPORT.md

**Google – The Gemma 4 Developer Agent Competition · why two submissions show "Kaggle Error"**
Prepared 2026-10-17 for Venugopal · evidence gathered 2026-10-09 → 2026-10-17

**Evidence tags** — **[EXEC]** I ran it (log named) · **[CODE]** read in the organizers' harness source copy, `file:line` · **[DOC]** document text I read (official copy or secondary, stated) · **[3P]** public third-party record (repo + path) · **[CALC]** arithmetic from stated inputs · **[INF]** my inference, not evidence.
**Labels** — UNKNOWN · ASSUMPTION · VERIFY · BLOCKER · DRIFT DETECTED.

---

## 0. Inputs, assumptions, blockers

| # | Item | Status |
|---|---|---|
| B1 | **BLOCKER — screenshot and Kaggle error logs were not supplied.** Which two rows errored, their dates, refs, file names and `errorDescription` are **UNKNOWN**. Every statement below about "your two rows" is conditional. | open |
| A1 | **ASSUMPTION** — the attached `submission.zip` (4,849 B) is the prompt's "GEMMA-ADAPTIVE-EVIDENCE-V1" (agent `gemma_swe_adaptive_evidence_v1`; the prompt calls it the new candidate). | unverified |
| V1 | **VERIFY** — the attached VNEXT file is `submission-VNEXT.zip`, not `submission-VNEXT(1).zip`. If a "(1)" copy exists, compare its SHA-256 with `292c4ab2…62c00da` (full hash in Appendix A). | open |
| B2 | **BLOCKER — current scorer source not obtained.** What I executed is swegemma 0.2.7 + adk-submission 0.2.11 + adk-eval-core 0.1.0 + google-adk 1.36.1 (a third-party mirror of Kaggle dataset `metric/gemma-4-developer-agent-wheelhouse`; RECORD hashes: swegemma 41/41, adk-eval-core 51/51, adk-submission 23/24 — the one differing file is `adk_submission/resolvers/generation.py`, explained by the organizers' 2026-09-27 same-version re-release [3P S9 `docs/harness-fidelity.md` L62–73]) **[EXEC `logs/record_check.log`]**. Third parties report scorer wheels moved to adk-submission 0.2.12 on 09-30 **[3P S14 `docs/competition.md` L113–115]** and to adk-submission 0.2.13 with swegemma 0.2.10/0.2.11 (dataset version 29; release date UNKNOWN) **[3P S10 `docs/THINKING_OFF_T0.md` L6–14; S16 README L40–43]**; swegemma 0.2.11 also removed the `swegemma.models` discovery/registry helpers **[3P S10 L9–10]**. The outer `scripts/inference.py` that the README calls "Stage 1" is not public **[DOC S5 L72, L98; 3P S15 L32: absent from the 524-item public file list, direct download 404]**, so run-level handling of an invalid package is **UNKNOWN**. | open |
| B3 | **BLOCKER — Kaggle's own pages are JavaScript-rendered** (Overview, Rules, Data, error glossary); my fetch tools return metadata only. Official text is cited through third-party copies (S5 for Overview, Data and README; S4b for the error glossary); each is labelled where used. The two README copies I found **differ** (S5 49,356 B newer; S6 46,294 B older; Appendix D #1), so every README citation holds for S5 only, and I cannot show S5 is byte-identical to the live Data tab. | open |
| N1 | **Not done, and not claimed:** no Gemma/vLLM run, no sandbox/Docker task run, no run of the real scorer, no submission to Kaggle. A "compile" below means the organizers' *loader/schema/registry* accepted the directory. | — |

---

## A. Executive finding

1. **Proven package defect:** `submission-VNEXT.zip` does not compile — `sub_agents/code_analyzer.yaml` L9 and L17 use `!include prompts/analyzer.md` and `!include configs/analyzer_sampling.yaml`, which the loader resolves relative to `sub_agents/` (not the ZIP root), so both targets are "not found" (executed against the organizers' loader copy, swegemma 0.2.7 / adk-submission 0.2.11); the other three ZIPs pass the same compile and I found no packaging defect in them.
2. **No inference/runtime defect is proven** (I could not run Gemma, vLLM, the sandbox or the real scorer), but I proved two non-fatal weaknesses — GRAPH-FUSION-V2 and HYBRID-V2-ADAPTIVE tell the model to call `search_similar_code` with concept phrases, which the tool resolves only as symbol names and answers with `count: 0` — and one budget exposure: with ~120 sequential tasks, per-task caps of 8, 12 and 60 min cannot be shown to fit the 12-hour limit, and VNEXT's 4.5 min fits only if per-task setup stays ≤ ~1.5 min (unmeasured).
3. **"Kaggle Error" is Kaggle's label for a "rare system error … try resubmitting"**, a different bucket from "Notebook Threw Exception", "Exceeded Allowed Compute" and "Notebook Timeout", and the only public instances I found (10-07 and 10-08, `errorDescription` "A system error. Please try resubmitting…") were later rescored with no package change — so a package defect is not shown to be the cause of your two rows.
4. **Gate verdict:** one package defect proven (VNEXT: fatal to any valid score, but not shown to produce "Kaggle Error"), no inference/runtime defect proven, and the precise cause of the two "Kaggle Error" rows **cannot be diagnosed** without their `errorDescription`, dates/refs and Kaggle's server logs.
5. **Recommendation:** do not resubmit VNEXT as attached; refresh the two error rows first (they may already be rescored), and if you submit today use `submission-VNEXT-INCLUDEFIX-ADDITIVE.zip` (adds two files, edits nothing, SHA-256 `c26518e6…1126`, rename to `submission.zip`), ideally after the zero-cost pre-flight in G4.

---

## B. The four ZIPs

### B1. Side by side

| | **VNEXT** | **GRAPH-FUSION-V2** | **submission.zip** (EVIDENCE-V1, A1) | **HYBRID-V2-ADAPTIVE** |
|---|---|---|---|---|
| File · bytes | `submission-VNEXT.zip` · 5,938 | `submission-GRAPH-FUSION-V2.zip` · 5,865 | `submission.zip` · 4,849 | `submission-GEMMA-HYBRID-V2-ADAPTIVE.zip` · 5,075 |
| Root config | one `agent.yaml` at ZIP root (413 B); agent `swe_coder` + `agent_tool: {config_path: sub_agents/code_analyzer.yaml, skip_summarization: true}` | one `agent.yaml` (578 B); `gemma_swe_graph_fusion_v2`, `agent_class: LlmAgent` | one `agent.yaml` (543 B); `gemma_swe_adaptive_evidence_v1`, `LlmAgent` | one `agent.yaml` (657 B); `gemma_swe_repair_v2_1_adaptive`, `LlmAgent` |
| Archive hygiene | 7 files, only `.yaml`/`.md`; no symlinks, traversal, encryption, duplicates; `testzip()` clean | 4 files, same | 4 files, same | 4 files, same |
| Model consistency | `gemma-4-31b-it-qat-w4a16-ct` in `agent.yaml` L2 **and** `sub_agents/code_analyzer.yaml` L2 — one declared model | same string, 1 declaration | same, 1 | same, 1 |
| `!include` / `config_path` | **5 refs, 2 BROKEN** (`sub_agents/code_analyzer.yaml` L9, L17) | 2 refs, 0 broken | 2 refs, 0 broken | 2 refs, 0 broken |
| Tools | root: the 9 registry tools + `code_analyzer`; analyzer: `run_command`, `read_file`, `get_code_neighbors`, `search_similar_code` | the 9 registry tools | the 9 | the 9 |
| Eval limits (`timeout_seconds` / `max_tool_calls` / `max_time_minutes` / `max_turns`) | 120 / 40 / 4.5 / 100 | 300 / 100 / 60 / 500 | 300 / 60 / 8 / 120 | 300 / 100 / 12 / 500 |
| Generation | temp 0.2, `max_output_tokens` 6144, `include_thoughts: false`; analyzer temp 0.1, 2048, `include_thoughts: false` | temp 0.2, top_p 0.95, top_k 40, `max_output_tokens` 8192, `thinking_budget` 4096, `include_thoughts: true` | same as GRAPH-FUSION | same as GRAPH-FUSION |
| Official-loader compile (0.2.11) | **FAIL** — `SubmissionValidationError: !include file not found: …/sub_agents/prompts/analyzer.md` | PASS | PASS | PASS |
| **Definite defect** | **D1 — fatal package defect** (broken includes) | none found | none found | none found |
| Proven, non-fatal | — | P1 `search_similar_code` concept-phrase instruction | — | P2 behaviour-words query for `search_similar_code` |
| Worst-case run time, N=120 [CALC, App. B] | 10.0 – 11.6 h | 121 – 123 h | 17.0 – 18.6 h | 25.0 – 26.6 h |

Tool names in every `tools:` list are inside the closed 9-tool registry (`run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`, `search_similar_code`, `get_code_neighbors`, `get_code_subgraph`) **[EXEC]**, and no prompt instructs the model to call a tool that is not declared for that agent **[EXEC `logs/prompt_tool_check.log`]**. All four `eval_config.yaml` files parse the way the organizers' notebook parses them (top-level `evaluation:`, no unknown keys; ints and floats) **[EXEC `logs/compile_*.json` step `parse_eval_config`]**; a float `max_time_minutes` such as `4.5` is accepted by the real scorer **[3P S8 `experiments/kaggle_submissions.md`: 4.5-minute rows 2026-09-28 → 10-07 scored]**.

### B2. Findings per ZIP

**VNEXT**
- **D1 (definite, executed).** Mechanism: `!include` is resolved against the directory of the file that contains the tag, then sandboxed to the root **[CODE `adk_submission/yaml_loader.py` L47–78, L170–171, L199–206; `adk_submission/paths.py` L156]**. `sub_agents/code_analyzer.yaml` L9 `!include prompts/analyzer.md` → `sub_agents/prompts/analyzer.md` (absent); L17 `!include configs/analyzer_sampling.yaml` → `sub_agents/configs/analyzer_sampling.yaml` (absent). The files exist only at the root (`prompts/analyzer.md`, `configs/analyzer_sampling.yaml`). The organizers' sample writes `!include ../prompts/analyzer.md` and `!include ../configs/sampling.yaml` in the same position **[3P S13 `submission/sub_agents/code_analyzer.yaml` L6–7]**. `validate_directory`, `validate_single_declared_model` and `discover_adapters` all PASS on the broken ZIP — **only the full `compile_submission` catches it** **[EXEC `logs/compile_vnext.json`, `logs/include_table.log`]**.
- **DRIFT DETECTED (docs vs code).** README says "`..` traversal components … strictly blocked" and gives no base for `<relative_path>` **[DOC S5 L99–102]**, while its own layout puts `prompts/analyzer.md` beside `sub_agents/code_analyzer.yaml` and the sample uses `../`. In the 0.2.11 code `..` is allowed in `!include` when the target stays inside the root (`ensure_no_traversal_components` is applied only to `config_path`, `context.py` L106) **[CODE; EXEC: `../` variant compiles]**. This ambiguity is the most plausible way the defect got written; it is also why the recommended fix in E uses no `..`.
- **Risks.** (1) `timeout_seconds: 120` is also the pytest verification timeout **[CODE `swegemma/harness/verification.py` L498–503]**; third parties keep it ≥180 **[3P S9 `docs/harness-fidelity.md` L54]**. (2) Thinking state is wheel-dependent: `include_thoughts: false` is checked first and turns thinking off in 0.2.11 **[CODE `adk_submission/resolvers/generation.py` L94–99]**, but on adk-submission 0.2.13 + swegemma 0.2.10 `include_thoughts: false` with no `thinking_budget` is reported to leave thinking ON because the injected default budget 4096 overrides it **[3P S10 `docs/THINKING_OFF_T0.md` L11–16; VERIFY]** — the 2048-token analyzer cap would then truncate. (3) `skip_summarization: true` ends the root invocation when the analyzer returns, so the harness nudge loop spends one "Please continue…" nudge per task **[EXEC `logs/smoke_vnext_additive.json`; CODE `agent_runner.py` L712–715]** — harmless. (4) Never run on the real scorer.
- **Validations.** Archive audit; include table (two rules); brace-template scan (`{problem_description?}` only, substituted); official-loader compile (FAIL as above); both patched variants compile PASS; scripted-fake-LLM ADK run of the patched variants RAN_TO_COMPLETION (root → `code_analyzer` → root, issue text reached the analyzer prompt, no raw braces left) **[EXEC]**.

**GRAPH-FUSION-V2**
- **No packaging defect found** (compile PASS, includes 2/2, one model).
- **P1 (proven, non-fatal).** `prompts/system.md` L31 tells the model: `search_similar_code: … A 3-8 word concept phrase such as "dependency override resolution", never issue prose` (and L18 "behavior only -> one semantic query"). The tool's contract is "Function name or code snippet" **[CODE `swegemma/tools/graph.py` L94]**; the implementation resolves the query as a node name (exact → `.`/`;` suffix → case-insensitive → substring, `graph_utils.py` L149–204), then `embed()` is only a lookup in the precomputed NPZ (`embedding_utils.py` L132–216, no text-embedding model), and if neither resolves it returns `[]` (`retrieval_utils.py` L377–386) → `{"status":"ok","count":0}`; the call is still charged (`@budget_gated`, `tools/base.py` L59–62). A multi-word phrase will almost never match a node name, so the prescribed use returns nothing and burns a tool call and a turn.
- **Risks.** All four `eval_config.yaml` values (300 / 100 / 60 / 500) equal the scorer defaults documented in README §7.1 **[DOC S5 README L538–545; CODE `swegemma/budget.py` L18: `time_minutes: float | None = 60.0`]**, i.e. the file adds no cap beyond "no config"; with ~120 sequential tasks the worst case is ≥121 h [CALC]. Staff reportedly recommend "a moderate `max_time_minutes` as a lifeline" **[3P S11 playbook §10.3 L498–500]**. `max_turns: 500`. Thinking on; the numeric `thinking_budget` is not forwarded in the 0.2.11 copy **[CODE generation.py L61–126; 3P S9 L52]** but is reported fixed in later wheelhouses **[3P S11 §10.2 L482]** → DRIFT, behaviour depends on the scorer wheel.

**submission.zip (EVIDENCE-V1, A1)**
- **No packaging defect found.** Prompt L28–30 (`search_similar_code` query "a known function/class/module symbol or a short code identifier, not … natural-language", stop after empty/error; `get_code_neighbors` with "the actual dotted symbol"; `get_code_subgraph` with "2-5 exact symbols") matches the tool semantics **[CODE]**.
- **Risk.** 8-minute cap → worst case 17.0–18.6 h [CALC]; thinking on. At ≈21 s per call (organizers' sample run) the cap binds after ≈23 calls, below the prompt's own "NORMAL 18–35 / HARD 35–50" call guidance (`prompts/system.md` L49) **[3P S8b `notes.md` L100–101; CALC; INF]**.

**HYBRID-V2-ADAPTIVE**
- **No packaging defect found.**
- **P2 (proven, non-fatal).** `prompts/system.md` L22: "Query = behavior words or a short code fragment" — half of that is outside the contract (see P1); the prompt has a count-0 no-retry fallback, which limits the waste. L25 `edge_type such as CALLS, DEFINED_IN, IMPORTS` matches the tool's own docstring **[CODE graph.py L26]**; `get_code_neighbors` filters by exact equality on the edge's `type`/`relation` (`graph_utils.py` L346–360), so a wrong string silently returns `[]`. Whether the hidden graph data uses exactly these strings is **UNVERIFIED** (no graph data available); the Data page says "such as calls" **[DOC S5/S6]** → DRIFT.
- **Risk.** 12-minute cap → worst case 25.0–26.6 h [CALC]; thinking on.

---

## C. Root-cause ranking

**Scope.** Candidate explanations for "your two Kaggle Error rows". B1 applies: the rows are unidentified, so each confidence rates the *hypothesis*, not a specific row.

**Stage key** (organizers' README): **K** = Kaggle platform (intake, scheduling, GPU/notebook provisioning, result publishing). **S1** = Stage 1: `scripts/inference.py` runs the package over the tasks and writes `/kaggle/working/submission.parquet` (`[id, prediction]`) **[DOC S5 README L72, L578; Data.md L61]**. **S2** = Stage 2: `score()` in `scripts/metric.py` runs `verify_task` in a fresh container and returns the resolution rate **[DOC S5 README L581–611]**.

### C0. Outcome taxonomy — what each result most likely represents

| Outcome as shown | Documented meaning | Stage it most likely marks | Evidence and caveats | Could it be your rows? |
|---|---|---|---|---|
| **Kaggle Error** | "A rare system error. Please try resubmitting to resolve the error and contact Kaggle Support if it persists." **[DOC S4b]**. API text seen in this competition: "A system error. Please try resubmitting…" **[3P S8 L29–30]** | **K** — platform or scoring-service fault outside the package | The only public instances (10-07, 10-08, two in a row) were later rescored with no package change; leaderboard best-score dates 638 / 74 / 4 on 10-06 / 10-07 / 10-08 **[3P S8 L29–30]**. Whether any package defect can produce this label is **UNKNOWN** (B2). | **Yes — this is the label you report.** |
| **Notebook Threw Exception** | "While rerunning your code, your notebook hit an unhandled error." **[DOC S4b]**. API text: "Your notebook hit an unhandled error while rerunning your code. Note that the hidden dataset can be larger/smaller/different than the public dataset." **[3P S8 L7–8]** | **S1, run level** — an exception escaped the inference run, or the platform killed it | A non-compiling package (disallowed `.sh`, unknown tools) ended here, no traceback **[3P S7 L21–29]**; the admin-confirmed GPU outage of 09-30 → 10-01 produced many such rows **[3P S14 L116–117; S11 L491]**; day 8 of one team, cause unknown **[3P S8 L7–10]**. | No (different label). Where a run-level package failure has most likely landed, n = 1. |
| **Notebook Exceeded Allowed Compute** ("requested more CPU, GPU or TPU resources than are available") | "violated a code requirement constraint during the rerun" **[DOC S4b]** | **K / S1** — resource or capacity at launch or rerun, not package validity | A tiny valid package got it on 09-24 **[3P S15 `submission_status_evidence.json`]**; a 5.5-min config on 09-26 got it, first read as a 12-h overrun and later retracted by the same author **[3P S8 L4–6]**. | No (different label). |
| **Notebook Timeout** | "Your submission notebook exceeded the allowed runtime." **[DOC S4b]**. Limit here: 12 h for all tasks, inclusive of sandbox setup, excluding patch validation **[DOC S5 Overview L55]** | **S1, wall clock** | The label an overrun shows *in this competition* is **UNDOCUMENTED**, and I found no confirmed public overrun. Relayed staff: exceeding 12 h "today throws an error", planned to become "unfinished tasks = 0" **[3P S11 L498–500]**. The one run a third party first read as an overrun (day 8, 4.5 min) showed "unhandled error", and the same author later withdrew that reading ("not the 12 h cap") **[3P S8 L7–10, L24, L28]**. **[INF]** if an overrun produces an error label, it is an exception bucket, not K. | No (different label), unless the mapping differs; check elapsed time (G6). |
| **Missing or invalid output** | Generic code-competition labels: "Submission CSV Not Found", "Submission Scoring Error" ("incorrect format") **[DOC S4b]**. Here the output is `submission.parquet` **[DOC S5 Data.md L61]** | **end of S1 / intake of S2** | Which label appears when `inference.py` writes no or a malformed parquet is **UNKNOWN** (script unpublished). A ZIP without a root `agent.yaml` fails `validate_directory` with "No root YAML config found…" **[CODE `adk_submission/discovery.py` L240–244]**; all four ZIPs have one **[EXEC]**. | No evidence for it. |
| **Numeric score** (0.06, 0.00, …) | Completed run; score = share of tasks whose patch passes validation **[DOC S5 Overview L53]** | **S1 + S2 completed** | **0.00 does not prove a valid package**: a per-task compile or runtime exception is swallowed (`agent_error`, `resolved=False`) and the run continues **[CODE `agent_runner.py` L217, L334, L797–801; `swegemma/evaluate.py` L495–543]**. The 09-24 day-1 0.00 was a valid package whose sample prompt "does not submit patches" **[3P S8 L17]**. | Your earlier 0.06 / 0.00 rows. |
| **Patch-validation failure** (per task) | Patch does not apply after four passes → `resolved=False`; tests fail, are skipped or time out → not resolved **[DOC S5 README L583–589, L606–611]**. Pytest timeout = the submission's `timeout_seconds` **[CODE `swegemma/harness/verification.py` L498–503]**. Excluded from the 12-h clock **[DOC Overview L55]** | **S2, per task** | Lowers the score only; it does not raise a run-level error label. | **Cannot** explain "Kaggle Error". |

Per-task outcomes that never become a run-level label: no `submit_patch` → the harness falls back to the working-tree diff **[CODE `agent_runner.py` L760–795; DOC S5 README L569–578]**; time, tool-call and turn budgets end the task **[CODE `agent_runner.py` L581–672]**; context overflow reportedly loses the patch **[3P S14 L121–124; UNVERIFIED by me]**.

### C1. Ranked hypotheses for the two "Kaggle Error" rows

| # | Hypothesis | Supporting evidence | Contradicting evidence | Confidence | Exact next check |
|---|---|---|---|---|---|
| **R1** | **Kaggle-side system or scoring fault; the package is not the cause.** | (a) The label is the platform's "rare system error … try resubmitting" bucket, not a rerun-exception bucket **[DOC S4b]**. (b) Same-text rows on 10-07 and 10-08 were rescored by 10-09 with no package change; best-score dates 638 / 74 / 4 **[3P S8 L29–30]**. (c) A confirmed GPU outage on 09-30 → 10-01 shows outages occur here **[3P S14 L116–117; S11 L491, thread 744807]**. (d) Three of the four ZIPs compile **[EXEC]**, so a cause shared by two different ZIPs cannot be VNEXT's include defect unless both rows are VNEXT. (e) Weak **[INF]**: entry mtimes inside VNEXT and HYBRID are 2026-10-07, inside that window; GRAPH-FUSION and `submission.zip` are 10-09 — proves nothing about upload dates. | (a) Row dates, refs and `errorDescription` not supplied (B1): the window match is unestablished. (b) No staff statement for the window found; the 10-07/10-08 attribution to Kaggle is the submitter's inference from the rescore **[3P S8 L29–30]**. (c) Glossary is a secondary copy; official page not rendered (B3). (d) A package defect cannot be excluded as a producer of this label: outer script unpublished (B2). | **MEDIUM** — rises to **HIGH** if G1 shows `errorDescription` beginning "A system error. Please try resubmitting" **and** G2 shows a rescore or an in-window date. | **G1** (read `errorDescription` through the API), then **G2** (refresh; compare dates with 10-07/10-08). |
| **R2** | **VNEXT's broken includes (D1) raised a run-level failure that Kaggle labelled "Kaggle Error"** — applies only if a row is VNEXT. | D1 is proven: `compile_submission` raises `SubmissionValidationError: !include file not found` **[EXEC `logs/compile_vnext.json`]**. A non-compiling package ended in a run-level exception once **[3P S7 L21–29]**. | In the harness copy `compile_submission` runs per task inside a `try` whose `except Exception` only records `agent_error`; the worker then records `resolved=False` and continues **[CODE `agent_runner.py` L217, L334, L797–801; `evaluate.py` L495–543]** → expected outcome is a numeric 0.00, not an error label. The one run-level analog failed other checks (`.sh` files, unknown tools — `validate_directory`/registry) and was labelled "Notebook Threw Exception", not "Kaggle Error" **[3P S7 L25–26]**. `validate_directory`, `validate_single_declared_model`, `discover_adapters` all pass VNEXT **[EXEC]**, so no run-level pre-check **[DOC S5 README L183]** rejects it. Scorer wheels are newer than my copy (B2). | **LOW** as the cause of *this label*. (D1 itself is **HIGH**: fatal to any valid score — see C2.) | **G1** on the VNEXT row: "unhandled error" ⇒ consistent with D1; "A system error" ⇒ not D1. Then **G4** on the scorer's wheels. |
| **R3** | **12-hour overrun**: per-task caps too large for ~120 sequential tasks. | Worst case N×(cap+setup): 10.0–11.6 h (VNEXT), 17.0–18.6 h (EVIDENCE-V1), 25.0–26.6 h (HYBRID), 121–123 h (GRAPH-FUSION) **[CALC, App. B]**. Relayed staff: exceeding 12 h "throws an error" **[3P S11 L498–500]**. Agent time use is prompt-dependent: the organizers' sample prompt used the full 5-minute budget on both sample tasks (305.8 s and 309.6 s, 14–15 tool calls, ≈21 s per call) **[3P S8b notes.md L100–101; CALC]**, so at that rate an 8-min cap binds after ≈23 calls, below EVIDENCE-V1's own "NORMAL 18–35 / HARD 35–50" call guidance (`prompts/system.md` L49) **[INF]**. GRAPH-FUSION's `eval_config.yaml` equals the scorer defaults 300 / 100 / 60 / 500 **[DOC S5 README L538–545]** — it adds no cap. | An overrun's label is undocumented. The one "unhandled error" a third party first read as an overrun (day 8, 4.5 min) was later withdrawn by the same author ("not the 12 h cap") **[3P S8 L24 vs L28]**. Third-party runs with 3.5 / 4.5 / 5.0-min caps were scored in ≈6–7.7 h from submission **[3P S8 L12–13, L20–22, L24–28]**; 4.5-min configs scored in 5 of 6 runs (day 8 failed, cause unknown; day 13 first showed "A system error", then scored) **[3P S8 L21, L23, L24, L26, L27, L29]**. No measurement exists for 8 / 12 / 60-min configs with these prompts; all three prompts call the limits ceilings, not targets **[EXEC grep: EVIDENCE L49, HYBRID L2, GRAPH-FUSION L48]**. Elapsed time of your rows unknown (B1). | **LOW** as the cause of the two rows; **MEDIUM** as a live risk for GRAPH-FUSION, HYBRID and EVIDENCE-V1. | **G6**: per row, completion time minus `date` versus 12 h; **G1**. |
| **R4** | **Scorer-side wheel drift**: the scorer's wheels (adk-submission 0.2.12 / 0.2.13, swegemma 0.2.10 / 0.2.11) reject or mishandle something my 0.2.7 / 0.2.11 copy accepts. | Wheels did change: 0.2.12 on 09-30 **[3P S14 L113–115]**; 0.2.13 with swegemma 0.2.10 (dataset v29) **[3P S16 README L40–43]**; swegemma 0.2.11 removed the `swegemma.models` helpers **[3P S10 L9–10]**; a same-version re-release on 09-27 changed `generation.py` **[3P S9 L62–68]**; Kaggle mounts the latest wheelhouse regardless of the `/N` pin **[3P S10 L6–8]**. Reported behaviour drift: `thinking_budget` now forwarded **[3P S11 L482]**; `include_thoughts: false` no longer disables thinking on 0.2.13 without a budget **[3P S10 L11–14]**. | Third-party packages of the same structure compile on 0.2.12 and 0.2.13 **[3P S14 L114–115; S10]**. None of the four ZIPs uses `thinking_budget: 0`, `thinking_level` or another key reported to break; `thinking_budget: 4096` is inside 0–32768 **[CODE `swegemma/config.py` L61–62]**. A compile-time rejection would surface per task or as an exception, not obviously as "Kaggle Error" **[CODE; INF]**. | **LOW** | **G4**: run `preflight_compile.py` on the scorer's installed wheels; record `versions` and `VERDICT_compile_submission`. |
| **R5** | **Instruction/tool-semantics mismatches (P1, P2) and thinking/context settings.** | P1 and P2 are proven **[CODE `swegemma/tools/graph.py` L94; `graph_utils.py` L149–204; `retrieval_utils.py` L377–386]**. Reported effective window ≈7–14k tokens **[3P S11 L472–473]**; context overflow reportedly loses the patch **[3P S14 L121–124; UNVERIFIED by me]**. | Per-task errors are caught and scored as that task failing **[CODE `evaluate.py` L495–543; `agent_runner.py` L797–801]**: they can lower a score but cannot produce a run-level label. The earlier 0.06 / 0.00 rows show the harness completing runs. | **HIGH** that P1/P2 exist and waste calls; **LOW** that they explain either row. | None for the rows. Out of scope to tune prompts (task rule). |
| **R6** | **Upload mismatch**: wrong file name, wrong bytes or wrong layout. | Contract is a file named `submission.zip` with `agent.yaml` at the root **[DOC S5 Overview L26]**; the four attached files carry other names, so a rename happened before upload; A1 and V1 are unverified. | All four ZIPs have exactly one root `agent.yaml`, only `.yaml`/`.md`, no traversal or symlinks, `testzip()` clean **[EXEC `logs/zipaudit_fresh.log`]**; earlier uploads through the same path scored. | **LOW** | **G3** (match `fileName` / `totalBytes` / SHA-256), **G7**. |

**What moves the ranking.** R1 → HIGH: G1 shows "A system error. Please try resubmitting…" and G2 shows a rescore or an in-window date. R1 → LOW and R2 → MEDIUM/HIGH: a VNEXT row's `errorDescription` reads "unhandled error", or identical bytes fail again on a quiet day. R3 → MEDIUM: a row's completion time is within ~1 h of 12 h or beyond it.

D1 is ranked LOW in R2 **only as an explanation of the "Kaggle Error" label**. It stays a proven fatal package defect for VNEXT whatever label it produced.

### C2. Fatal defect vs. performance weakness vs. infrastructure, per candidate

| | **VNEXT** | **GRAPH-FUSION-V2** | **submission.zip** (EVIDENCE-V1, A1) | **HYBRID-V2-ADAPTIVE** |
|---|---|---|---|---|
| **Fatal configuration defect** | **D1** — two broken `!include`s. **HIGH** **[EXEC]** | none found (compile PASS; never run on the scorer) | none found | none found |
| **Performance weakness / exposure (non-fatal)** | `timeout_seconds: 120` doubles as the pytest verification timeout — **MEDIUM** **[CODE]**; thinking state wheel-dependent — **LOW** **[3P S10]** | **P1** concept-phrase `search_similar_code` → `count: 0` — **HIGH** that it exists, impact unknown; caps equal scorer defaults — **HIGH** | 8-min cap exposure — **MEDIUM** | **P2** behaviour-words query, limited by its no-retry fallback — **HIGH** that it exists, impact low |
| **12-h worst case, N = 120 [CALC]** | 10.0–11.6 h (fits only if per-task setup ≤ ~1.5 min) | 121–123 h | 17.0–18.6 h | 25.0–26.6 h |
| **Infrastructure-side** | Shared by all four and not a property of any package: a submission shown as "A system error" was later rescored to 0.10 without a re-upload **[3P S8 L29]**. Cause for your rows **UNKNOWN** without G1/G2. | | | |

---

## D. What the screenshot does and does not prove

**Status.** No screenshot and no Kaggle log were attached (B1). I did not see, describe or infer their content. The table states what a Submissions-page screenshot can establish, what it cannot, and how each gap closes. I did **not** assume the two error rows are VNEXT and HYBRID-V2-ADAPTIVE, and I did **not** assume they fall on 10-07 / 10-08.

| A Submissions-page screenshot can show | It cannot show | Closes with |
|---|---|---|
| The label per row ("Kaggle Error") and the earlier scores (0.06, 0.00) | **Cause or stage.** "Kaggle Error" is the platform's system-error bucket; Notebook Threw Exception, Exceeded Allowed Compute and Timeout are different buckets (C0). | G1 |
| Row order and upload dates | **Whether the dates fall in an outage window.** Public precedent: system-error rows of 10-07 / 10-08 were rescored by 10-09 **[3P S8 L29–30]**. | G2 |
| File names and descriptions | **Which bytes were scored.** A file name is not a hash, and the required name `submission.zip` **[DOC S5 Overview L26]** is shared by every build. | G3 |
| That a run ended in error | **Whether the package caused it.** An outage and a broken package can look alike; a failed scoring run alone does not make the archive the cause (the prompt's own rule). | G1, G4 |
| That earlier rows scored 0.06 and 0.00 | **That those packages were valid, or like the current ones.** A 0.00 is also what a package whose per-task compile fails would plausibly produce **[CODE; INF]**; the 09-24 sample-prompt 0.00 came from a valid package that submitted nothing **[3P S8 L17]**; the scorer's wheels changed after 09-27 (B2). | G4, compare wheel `versions` |
| The rows as of the screenshot | **Finality.** A row can change from error to scored without a re-upload (precedent above). | G2 (refresh) |
| — | **Slot consumption.** A third-party digest says a failed run still uses that day's submission **[3P S14 L116–117]**; the Rules page was not readable (B3). **VERIFY.** | G5 |
| — | **Elapsed time and 12-h behaviour.** | G6 |
| — | **Whether the two errors share a cause.** | G1 on both rows |
| — | **Anything about agent quality.** An error row is not a score. | — |

---

## E. Recommended ZIP

### E1. Recommendation and decision rule

**Use today: `submission-VNEXT-INCLUDEFIX-ADDITIVE.zip`** — your VNEXT plus two added files; nothing edited, nothing removed. Upload it under the name **`submission.zip`** (the contract name, **[DOC S5 Overview L26]**); the rename changes neither bytes nor hash.

Decision rule (each step removes candidates):

1. **Must compile under the organizers' loader.** VNEXT as attached fails (D1) and needs a patch; GRAPH-FUSION-V2, `submission.zip` (EVIDENCE-V1) and HYBRID-V2-ADAPTIVE compile as attached, so none of them was touched **[EXEC]**.
2. **Among compile-clean builds, prefer per-task caps that can fit 12 h for ~120 sequential tasks.** Only VNEXT's 4.5 min does (fits only if per-task setup ≤ ~1.5 min); EVIDENCE-V1 17.0–18.6 h, HYBRID 25.0–26.6 h, GRAPH-FUSION 121–123 h worst case **[CALC, App. B]**. VNEXT is the tightest, **not proven safe**: setup is unmeasured (App. B), and one of six third-party runs at a 4.5-min cap (different prompt) ended in an unexplained "unhandled error" **[3P S8 L24]**.
3. **Smallest change that makes VNEXT valid under both readings of `!include`** (relative to the including file, and relative to the root) **without `..`**: the additive form (E4).
4. **Instructions consistent with tool semantics.** VNEXT's root prompt forbids `get_code_subgraph` and allows graph tools only with exact symbols (`prompts/system.md` L18); its analyzer prompt says "SYMBOL NAMES … never sentences" (`prompts/analyzer.md` L9) — this matches the tool contract **[CODE `swegemma/tools/graph.py` L94; EXEC `logs/final_6_prompt_tool_check_additive.log`: 0 mentioned-but-undeclared tools]**.

**Limits of this recommendation.** It is the best-supported choice on *harness validity*, not a proven scorer. It has never run on the real scorer (B2), and it cannot remove Kaggle-side failure (R1). Which candidate to submit for *score* is outside this task (leaderboard strategy was excluded).

### E2. Identity

| Property | Value |
|---|---|
| File | `submission-VNEXT-INCLUDEFIX-ADDITIVE.zip` (upload as `submission.zip`) |
| Bytes | **7,700** |
| SHA-256 | **`c26518e6a6b91eff4136238a121a93bb045e593e7586b314795b6945efac1126`** |
| Archive | 9 files, deflate, no directory entries, no comment; `testzip()` → `None` **[EXEC `logs/final_1_zipaudit.log`]** |
| Built from | your `submission-VNEXT.zip` — 5,938 B — `292c4ab28c9c516f26f92b71e9352f0e5d87dbfef95b0120845b77f6f62c00da` (V1 applies) |
| Check on your machine (PowerShell; syntax **not executed here**, no PowerShell in this environment) | `Copy-Item .\submission-VNEXT-INCLUDEFIX-ADDITIVE.zip .\submission.zip -Force; (Get-FileHash .\submission.zip -Algorithm SHA256).Hash; (Get-Item .\submission.zip).Length` → expect `C26518E6A6B91EFF4136238A121A93BB045E593E7586B314795B6945EFAC1126` and `7700` |

### E3. Exact file tree

```
submission.zip                                   7,700 B · 9 entries
├── agent.yaml                                      413 B   unchanged
├── eval_config.yaml                                 97 B   unchanged
├── configs/
│   ├── analyzer_sampling.yaml                      106 B   unchanged
│   └── sampling.yaml                               106 B   unchanged
├── prompts/
│   ├── system.md                                 5,825 B   unchanged
│   └── analyzer.md                               2,583 B   unchanged
└── sub_agents/
    ├── code_analyzer.yaml                          563 B   unchanged
    ├── configs/
    │   └── analyzer_sampling.yaml                  106 B   NEW (byte copy of configs/analyzer_sampling.yaml)
    └── prompts/
        └── analyzer.md                           2,583 B   NEW (byte copy of prompts/analyzer.md)
```

| Entry | Bytes | CRC-32 | SHA-256 | vs your VNEXT |
|---|---:|---|---|---|
| `agent.yaml` | 413 | 1b04b25a | `f40c541aeb992d937638308fe69f45173409bb1fe64576846d8a689b578efc73` | identical |
| `eval_config.yaml` | 97 | c8ced586 | `ec4972745cc6d63568600d16c55895c8db7d9f73254364047648390b69869eaa` | identical |
| `configs/analyzer_sampling.yaml` | 106 | 86c2cbfa | `f30184c2651ecac7669a2160a22b4d18578da32d5a722655c7c2411a7fbbb1aa` | identical |
| `configs/sampling.yaml` | 106 | 7dcb3354 | `76247648c7e37a4be7aed283f1e7222ccc44c33a75b9187d68f9076b8d4e07b4` | identical |
| `prompts/system.md` | 5,825 | 1f74a14f | `d98c9db5b64fe7e993a8260413c95e4d0a19a3a5aa9b631146a134edd416ac49` | identical |
| `prompts/analyzer.md` | 2,583 | 61385c15 | `c5efb4907619768be6f35e86f3dd039a7bc1238fbdd5a112c2b7ca2a19365073` | identical |
| `sub_agents/code_analyzer.yaml` | 563 | 979a0f99 | `8b5c6889f6b5b56a76498145720a64a548381c9f23035cf1af6f5b5c7e4ac937` | identical |
| `sub_agents/configs/analyzer_sampling.yaml` | 106 | 86c2cbfa | `f30184c2651ecac7669a2160a22b4d18578da32d5a722655c7c2411a7fbbb1aa` | **NEW** — same bytes as `configs/analyzer_sampling.yaml` |
| `sub_agents/prompts/analyzer.md` | 2,583 | 61385c15 | `c5efb4907619768be6f35e86f3dd039a7bc1238fbdd5a112c2b7ca2a19365073` | **NEW** — same bytes as `prompts/analyzer.md` |

Source: `logs/final_2_entry_hashes.log` **[EXEC]**. The two new entries carry the timestamp 2026-10-16 00:00:00; the seven originals keep their original timestamps and their original order.

### E4. What changed versus your VNEXT, and why this form

**Delta: +2 entries, 0 changed, 0 removed.** `sub_agents/code_analyzer.yaml` is byte-identical, so L9 `instruction: !include prompts/analyzer.md` and L17 `generate_content_config: !include configs/analyzer_sampling.yaml` stand as written.

**Mechanism.** `!include` resolves "relative to the directory of the file containing the tag" **[DOC S5 Overview L99; CODE `adk_submission/yaml_loader.py` L47–78, L170–171, L199–206]**. For a tag inside `sub_agents/code_analyzer.yaml` the targets are `sub_agents/prompts/analyzer.md` and `sub_agents/configs/analyzer_sampling.yaml`; the additive build puts them there. The README names no base for `<relative_path>` **[DOC S5 README L99]**, so the same two lines would also resolve against the root; the root copies are kept for that reading. Result: 5 references, 0 missing under either rule, 0 uses of `..` (original: 2 missing under the implemented rule) **[EXEC `logs/final_3_include_table_additive.log`, `logs/final_3b_include_table_orig.log`]**.

**Cost of this form.** Two duplicated files; the two root copies are referenced only under the root-relative reading. Any later edit to `prompts/analyzer.md` must be made in both places or the two will diverge silently.

**Alternate, not delivered — Variant A (two-line edit).** `sub_agents/code_analyzer.yaml` L9 → `!include ../prompts/analyzer.md`, L17 → `!include ../configs/analyzer_sampling.yaml`. ZIP 5,941 B, SHA-256 `f043d43d5cc80a665f9fc4d1bbb921e35039897d91e0cead8ea223ecdd962b20`; the entry changes CRC 979a0f99 → 348e6cdc, 563 → 569 B, SHA-256 `8b5c6889…` → `790dfe8f6353cbf082b9b986dfc1e9123addc7dc6cdce492109f1063f5dc9b53`; other six entries identical **[EXEC `logs/final_7_variantA_diff.log`]**. It compiled and ran the scripted ADK test on the 0.2.11 copy **[EXEC `logs/compile_vnext_includefix.json`, `logs/smoke_vnext_includefix.json`]**, but it resolves only under the relative-to-file rule and uses `..`. **DRIFT DETECTED:** README says `..` components are "strictly blocked (`PathTraversalError`)" **[DOC S5 README L102]** and Overview says traversal "via ../ or symlinks" is not allowed **[DOC S5 Overview L100]**, yet the organizers' own sample uses `!include ../prompts/analyzer.md` **[3P S13 `submission/sub_agents/code_analyzer.yaml` L6–7]** and the 0.2.11 code allows `..` in `!include` when the target stays inside the root (`ensure_no_traversal_components` is applied only to `config_path`, `context.py` L106) **[CODE]**. A scorer that tightened this would reject Variant A and still accept the additive build.

### E5. Validation log

Run on the delivered file, on fresh extractions, 2026-10-17, harness copy swegemma 0.2.7 / adk-submission 0.2.11 / adk-eval-core 0.1.0 / google-adk 1.36.1 (B2).

| # | Check | How | Result | Log |
|---|---|---|---|---|
| V1 | Archive audit | `scripts/zipaudit.py` | `testzip()` None; 9 files; one root `agent.yaml`; only `.yaml` / `.md`; no symlinks, directories, traversal, duplicates, encryption | `logs/final_1_zipaudit.log` |
| V2 | Entry diff vs your VNEXT | inline Python, CRC-32 + SHA-256 | 7 of 7 original entries identical and in the original order; 2 new byte-copies; none removed | `logs/final_2_entry_hashes.log` |
| V3 | Include / `config_path` table under two rules | `scripts/include_table_dual.py` | 5 refs; 0 missing under relative-to-file and under root-relative; 0 `..` | `logs/final_3_include_table_additive.log` |
| V4 | **Organizers' loader, schema, tool and model registries, generation constraints** | `scripts/preflight_compile.py <harness> <dir>`, normal and forced-fallback modes | **PASS** and **PASS** (your VNEXT, same script: **FAIL** and **FAIL** — `!include file not found: …/sub_agents/prompts/analyzer.md`) | `logs/final_4_preflight_{normal,fallback}_{additive,orig}.json` |
| V5 | Compiled shape | from the compile record | root `swe_coder` with 9 registry tools + `code_analyzer`; analyzer has 4 tools; model `openai/gemma-4-31b-it-qat-w4a16-ct` in both; `include_thoughts: false` with the injected default `thinking_budget: 4096`; `eval_config.yaml` parsed as 120 / 40 / 4.5 / 100, no unknown keys | `logs/compile_vnext_additive.json` |
| V6 | Scripted-fake-model ADK run | `scripts/adk_smoke_fake_llm.py`, google-adk 1.36.1 | `RAN_TO_COMPLETION`: root → `code_analyzer` → root; issue text reached the analyzer prompt; no raw `{…}` left in either prompt; the harness nudge ("Please continue…") is consumed once because `skip_summarization: true` ends the first invocation | `logs/final_5_smoke_additive.json` |
| V7 | Prompt vs declared tools | `scripts/prompt_tool_check.py` | 0 mentioned-but-undeclared tools | `logs/final_6_prompt_tool_check_additive.log` |

**What this is not.** V4 is **not** the official scorer's compile: it runs the organizers' public loader/schema/registry code from a third-party mirror of the wheelhouse, at versions that may be older than the scorer's (B2). V6 uses a **scripted fake model**: **not** Gemma, **not** vLLM, **not** the sandbox, **not** a task run. No score or runtime is implied. The three other candidates were compile-checked only (no V6).

### E6. Residual risks and hardening not applied

Not applied, because each changes your build and the task is the smallest correction for validity. Each is yours to decide.

| # | Risk in the recommended ZIP | Evidence | Option (not applied) |
|---|---|---|---|
| 1 | **Never run on the real scorer.** | B2 | G4 pre-flight on the scorer's wheels before spending the day's slot. |
| 2 | `timeout_seconds: 120` is also the pytest verification timeout; whether Stage 2 reads the submission's value is **UNKNOWN** (`metric.py` unpublished). | **[CODE `swegemma/harness/verification.py` L498–503]**; third parties keep it ≥ 180 **[3P S9 L54]** | Raise to 180. Affects score, not validity. |
| 3 | Thinking state is wheel-dependent. `include_thoughts: false` turns thinking off in the 0.2.11 copy, but is reported not to on 0.2.13 + swegemma 0.2.10 when no budget is set; then the 2048-token analyzer cap could truncate. | **[CODE `adk_submission/resolvers/generation.py` L94–99; 3P S10 L11–14; VERIFY]**. If thinking is silently on, calls cost ≈21 s each in the organizers' sample run **[3P S8b notes.md L100–101; CALC]**, so tasks tend to run to the 4.5-min cap and runtime approaches the 10.0–11.6 h worst case. | `thinking_level: none` compiled on 0.2.11 **[EXEC `logs/exp_level_none.json`]**; `thinking_budget: 0` is **rejected** by the 0.2.11 schema ("Input should be greater than or equal to 1") **[EXEC `logs/exp_budget_zero.json`]** but is reported to be the working off-switch on 0.2.12 / 0.2.13 **[3P S10 L15–16]**. Both **UNVERIFIED** on the scorer's wheels; run G4 first. |
| 4 | 12-h fit holds only if per-task setup ≤ ~1.5 min. Setup is **UNKNOWN**. | **[CALC, App. B]**. Two third-party bounds, both weak: ≈25 s setup measured on a local T4×2 replica, not scorer hardware **[3P S8b notes.md L98–102]**; ≥ ~1.3 min per-task overhead inferred from scorer wall time, which also contains Stage-2 validation and queueing **[3P S8 L24; INF]**. | None; record elapsed time (G6). |
| 5 | `skip_summarization: true` costs one nudge per task. | **[EXEC V6; CODE `agent_runner.py` L712–715]** | None needed; harmless. |
| 6 | A Kaggle-side fault recurs regardless of the package. | R1 | Re-upload of identical bytes is the test. |

If you build or submit any other candidate instead: EVIDENCE-V1 (8 min), HYBRID (12 min) and GRAPH-FUSION (60 min, caps equal scorer defaults) carry the 12-h exposure in C2; none of them needs a validity patch.

---

## F. Sources

Types: **PRIMARY-nr** = official Kaggle page, JavaScript-rendered, not readable by my tools (B3); **COPY** = third-party copy of official text; **3P** = third-party record; **LOCAL** = code I executed. No source below was a live fetch of an official Kaggle page.

| ID | Source | Type | Used for |
|---|---|---|---|
| S1 | https://www.kaggle.com/competitions/gemma-4-developer-agent/overview | PRIMARY-nr; text via S5 | root `agent.yaml` in `submission.zip`; 12-h limit; model; `!include` and traversal rules |
| S2 | https://www.kaggle.com/competitions/gemma-4-developer-agent/rules | PRIMARY-nr; **not read** | **VERIFY here:** submission slots, what a failed run costs |
| S3 | https://www.kaggle.com/competitions/gemma-4-developer-agent/data | PRIMARY-nr; text via S5 | ~120 test tasks; `submission.parquet`; `HARNESS_README.md` |
| S4 | https://www.kaggle.com/code-competition-debugging | PRIMARY-nr (only the title "Code Competitions - Errors & Debugging Tips" visible) | official error glossary (not read) |
| S4b | https://www.currypurin.com/entry/error | COPY/secondary glossary, re-fetched 2026-10-17, undated | outcome labels and meanings in C0 |
| S5 | https://github.com/8kta/kaggle-gemma4 — `docs/Overview.md`, `docs/Data.md`, `docs/HARNESS_README.md` | COPY | every Overview / Data / README line cited as "S5". README copy = 49,356 B, SHA-256 `3d6e57a13234cb4e783ba24eaab486459af76e0923ea4c6607cd41cc8961bbbb`. Unnumbered `L` in §0–§B for README, e.g. "S5 L99–102", = `HARNESS_README.md`. |
| S6 | https://github.com/happyc0der/gemma-swe-agent — `docs/HARNESS_README.md`, `docs/competition.md` | COPY | **older README revision** (46,294 B, SHA-256 `0a93ab2c…e4e0f`; 150 lines differ from S5); `competition.md` L22 corroborates "12 hours … sandbox setup included, verification excluded" |
| S7 | https://github.com/mangeshraut712/Hindai — `docs/KAGGLE_GEMMA4.md` L21–31 | 3P | non-compiling package → "Notebook Threw Exception" |
| S8 | happyc0der repo — `experiments/kaggle_submissions.md` | 3P | error texts, outcome ledger, runtimes, 10-07/10-08 incidents |
| S8b | happyc0der repo — `experiments/2026-09-27-day4/notes.md` L97–116 | 3P | organizers' sample run time per call; local setup time; retraction context |
| S9 | happyc0der repo — `docs/harness-fidelity.md` | 3P | 09-27 same-version wheelhouse re-release; keep `timeout_seconds` ≥ 180 |
| S10 | https://github.com/CharlieHerbst331/gemma4-agent-lab — `docs/THINKING_OFF_T0.md`, `docs/STATUS.md`, `tests/test_harness_0211.py` | 3P | scorer wheels 0.2.12/0.2.13, swegemma 0.2.10/0.2.11, thinking-off behaviour |
| S11 | https://github.com/emiliodavola/kaggle-gemma-agent — `docs/competitive-options-playbook.md` §10 | 3P relaying forum answers (threads 743063, 744807, 745028, 745059 — **not opened by me**) | sequential tasks; four eval keys; 12-h error; GPU outage; undeclared tool |
| S12 | happyc0der repo — `harness/official/` (swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0) | LOCAL mirror of the organizers' wheels | all `[CODE]` and `[EXEC]` compile results |
| S13 | https://github.com/ennydev-2026/gemma-4-developer-agent — `submission/` | 3P copy of the organizers' sample | sample uses `!include ../prompts/analyzer.md` |
| S14 | https://github.com/bansal1600/kaggle-finetune-gemma — `docs/competition.md` L109–124 | 3P | 1 submission/day, 720 min, scorer wheels 0.2.12, outage, failed run uses a slot |
| S15 | https://github.com/LogosTopos/gemma-4-developer-agent — `docs/research/history/SUBMISSION_DIAGNOSIS.md`, `analysis/2026-09-27-localization/runtime/submission_status_evidence.json` | 3P | `inference.py` not public; 09-24 "Exceeded Allowed Compute" |
| S16 | https://github.com/tamasmakos/swe-bench-press — README L38–47 | 3P | wheelhouse dataset v29 = adk-submission 0.2.13, swegemma 0.2.10 |
| S17 | https://aiwiki.ai/wiki/gemma_4_developer_agent_competition (updated 2026-10-03) | secondary | corroborates 12 h incl. setup excl. validation, 1 submission/day, `submission.zip` + root `agent.yaml` |
| W | https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse (URL built from the slug in S14/S16; **not opened**) | PRIMARY-nr | scorer wheels |
| L1 | google-adk 1.36.1; kaggle 2.2.4 (local venvs) | LOCAL | ADK smoke run; Kaggle API method and field names |

---

## G. Evidence still needed from Kaggle (checklist)

Do in this order. G1–G3 cost nothing and consume no submission.

| # | Get | How | Decides |
|---|---|---|---|
| **G1** | `errorDescription`, `ref`, `date` (UTC), `status`, `totalBytes`, `fileName` for **every** row. The CLI hides `errorDescription` (shows COMPLETE, blank score) **[3P S8 L3; S4b]**. | PowerShell one-liner below (shell syntax **not run here**; the Python expression was run against a **synthetic** stand-in API, `logs/g1_oneliner_synthetic_test.log`) | R1 vs R2 vs R3 |
| **G2** | Refresh and re-run G1 later. A row with "A system error. Please try resubmitting…" that now has a number was rescored (precedent 10-07/10-08 **[3P S8 L29–30]**). Compare row dates with 10-07 / 10-08. | same command | R1 → HIGH |
| **G3** | Which ZIP each row is: match `totalBytes` to 5,938 (VNEXT) / 5,865 (GRAPH-FUSION) / 4,849 (EVIDENCE-V1) / 5,075 (HYBRID) and, locally, `(Get-FileHash .\<file>.zip -Algorithm SHA256).Hash` to Appendix A. **VERIFY** that `totalBytes` equals the uploaded file size. | PowerShell | which rows are VNEXT (R2) |
| **G4** | Compile on the **scorer's** wheels. In a Kaggle notebook with the competition wheelhouse attached, run the organizers' install cell (**VERIFY** the exact lines; I have the Getting-Started cell structure only: it installs every `*.whl` from `/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse` **[3P copy of the notebook, my `getting_started_nb.txt`]**), unzip the candidate into a fresh folder, then `python -I preflight_compile.py - <folder>`. Record `versions` and `VERDICT_compile_submission`. An import error means the script is stale for that wheel (never tested on swegemma 0.2.10/0.2.11 or adk-submission 0.2.12/0.2.13). | notebook | R4 |
| **G5** | If G1 says "A system error" and an identical re-upload errors again: Kaggle Support (Help → Contact Support; URL not verified) with refs, dates, `errorDescription`. Read competition forum threads 743063, 744807, 745028 **[3P S11; unopened by me]**. Check the Rules page for slot consumption (S2). | web | slot cost (D) |
| **G6** | After the next run: record `date`, completion time, elapsed hours vs 12 h; if > ~10 h, lower `max_time_minutes`. | G1 output | R3 |
| **G7** | The uploaded file name is exactly `submission.zip` **[DOC S5 Overview L26]**. | upload form | R6 |
| **G8** | Keep a local ledger: SHA-256 of each uploaded ZIP ↔ submission `ref`. | text file | future attribution |

G1 / G2 command (dates print in UTC):

```powershell
python -c "from kaggle.api.kaggle_api_extended import KaggleApi; a=KaggleApi(); a.authenticate(); [print(d.get('ref'), (d.get('date') or '')[:19], d.get('status'), d.get('publicScore'), d.get('totalBytes'), d.get('fileName'), '|', d.get('errorDescription')) for d in (s.to_dict() for s in a.competition_submissions('gemma-4-developer-agent', page_size=50))]"
```

---

## Appendix A — hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `submission-VNEXT.zip` (as attached) | 5,938 | `292c4ab28c9c516f26f92b71e9352f0e5d87dbfef95b0120845b77f6f62c00da` |
| `submission-GRAPH-FUSION-V2.zip` | 5,865 | `a9e9b7a333a059dce7ce88e660b80ef651e8015c00614591e6994e261322bbe5` |
| `submission.zip` (EVIDENCE-V1, A1) | 4,849 | `46e455c81d594b9532cd51f142bc7482020293514b36d6a539ecff21edc67343` |
| `submission-GEMMA-HYBRID-V2-ADAPTIVE.zip` | 5,075 | `2932140057fca9e0aeea2dad736a57dd025fcf6ab1f5f81c8e49d63274e7d66c` |
| **`submission-VNEXT-INCLUDEFIX-ADDITIVE.zip` (recommended)** | 7,700 | `c26518e6a6b91eff4136238a121a93bb045e593e7586b314795b6945efac1126` |
| `submission-VNEXT-INCLUDEFIX.zip` (Variant A, not delivered) | 5,941 | `f043d43d5cc80a665f9fc4d1bbb921e35039897d91e0cead8ea223ecdd962b20` |

Per-entry hashes of the recommended ZIP: E3. All attached-ZIP hashes recomputed 2026-10-17 **[EXEC `sha256sum`]**.

## Appendix B — 12-hour arithmetic (ESTIMATE)

Worst case = N × (cap + s) / 60 h, N = 120 sequential tasks **[DOC S5 Data.md L78 "about 120"; 3P S11 L495 "sequential"]**, every task running to its cap. 12 h = 6.0 min per task all-in. Per-task setup *s* is **UNKNOWN**; two bounding **ASSUMPTIONS**: s = 0.5 min (≈25 s measured on a local T4×2 replica, not scorer hardware **[3P S8b L102]**) and s = 1.3 min (inferred from scorer wall time, which includes Stage-2 validation and queueing **[3P S8 L24]**). The 12-h limit includes setup and excludes validation **[DOC S5 Overview L55]**.

| Candidate | Cap (min) | s = 0.5 | s = 1.3 | Break-even s |
|---|---:|---:|---:|---:|
| VNEXT | 4.5 | 10.0 h | 11.6 h | ≤ 1.5 min |
| EVIDENCE-V1 | 8 | 17.0 h | 18.6 h | none (cap > 6.0) |
| HYBRID-V2-ADAPTIVE | 12 | 25.0 h | 26.6 h | none |
| GRAPH-FUSION-V2 | 60 | 121.0 h | 122.6 h | none |

Call-rate note **[CALC]**: organizers' sample run on 4×L4 used 305.8 s and 309.6 s for 14–15 tool calls → ≈20–22 s per call **[3P S8b L100–101]**. At that rate the caps bind after ≈12–13 calls (4.5 min), ≈22–24 (8 min), ≈33–35 (12 min). Thinking-off agents are faster per call; thinking state on the scorer is wheel-dependent (E6 #3). Observed third-party totals at 3.5–5.0-min caps: ≈6–7.7 h **[3P S8]**. Staff reportedly advise a moderate `max_time_minutes` **[3P S11 L498–500]**.

## Appendix C — tool semantics audited (harness copy S12; paths under `swegemma/`)

| Tool | Behaviour | Source | Prompt consequence |
|---|---|---|---|
| `search_similar_code(query, k=10)` | Contract "Function name or code snippet". Query resolved as a node name (exact → `.`/`;` suffix → case-insensitive substring); `embed()` is a lookup in a precomputed NPZ, not a text embedder; unresolved → `[]` → `count: 0`; call still charged. | `tools/graph.py` L94; `graph/graph_utils.py` L149–204; `graph/embedding_utils.py` L132–216; `graph/retrieval_utils.py` L377–386; `tools/base.py` L59–62 | Concept phrases (P1, P2) return nothing; symbol names work. |
| `get_code_neighbors(node, edge_type=None, max_neighbors=50)` | Unresolved node → `[]`; `edge_type` = exact equality on edge `type` or `relation`; `sorted(...)[:max]`. Docstring examples `'CALLS'`, `'DEFINED_IN'`, `'IMPORTS'`; real data vocabulary **UNVERIFIED**. | `tools/graph.py` L26; `graph/graph_utils.py` L336–339, L346–363 | A wrong `edge_type` string silently returns `[]`. |
| `get_code_subgraph(nodes)` | Empty list → `ValueError`; unresolved names silently dropped; induced subgraph. | `graph/graph_utils.py` L373–374, L378–388 | Needs 2+ exact symbols. |
| `read_file` | Workspace-relative path; ≤150 lines and ≤10,000 chars per call. | `tools/workspace.py` L17–22, L114–126; `budget.py` L28–31 | Chunk reads. |
| `write_file` | Workspace-only create/overwrite. | `tools/workspace.py` L144–150 | — |
| `edit_file` | File must exist and be non-empty; diff output capped at `max_stdout_chars` (5,000). | `tools/workspace.py` L215–218, L233–238 | Empty file → use `write_file`. |
| `run_command` | Timeout = min(`timeout_seconds`, max(5 s, remaining agent time)); stdout and stderr each capped at 5,000 chars. | `tools/execution.py` L26–40, L49–51 | Pipe to `head`. |
| `submit_patch`, `get_status` | Free (`count_tool_call=False`). The loop stops once `patch_submitted`. | `tools/execution.py` L71, L101; `harness/agent_runner.py` L635–637 | VNEXT's "submit_patch ENDS the task" is consistent. |

Harness loop facts: ≤3 consecutive nudges ("Please continue your work using the available tools, or call submit_patch…") **[CODE `agent_runner.py` L499–500, L712–715]**; nudge counter resets on a tool call (L677–678); time/tool/turn budget breaks (L581–672); working-tree-diff fallback (L760–795).

## Appendix D — DRIFT DETECTED

| # | Drift | Evidence |
|---|---|---|
| 1 | **Two revisions of `HARNESS_README.md`** exist: S5 (newer: documents `eval_config.yaml`, Stage 1 `scripts/inference.py` → `submission.parquet`, `thinking_budget` 0–32,768) vs S6 (older: `metric/scoring.py`, "or referenced in `submission.csv`", `thinking_budget` 1–32,768). Which one is on the Data tab now is **UNKNOWN**. VERIFY: download the Data-tab file and compare SHA-256 with S5's. | `diff` of the two copies **[EXEC]** |
| 2 | README says `..` components are "strictly blocked (`PathTraversalError`)"; Overview says traversal "via ../" is not allowed; the organizers' sample uses `!include ../…`; 0.2.11 code allows in-root `..` in `!include`. | S5 README L102; Overview L100; S13 L6–7; `context.py` L106 |
| 3 | README (S5 L148) documents `thinking_budget` 0–32,768 and "use `0` or `include_thoughts: false` to disable thinking"; the 0.2.11 schema rejects 0 (`ge=1`); on 0.2.13 `include_thoughts: false` without a budget reportedly leaves thinking on. | **[EXEC `logs/exp_budget_zero.json`]**; S10 L11–16 |
| 4 | 0.2.11 copy does not forward the numeric `thinking_budget`; later wheelhouses reportedly do. | `adk_submission/resolvers/generation.py` L61–126; S11 L482 |
| 5 | README: scorer reads `eval_config.yaml` (S5 L98, L526–548); the organizers' Getting-Started notebook hard-codes `max_tool_calls = 100` and `max_time_minutes = 5.0` and comments out the file's values. | my `getting_started_nb.txt` lines 240–243 **[3P copy]** |
| 6 | `edge_type` examples: docstring "CALLS" vs Data page "calls". | `tools/graph.py` L26; S3 |
| 7 | swegemma 0.2.11 removed the `swegemma.models` helpers; `official_compile_check.py` imports them, so `preflight_compile.py` has a fallback. | S10 L9–10 |
| 8 | GRAPH-FUSION's `eval_config.yaml` equals the scorer defaults (a no-op cap). | README L538–545 |

## Appendix E — validation commands and logs (all in the scratchpad `logs/`)

`zipaudit_fresh.log`, `compile_{vnext,graphfusion,evidence,hybridv2,vnext_includefix,vnext_additive}.json`, `include_table*.log`, `final_1…7_*.log|json`, `exp_level_none.json`, `exp_budget_zero.json`, `record_check.log`, `prompt_tool_check.log`, `prompt_budget_lines.log`, `g1_oneliner_synthetic_test.log`. Scripts: `zipaudit.py`, `include_table_dual.py`, `preflight_compile.py` (delivered), `adk_smoke_fake_llm.py`, `prompt_tool_check.py`, `build_zip_additive.py`.

## Appendix F — limitations

- No screenshot or Kaggle log (B1); no live fetch of any official Kaggle page (B3); scorer source and `scripts/inference.py` / `metric.py` unavailable (B2).
- Compile results are for swegemma 0.2.7 / adk-submission 0.2.11; the scorer's wheels are newer.
- No Gemma, vLLM, sandbox or scorer run; the ADK smoke test used a scripted fake model and covered only the patched VNEXT, not the other three.
- Third-party claims (S7–S16) are records I read, not verified by me; relayed forum statements (S11) were not opened at the source.
- PowerShell commands were not executed (no PowerShell here).
