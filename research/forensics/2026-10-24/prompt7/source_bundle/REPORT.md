# GEMMA FORENSICS FOLLOW-UP (Prompt 7)

Competition: Google - The Gemma 4 Developer Agent Competition. Author environment: cloud container, 2026-10-24. Extends `SUBMISSION_FORENSIC_REPORT.md` (Mission 1; not repeated here).

Labels: **CONFIRMED** (I ran/read it myself) | **INFERRED** | **UNKNOWN** | **BLOCKED** (could not be attempted) | **NOT TESTED**.

## 0. Result

| Question | Status | One line |
|---|---|---|
| Q1 Which uploaded ZIP = which Kaggle row? | **UNKNOWN / BLOCKED** | No Kaggle credentials and no route to kaggle.com from here. Ready-to-run exporter shipped. |
| Q2 Were the two "Kaggle Error" rows platform, package, or unresolved? | **UNRESOLVED** | Needs each row's `errorDescription`. Third-party evidence leans platform-side for 10-07/10-08 rows; not proof for yours. |
| Q3 Does S0 / repaired VNEXT compile on the ACTUAL competition wheelhouse? | **BLOCKED** (S0 also not supplied) | Old-mirror results only. Notebook shipped to get the real answer. |
| Q4 Candidate fit for one user-submitted run? | **None eligible** | Best candidate is HOLD. Do not spend a slot yet. |

**One recommendation:** run `KAGGLE_CURRENT_WHEELHOUSE_PREFLIGHT.ipynb` on Kaggle (RUN_ORDER step 4); run the free metadata exporter first (step 3). No submission slot needed for either.

## 1. Evidence rules applied
No claim of a Kaggle Error cause without that row's metadata or logs. The old `swegemma 0.2.7 / adk-submission 0.2.11` mirror is not assumed to match the scorer. Static ZIP checks, fake-model replay and custom validators are not called official current-harness tests. Nothing fabricated; no submission made; no token read, printed or requested. A successful official compile is not reported because the current wheelhouse was inaccessible.

## 2. What I could and could not reach (CONFIRMED, `logs/00_*`, `logs/01_*`)
- Proxy CONNECT returns 403 for `www.kaggle.com`, `api.kaggle.com`, `storage.googleapis.com`. PyPI is reachable but has no `swegemma`, `adk-submission` or `adk-eval-core` (HTTP 404), so the wheelhouse cannot be obtained another way.
- No `KAGGLE_*` environment variables and no token file (booleans only; contents never read).
- The Prompt-6 "S0" archive was never attached: **UNKNOWN**. It appears in `candidate_manifest.csv` as BLOCKED.

## 3. Phase A - inventory (CONFIRMED, hashes recomputed from the files; see `candidate_manifest.csv`)
| Label | File | Bytes | SHA-256 (first 16) |
|---|---|---|---|
| VNEXT-ORIGINAL | submission-VNEXT.zip | 5938 | 292c4ab28c9c516f |
| VNEXT-INCLUDEFIX-ADDITIVE | submission-VNEXT-INCLUDEFIX-ADDITIVE.zip | 7700 | c26518e6a6b91eff |
| EVIDENCE-V1 (assumption A1) | submission.zip | 4849 | 46e455c81d594b95 |
| HYBRID-V2-ADAPTIVE | submission-GEMMA-HYBRID-V2-ADAPTIVE.zip | 5075 | 2932140057fca9e0 |
| GRAPH-FUSION-V2 | submission-GRAPH-FUSION-V2.zip | 5865 | a9e9b7a333a059dc |
| S0 (Prompt 6) | not supplied | - | - |

Mission-1 findings preserved: original VNEXT has two broken relative `!include`s (`sub_agents/code_analyzer.yaml` L9, L17); the additive ZIP adds two byte-copies and changes nothing else; neither result proves current-scorer compatibility; the cause of the historical Kaggle Error rows was not proven.

## 4. Phase B - submission metadata: BLOCKED
- `fetch_submission_metadata.py` written against the installed SDK shapes (kaggle 2.2.4: `competition_submissions()` returns `ApiSubmission`; keys `date, description, errorDescription, fileName, privateScore, publicScore, ref, status, teamName, totalBytes, url, submittedBy` via `to_dict()`; the CLI hides `errorDescription`).
- Real run here: exit 3, "BLOCKED... No token was read or printed" (`logs/10_*`). It writes nothing fake.
- Tested on **SYNTHETIC** shim rows (invented; `logs/11_*`, `logs/12_*`): JSON/CSV/Markdown output, size-association, `--previous` rescoring diff, secret-key dropping and env/Bearer scrubbing all behave. This proves the script's logic, not any Kaggle fact.
- `submission_metadata.TEMPLATE.json/.csv` are empty templates, labelled; no live data exists.
- Size association is **SIZE-ONLY (INFERRED)**: the SDK object exposes no content hash (observed keys are checked at run time and reported). All candidate sizes are distinct, so a size match is a useful lead, not proof; a re-zipped file would not match.

## 5. Q2 - the two "Kaggle Error" rows
- UNKNOWN for your rows. Nothing in this package can classify them without their `errorDescription`.
- Third-party, not verified by me (happyc0der `experiments/kaggle_submissions.md` L3-10, L29-30): the same competition shows distinct texts for distinct failures: "A system error. Please try resubmitting..." (day 13 and 14, submitted 10-07 and 10-08, first shown failed, **rescored by 10-09**, scores 0.10 each); "Your notebook hit an unhandled error while rerunning your code..." (day 8); "...requested more CPU, GPU or TPU resources than are available" (day 3, which that author first read as the 12 h cap and later withdrew). Their own comment: leaderboard best-score dates for 10-07/10-08 were sparse, "consistent with a Kaggle scoring outage".
- INFERRED reading: a row whose `errorDescription` says "A system error" and which later rescored was platform-side. A package/compiler error would be deterministic and would not rescore. If your two rows are not from 10-07/10-08, this does not transfer.
- Decision table once you have the text: "system error" + later rescored -> platform; "unhandled error while rerunning" -> exception in the scoring run (compile failure in the outer script is one possible cause, UNKNOWN); resource/compute text -> not a compile fault (cap or capacity, cause UNKNOWN).

## 6. Phase C - current-wheelhouse compile: BLOCKED. What is ready
| Step | Status | Where |
|---|---|---|
| 1 Inspect current official starter | **BLOCKED** (Kaggle unreachable). I hold an OLDER copy; the notebook's install cell is based on it and flags this | notebook cells 0, 2 |
| 2 Offline install procedure | **INFERRED** from that older starter: symlink wheels (restore `+cu128`), `pip install --no-deps --force-reinstall` | cell 2 |
| 3 `preflight_compile.py` support for discovered versions | **UNKNOWN**: versions not discoverable here. Original kept unmodified in `reference/`. **No `preflight_compile_current.py` shipped**: the current compiler was never inspected, so adapting it would be guesswork. Its fallbacks cover the third-party-reported 0.2.11 layout (no `swegemma.models.registry`, no `validate_single_declared_model`), but this is NOT TESTED on those wheels | cell 6 |
| 4 Official validator + `compile_submission` | **NOT TESTED**; cell 4 prints exact signatures, cell 6 records exit/versions/output | cells 4, 6 |
| 5 Compile S0 / additive / original (+ controls) | **NOT TESTED**; original VNEXT is the negative control | cell 6 |
| 6 Layout, includes, `config_path`, model, tools, extensions, eval config, schema | old-mirror CONFIRMED (section 7); current NOT TESTED | cells 5, 6 |
| 7 Does the live resolver honour thinking-off? | old mirror CONFIRMED; current **NOT TESTED**, cell 8 tests it | cell 8 |
| 8 Meaning of `timeout_seconds` | old mirror CONFIRMED; current NOT TESTED, cell 9 greps installed code | cell 9 |

Why step 7 matters (INFERRED from third-party, NOT TESTED by me): happyc0der commit `e48ef3b` (2026-10-09) and CharlieHerbst331 `docs/THINKING_OFF_T0.md` L6-16 report that on newer wheels (swegemma 0.2.10/0.2.11, adk-submission 0.2.13) `include_thoughts: false` alone leaves thinking ON because the default budget 4096 wins; `thinking_level: none` (or budget 0) turns it off. VNEXT and the additive ZIP use only `include_thoughts: false`. If that is true, they would run with thinking ON, ~21 s per tool call in the organizers' sample, which erodes the 12 h margin. Also third-party: swegemma 0.2.11 removed `swegemma.models.registry` (happyc0der `9bcdf9f`, ledger "v11 import failure").

## 7. Old-mirror results (CONFIRMED; OLD MIRROR ONLY: swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0, google-adk 1.36.1; `logs/old_mirror_notebook_run/`)
| Archive | `compile_submission` | Replay (FAKE-MODEL REPLAY - NOT A GEMMA TEST - NOT A SCORE TEST) | `enable_thinking` on the wire |
|---|---|---|---|
| VNEXT-ORIGINAL | **FAIL** `!include file not found .../sub_agents/prompts/analyzer.md` | cannot load | - |
| VNEXT-INCLUDEFIX-ADDITIVE | PASS | ran to completion | false |
| EVIDENCE-V1 | PASS | ran to completion | true |
| HYBRID-V2-ADAPTIVE | PASS | ran to completion | true |
| GRAPH-FUSION-V2 | PASS | ran to completion | true |

Replay (local scripted OpenAI-compatible server, real `LiteLlm` objects, fake sandbox returning a canned diff) confirmed for the 4 loadable archives: agent loads; declared tools resolve; tool arguments parse and results flow back; issue text reaches the conversation (and the analyzer system prompt for VNEXT); no undeclared tool offered; `submit_patch` sets `patch_submitted` (through the FAKE sandbox: plumbing only, not real patch capture); no raw `{template}` braces; no include errors. `submit_patch` ends nothing by itself: when an invocation ends without it the harness re-invokes with a nudge (max 3), per swegemma 0.2.7 `agent_runner.py` L708-718.

Thinking variants of the additive ZIP on this mirror: include_thoughts=false -> false; true+4096 -> true; false+4096 -> **false**; false+`thinking_level: none` -> false; `thinking_budget: 0` alone -> **schema rejects** (`>= 1`) even though `GenerationConstraints.thinking_budget` allows min 0. So on this mirror the third-party "4096 overrides false" behaviour does not occur; it is a newer-wheel claim (README S5 also documents `thinking_budget` 0-32,768). This is the single most useful thing the notebook will resolve.

`timeout_seconds` (old mirror, code): `EvalConfig.timeout_seconds` (config.py L180-188) becomes `command_timeout_seconds`, used for sandbox commands (tools/execution.py L27) and the verification pytest run (verification.py L502). So VNEXT's `timeout_seconds: 120` also bounds test verification: NOT TESTED on current wheels; not changed.

## 8. Phase D - fake-model replay
Run on the old mirror only (section 7). Current wheels: **BLOCKED** until cell 7 runs on Kaggle (exact missing dependency: access to the mounted wheelhouse; the replay needs `adk_submission`, `swegemma`, `google-adk`, `litellm` importable). The optional real-`Evaluator` smoke (cell 10) is NOT TESTED and off by default. Real Gemma inference: NOT TESTED for every candidate.

## 9. Phase E - candidate comparison
| Archive (SHA-256) | Structural | Old-mirror compile | Current-wheel compile | Fake replay | Real Gemma | Row association | Remaining risks | Decision |
|---|---|---|---|---|---|---|---|---|
| VNEXT-ORIGINAL `292c4ab2...00da` | FAIL (2 includes resolve to non-existent paths) | FAIL | NOT TESTED (known failure on old mirror) | cannot load | NOT TESTED | UNKNOWN (size 5938 lead only) | include failure | **REJECT** |
| VNEXT-INCLUDEFIX-ADDITIVE `c26518e6...1126` | PASS | PASS | **NOT TESTED / BLOCKED** | PASS (old mirror) | NOT TESTED | none (new file) | thinking may stay ON on newer wheels (INFERRED, third-party); `timeout_seconds: 120` doubles as pytest timeout; worst-case 10.0-11.6 h of 12 h if every task uses its 4.5 min cap and per-task setup is 0.5-1.3 min (setup time UNKNOWN) | **HOLD** |
| EVIDENCE-V1 `46e455c8...7343` | PASS | PASS | NOT TESTED | PASS (old mirror) | NOT TESTED | UNKNOWN (size 4849 lead only; A1 unverified) | thinking ON; worst case 17.0-18.6 h at 8 min cap | **HOLD** |
| HYBRID-V2-ADAPTIVE `29321400...d66c` | PASS | PASS | NOT TESTED | PASS (old mirror) | NOT TESTED | UNKNOWN (size 5075 lead only) | worst case 25.0-26.6 h at 12 min cap; prompt calls `search_similar_code` with concept phrases though the tool resolves symbol names | **HOLD** |
| GRAPH-FUSION-V2 `a9e9b7a3...bbe5` | PASS | PASS | NOT TESTED | PASS (old mirror) | NOT TESTED | UNKNOWN (size 5865 lead only) | worst case 121-123 h at 60 min cap; same `search_similar_code` issue | **HOLD** |
| S0 (Prompt 6) | not supplied | - | BLOCKED | - | - | - | cannot assess | **HOLD (BLOCKED)** |

The 12 h figures are worst-case arithmetic from Mission 1 (N=120 tasks x (cap + setup)); agents often stop early, so they are upper bounds, not predictions; the 1-submission-per-day and 720 min limits come from third-party digests. No score threshold is promised. Nothing is eligible: every non-rejected archive lacks a current-wheel compile.

## 10. Remaining risks and what would change the plan
- If the notebook shows the additive ZIP compiles on the current wheels but `enable_thinking` is not false on the wire, that is a concrete diagnosed defect: a minimal settings change (`thinking_level: none`, only if the live schema accepts it) would then be justified. I did not build that archive; there is no evidence yet.
- If the current compiler rejects something old-mirror accepted, the cell 6 log names the file and message; fix only that.
- Per-task compile failures are swallowed inside `agent_runner.py` (try at L217, `except Exception` at L799-801 sets `agent_error`), so a compile failure plausibly scores 0.00 rather than raising; how the unseen outer `inference.py` treats run-level failures is UNKNOWN.
- The wheelhouse can change between your preflight and a real submission (Kaggle mounts the latest regardless of the `/N` pin; third-party).

## 11. Sources
Local, read by me: `swegemma 0.2.7`, `adk-submission 0.2.11`, `adk-eval-core 0.1.0` (happyc0der/gemma-swe-agent `harness/official`, a mirror, not the current scorer); kaggle 2.2.4 SDK source. Third-party, not verified: happyc0der/gemma-swe-agent (`experiments/kaggle_submissions.md`, `experiments/kaggle_gpu_hours.md`, `scripts/compile_check.py`, commits `e48ef3b`, `b919ccd`, `9bcdf9f`, `a01937f`, `066df36`); CharlieHerbst331/gemma4-agent-lab (`docs/THINKING_OFF_T0.md`, `tests/test_harness_0211.py`, `tests/fixtures/official_starter_codes.json`, which is the same older starter); 8kta/kaggle-gemma4 `docs/Overview.md`, `HARNESS_README.md`; organizer starter notebook `ryanholbrook/getting-started-gemma-4-developer-agent` (older copy).
