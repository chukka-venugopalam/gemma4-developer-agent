# DEVELOPMENT_SET_AND_ABLATION_PLAN.md

**Gemma 4 Developer Agent Competition: development-data research, reproducible ablations and score strategy (Prompt 3)**
Prepared 2026-10-10. Package: this file, `devset_tools.py` (stdlib-only toolkit), `design_calculations.md` (raw simulation/arithmetic tables).

**Evidence legend used throughout.**
`[K]` text of a Kaggle competition page, obtained through a search index (the pages are JavaScript-rendered and my fetch tool returned only page metadata).
`[M]` third-party mirror of those pages. `[T]` third-party analysis or measurement; I did not verify it.
`[X]` project context supplied for this work (your split, score, settings); taken as given.
`[C]` computed by the code in this package (arithmetic or synthetic fixtures). `[D]` design calculation: simulation under stated assumptions.
`[P]` proposed, not done. Source numbers `[S#]` refer to the list in section A.4.

---

## 0. Bottom line

### 0.1 What I could and could not do

The only file uploaded was the prompt. I had no `tasks.jsonl`, no snapshots, no harness, no GPU and no outbound network from my sandbox. So **this report contains no measured Gemma result and no dataset statistic computed by me.** Per the rules, nothing is estimated in place of data.

What it does contain:

1. A sourced inventory of the dataset schema, scoring rules and harness limits, with the conflicts between sources listed (section A).
2. `devset_tools.py`: `profile`, `audit-split`, `scan-bundle`, `summarize`, `budget`, `budget-arith`, `power`, `selftest`. Its plumbing was checked on synthetic fixtures (`selftest` passes and its outputs are byte-identical across two runs). Those fixtures say nothing about Gemma or the real tasks.
3. A leakage protocol, an ablation matrix with decision rules, a 12-hour budget policy, a failure taxonomy and a per-task logging schema (sections C to F).

### 0.2 Six findings that decide the next experiment

1. **The 12-hour limit is a cliff, and it is the first thing to measure.** The evaluation text gives the agent 12 hours for all tasks, inclusive of sandbox setup and exclusive of patch validation [S2]. Notes that quote the hosts say tasks run sequentially, one `eval_config.yaml` applies to every task, and an overrun errors the whole submission (a fix that scores unfinished tasks as 0 was described as planned; I could not confirm it is live) [S5]. Arithmetic from those constraints `[C: budget-arith]`: with N=120 tasks, a 15-minute server start and 0.1 min setup per task, a 5-minute cap has a worst case of 10.45 h and a 60-minute cap has a worst case of 120 h. If the other tasks average 3 minutes, **at most about 5 tasks may run to a 60-minute cap** before the run exceeds 12 h minus a 45-minute margin (about 3 if the others average 4 minutes). The V2 settings carry `max_time_minutes: 60` `[X]`. Whether that is safe depends on the fraction of tasks that hit the cap, which has not been measured.
2. **Time is tokens.** A third-party scorer replica measured roughly 0.6 s + completion_tokens / 25.5 s per model call on 4xL4 [S6]. Taken at face value (re-measure it), a 5-minute task is about 7.6k generated tokens in total, one 4,096-token thinking turn costs about 161 s, and one 16,384-token generation about 643 s `[C]`. Tool-call counts are a poor budget unit; log tokens and seconds per request.
3. **Dev results will not predict the leaderboard; they can diagnose mechanisms.** The dev tasks come from four public repositories (reported counts: fastapi 67, rich 48, requests 13, httpx 1 [S4][S7]) that the model may have seen. The hidden ~120 tasks come from private repositories and were filtered so that a larger frontier model solves or nearly solves each [S3]. Third parties report local scores of 0.18 to 0.24 against leaderboard scores of 0.05 to 0.12 [S4]. VNEXT scored 22/22 on a heuristic localization benchmark and 0.00 on the leaderboard `[X]`. Use dev runs to count repo-agnostic mechanisms (no patch, timeouts, context overflow, edits never executed, malformed calls) and use the leaderboard for outcome confirmation.
4. **Local A/B tests are weak at this size** `[D]`. At 45 tasks and one seed, a screening rule (one-sided exact sign test p <= 0.10 and at least 3 wins) promotes an arm that truly triples the odds of success only 17% to 36% of the time when baseline success is 10%, and 94% of the time only in an optimistic regime (3 seeds, baseline 20%, little task-level correlation). The leaderboard has the same limit: 0.06 on about 58 tasks `[X]` is 3 or 4 solved tasks, Wilson 95% interval about 0.02 to 0.16 `[C]`. Consequence: measure failure **prevalence** in a single arm first (no comparison needed, precise enough to rank failure classes); run A/B only for hypotheses with large expected effects; calibrate noise with an A/A replicate.
5. **Schema discrepancy.** The Data page names the reference-fix column `patch` [S1]; your notes call it `implementation_patch` `[X]`. The tools accept both spellings and `profile` reports which one it found.
6. **A dev-only leak channel to rule out.** The Data page lists offline wheels (fastapi, starlette, pydantic, requests, urllib3, rich, httpx, httpcore, pytest and dependencies) mounted read-only at `/wheels` in the sandbox [S3]. If a wheel of a library under test is newer than a task's `base_commit`, it contains post-fix code that the hidden private repositories cannot offer. Audit the traces for it (section C.3) before trusting any dev score.

### 0.3 The next experiment, in order

| Step | Where / cost | Do | Output and decision |
|---|---|---|---|
| 0a | CPU, minutes | `devset_tools.py profile --tasks tasks.jsonl --snapshots-dir snapshots/` | Fills tables B1-B7; confirms column names; compare with the third-party cross-check values in B.3 |
| 0b | CPU, seconds | `audit-split --tasks tasks.jsonl --splits <your 84/22/23 file>` | PASS / WARN / FAIL on cross-split leakage; list of training tasks to quarantine |
| 0c | CPU, seconds | `scan-bundle --tasks tasks.jsonl --bundle <current ZIP> --exclude-ids-file <train ids>` | Zero hits required before any further run |
| 0d | CPU, official grader, no model | Grader check on all 129 tasks: reference patch must pass, empty patch must fail [S4] | List of healthy tasks; unhealthy tasks leave every pool |
| 1 | One Kaggle 4xL4 notebook (the scorer's hardware [S4][S8]); about n x mean-minutes, e.g. 30 tasks at ~5 min = 2.5 h, at most 5 h at a 10-min cap | **Measurement run, no ablation** (how: D.6): the current best agent, scorer-like config (compaction on), cap 10 min, logging schema of section F, patch snapshots after every edit | Failure-class prevalence, cap-hit fraction f, tokens/s, time-to-first-edit, leak-channel audit |
| 2 | CPU, minutes | Re-grade the saved patch snapshots as if the cap had been 3/4/5/6/8/10 min; `budget` | Yield curve Y(c), conditional yield, E[T](c), P(T > 12 h), a safe global cap c*, stop-predicate precision |
| 3 | GPU, same cost as step 1 | Replicate step 1 on the same tasks (A/A), different seed | Noise floor and the correlation level that decides how many tasks later A/B tests need |
| 4 | GPU, per arm | Ablations of section D, ordered by the largest failure class from step 1 | Promote / drop by the decision rules of D.4 |

Step 1 is the one that cannot be skipped: every later choice (which ablation first, which cap, how many tasks) depends on its output.

---

## A. Verified dataset inventory, schema and sources

### A.1 What the official pages say

| Fact | Value | Evidence |
|---|---|---|
| Competition | Google - The Gemma 4 Developer Agent Competition (Kaggle, 2026) | [S1][S2] |
| Development data | `tasks.jsonl`: **129 public development tasks**, each a bug-fixing instance with reference fix and verification tests for local evaluation | [S1] |
| Documented columns | `instance_id` (repo short name + issue/PR number, e.g. `fastapi_11194`, `rich_3454`), `repo` (owner/repo), `problem_statement`, `patch` (reference diff; **excluded from the hidden test set**), `test_patch` (verification tests; kept private during scoring) | [S1] |
| Further columns | `base_commit`, `hints_text` (may be empty), `created_at` | [S3] mirror only |
| Snapshots | `snapshots/<instance_id>.tgz`: git working trees frozen at `base_commit`, forward history removed | [S3] |
| Code-graph files | 256 files = 129 task-named hard links to **127** commit-named files, so 127 distinct (repo, base_commit) pairs for 129 tasks and at least two tasks share a base commit | [S3], inference by me; `profile` section 7 verifies it |
| Repo mix | fastapi 67, rich 48, requests 13, httpx 1 | [S4][S7] (two independent notes; not verified by me) |
| Hidden test set | about 120 tasks from private repositories, split about evenly between public and private leaderboards; each checked solvable or nearly solvable by a larger frontier model | [S3] |
| Scoring | PASS/FAIL per issue: patch applied to the repository, that issue's validation tests run; score = percentage of patched repositories that pass | [S2] |
| Time limit | 12 h for all tasks, inclusive of sandbox setup, exclusive of patch validation | [S2] |
| Lifecycle | Phase 1 container: agent edits `/workspace`; the patch is the `git diff` of that tree at the end (taken even if `submit_patch` is never called). Phase 2 container: fresh snapshot + patch + `test_patch` + hermetic pytest; resolved iff pytest exits 0 and the required tests passed; edits to tests/config files are reset | [S4][S7], summarising `HARNESS_README.md`, which I did not read |
| Dataset verification | fail-to-pass: tests fail without the fix; pass-to-pass: with fix and tests the whole suite exits 0 | [S3] |
| Submission output | `submission.parquet` with `id` and `prediction` (unified diff or `NO_PATCH`) | [S1] |
| Model and context | one model, `gemma-4-31b-it-qat-w4a16-ct`; 32,768-token context; compaction documented at 14,336 tokens (interval 5 in the README, 15 in the hosts' notebook); local `swegemma eval` runs with compaction **off** by default | [S6][S7] |
| Hardware | the official starter notebook ran on GPU L4 x4 (its logged run took 944.8 s) | [S8]; digest says competition notebooks may use 4xL4 at 2x quota with internet disabled [S4] |
| Local harness outputs | `swegemma eval`; `results/<run>/traces/trace_<id>.json`; `task_results.jsonl` with `duration_s`, `tool_calls`, `error` | [S4][S5] |
| Model-call cost | about 0.6 s + completion_tokens / 25.5 tok/s on 4xL4 (three evaluation arms shared one server, so slightly pessimistic) | [S6] |
| Timeline | final submission 2026-12-02 (53 days from today) and entry deadline 2026-11-25 per the mirror and Kaggle's X post; verify on the Timeline page | [S3][S11] |

### A.2 Conflicts and items I could not verify (resolve before relying on them)

1. **`patch` vs `implementation_patch`**: official name is `patch` [S1]; project notes say `implementation_patch` `[X]`. Check the header of your local file. The tools accept both.
2. **Default per-task caps.** Project settings use 60 min / 100 calls / 500 turns / 300 s `[X]`. A third-party note relays a host statement that a *missing* key in `eval_config.yaml` means *no limit*, and reports a sample config of 10 calls / 1 min [S5][S4]. Always set every cap explicitly; do not rely on defaults.
3. **`thinking_budget` enforcement.** One third-party note says the harness only sends thinking on/off and never enforces the budget [S5]; another says the budget is forwarded and enforced by vLLM, with one observed request obeying a budget of 24 [S6]. They may describe different harness versions. Resolve by logging reasoning tokens per request and comparing with 4,096.
4. **Compaction.** Interval 5 vs 15; local eval default off [S6][S7]. Local ablations must turn it on with the same interval as the scorer, or local and scorer behaviour differ.
5. **Overrun semantics.** Whole-submission failure vs partial credit for finished tasks [S5]. Plan as if it is catastrophic.
6. **Gemma 4 knowledge cutoff.** One catalog lists 2025-01, another lists none [S10]. Read the official model card before using a cutoff to define a "post-cutoff" stratum; the tools take it as a parameter, they do not hard-code it.
7. **The Kaggle pages were not fetched directly.** Facts marked `[K]` come from search-index text of those pages; facts marked `[M]` come from a mirror that calls itself unofficial. The authoritative documents are the Data page and `HARNESS_README.md` (671 lines [S7]) inside your download. Read the latter for the exact CLI flags and output files; I could not.
8. **Python versions.** A digest reports 3.12 in notebooks vs 3.13 in the scorer image [S4]; record interpreter and pytest versions in every run.

### A.3 Boundary of this inventory

Nothing in A.1 was checked against the data itself. Every count in B.3 (third-party cross-check column) must be regenerated by `profile` and compared; if they disagree, trust the script and investigate.

### A.4 Sources

- S1 `[K]` Kaggle Data page: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
- S2 `[K]` Kaggle Overview and Evaluation text: https://www.kaggle.com/competitions/gemma-4-developer-agent
- S3 `[M]` Mirror of Overview, Data and Rules (states it is not official), dated 2026-10-02: https://github.com/sweeden-ttu/developer-agent
- S4 `[T]` Digest and local-evaluation notes, collected 2026-10-01: https://github.com/bansal1600/kaggle-finetune-gemma/blob/main/docs/competition.md and https://github.com/bansal1600/kaggle-finetune-gemma/blob/main/docs/local-eval.md
- S5 `[T]` Budget model with VERIFIED / third-party / ESTIMATE labels and relayed host statements: https://github.com/Gosling-dude/gemma4-developer-agent/blob/main/docs/budget_model.md (README: https://github.com/Gosling-dude/gemma4-developer-agent)
- S6 `[T]` Local scorer replica (call cost, compaction, overflow rule, thinking budget): https://github.com/damsolanke/gemma4-swe-kit
- S7 `[T]` Notes summarising `HARNESS_README.md` (phases, compaction 14,336/5, tools, sample sampling): https://github.com/Acivar-Digital/gemma4
- S8 `[K]` Official starter notebook log (GPU L4 x4, 944.8 s): https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent/log
- S9 `[T]` Lab notes on matched controls and concurrent failure axes (as I read them): https://github.com/CharlieHerbst331/gemma4-agent-lab
- S10 `[T]` Model catalogs (release 2026-04-02; cutoff listed as 2025-01 by one, not reported by another): https://www.datalearner.com/en/ai-models/pretrained-models/gemma-4-31b and https://magica.com/blog/compare/gemma-3-4b-it-vs-gemma-4-31b-it
- S11 `[K]` Kaggle announcement (entry deadline 2026-11-25): https://x.com/kaggle/status/2102793965854662859

---

## B. Dataset profile: tables and code

### B.1 Exact inputs needed

| File | Needed for | Required |
|---|---|---|
| `tasks.jsonl` (129 rows) | everything in B and C | yes |
| `snapshots/<instance_id>.tgz` | exact enclosing-symbol analysis (`--snapshots-dir`); otherwise symbols are approximated from diff text | no |
| your existing split (JSON `{name: [ids]}` / `{id: name}`, or CSV `instance_id,split`) | `audit-split --splits` | for section C |
| the current submission ZIP or its unzipped folder | `scan-bundle` | for section C |
| `HARNESS_README.md`, one `task_results.jsonl` row, one trace JSON | finishing the run adapter of section F | for section F |

### B.2 How to run (descriptive only; no model is involved)

```bash
DATA=/kaggle/input/competitions/gemma-4-developer-agent        # data directory shown in [S8]; use `find $DATA -name tasks.jsonl`
python devset_tools.py profile     --tasks $DATA/tasks.jsonl --snapshots-dir $DATA/snapshots --out out/profile
python devset_tools.py audit-split --tasks $DATA/tasks.jsonl --splits splits_84_22_23.json --out out/audit
python devset_tools.py scan-bundle --tasks $DATA/tasks.jsonl --bundle submission.zip --exclude-ids-file train_ids.txt --out out/scan
```

Outputs: `profile.md` (all tables), `profile.json`, `task_features.csv` (one row per task; also the stratification keys for `summarize`).

### B.3 Statistics, definitions, and cross-checks

"Measured here" is empty on purpose. The third-party values are regression targets for the script, not data.

| Required statistic | Script field(s) | Definition and limits | Third-party value to compare | Measured here |
|---|---|---|---|---|
| Task count by repository | `repo_short` | prefix of `instance_id` | fastapi 67, rich 48, requests 13, httpx 1 [S4][S7] | to fill |
| Task count by year and by repository | `year` from `created_at` | issue/PR creation time | created 2023-07 .. 2026-06 [S4] | to fill |
| Issue type | `issue_type_heuristic`, `it_*` flags | **keyword heuristic**, first matching rule of: traceback/exception, bug wording, feature wording, typing/docs/deprecation, other. Not ground truth | none | to fill |
| Complexity | `n_files_total`, `n_src_files`, `hunks_src`, `lines_changed_src`, `n_symbols` | from the reference `patch`; `src` = non-test `.py` outside `docs/`, `docs_src/`, `examples/` | 91 of 129 touch exactly 1 file, 19 touch 3 or more; median 12 changed lines [S4] (compare with `n_files_total`) | to fill |
| Issue size and shape | `issue_chars`, `has_traceback`, `has_code_block`, `has_repro`, `n_urls` | `has_repro`: a fenced block containing `import`, `def`, `>>>` or `print(` | median 418 characters, range 42 to 10,095 [S4] | to fill |
| Test style | `ts_*`, `n_new_test_defs`, `n_test_files` | regexes over *added* lines of `test_patch`: parametrize, raises, fixtures, mock/monkeypatch, async, class-based, `TestClient`, output capture. `n_new_test_defs` counts new `def test_*` only (a lower bound for tests the verifier runs) | none | to fill |
| Patch size | `lines_added_src`, `lines_removed_src`, `lines_changed_all`, `n_new_src_files` | diff line counts | median 12 lines [S4] | to fill |
| Source-module spread | `n_src_dirs`, `n_src_toplevel`, `n_symbols`, `symbols_mode` | distinct directories / top-level path parts / changed `def`/`class` names; `symbols_mode` is `exact` (AST on the base-commit file from the snapshot) or `approx` (diff text only) | none | to fill |
| Does the issue name the files/symbols that the fix changes? | `m_file_exact_path`, `m_file_basename`, `m_file_dotted_module`, `m_file_any`, `m_symbol_strong`, `m_symbol_in_code_block`, `m_symbol_plain_weak`, `m_any_path_in_text`, `m_traceback_frames` | tasks with at least one gold src file. `symbol_strong` = in backticks or a traceback; weak matching drops generic names. These are **upper bounds on text-only localization**, not agent results | none | to fill |
| Hints | `hints_chars` | non-empty `hints_text` rows | "no task has hints" [S4] | to fill |
| Shared identifiers | profile section 7 | duplicate `instance_id`, shared (repo, `base_commit`), identical patch or issue hash | 127 distinct commits for 129 tasks [S3] | to fill |

### B.4 What the profile is for

It does three jobs and nothing else: (1) catches schema surprises before any experiment; (2) supplies strata (repository, issue type, size bucket, explicit-localization flag) so every later failure table can be cut by task type; (3) feeds the leakage audit. It is not a difficulty model and must not be reported as a score. A localization-style heuristic that looks excellent on dev is exactly what VNEXT showed can coexist with a 0.00 leaderboard result `[X]`.

---

## C. Leakage analysis and recommended protocol

### C.1 Threat model

| # | Leak or bias | Why it matters here | Control | Measured by |
|---|---|---|---|---|
| T1 | Reference `patch` / `test_patch` text inside anything the agent sees (prompt, skills, playbook, few-shots, adapters) | The agent prompt must contain only what exists at inference time | `scan-bundle` over the whole submission folder, excluding only training ids that are allowed to inform priors | hits = 0 |
| T2 | Training-derived priors built from tasks later used for evaluation | The playbook is derived from the 84 training tasks `[X]`; any overlap inflates validation | Split roles of C.2; priors only from the training split | `audit-split` verdict |
| T3 | Near-duplicate or same-fix tasks across splits | Four repos, 129 tasks; at least two tasks share a `base_commit` [S3] | Hard edges: same (repo, `base_commit`), same (file, symbol) changed, same added test def, near-identical issue text. Soft edges are reported: similar text, same file | `audit-split` edges, quarantine list |
| T4 | Adaptive overfitting to the validation split | Validation was already used for localization analysis `[X]` | Treat those 22 as burned for any localization claim; use a lockbox (C.2) | log of every look |
| T5 | Pretraining contamination of public repos and fixes | Dev scores can exceed what private repos allow [S4] | Recency strata against the model cutoff; no-tools recall probe (C.3); trust only paired differences and mechanism counts | probe result by year |
| T6 | Dev-only environment channels (`/wheels`, site-packages copy of the library under test, `.git` remnants) | Hidden private repos have none | Trace audit (C.3) and exclusion of flagged runs | `leak_audit.*` fields of section F |
| T7 | Distribution shift to private repos and frontier-solvable filtering [S3] | Dev rank may not transfer | Cross-repo transfer test (C.2) for any component that learned repository specifics | fastapi to rich and back |
| T8 | Harness fidelity gap (compaction off locally, Python 3.12 vs 3.13, pytest versions) [S4][S6] | Local behaviour differs from the scorer | Scorer-like flags in every run; record versions | run header of section F |
| T9 | `hints_text` | Hidden tasks may carry hints [S4] | Report non-empty fraction; run with and without if non-empty | `hints_chars` |

### C.2 Recommended split protocol

1. **Healthy tasks only.** Run the official grader check (step 0d). Unhealthy tasks leave every pool.
2. **Audit the existing 84/22/23 split** `[X]` with `audit-split --splits`. Any hard edge between the training split and an evaluation split is a FAIL; quarantine the training-side tasks (do not derive priors, playbooks or few-shots from them). Do not move evaluation tasks, so that dev and lockbox keep their size.
3. **Split roles depend on what the arm learned**, which is the cheap way to get more tasks:
   - *Policy-only arms* (confidence gate, graph-escalation rule, reproduction rule, budget rule, investigator presence) use no task-derived content, so every healthy task except the lockbox can be a screening task. That is about 106 tasks instead of 22.
   - *Training-derived arms* (the repair playbook, any retrieved examples) may be evaluated only on tasks that were not used to derive them: the 22 validation tasks and, for the final check, the lockbox. For repository-specific content also run **cross-repo transfer**: derive on rich, test on fastapi, and the reverse (httpx has one task and requests 13, too few to hold out alone). This is the closest local imitation of the private-repo shift.
4. **Lockbox = the 23 held-out tasks**, evaluated once per finalist pair (D.4), never used to tune. Record the date, config hash and result of every look.
5. **Pools for screening**: draw a stratified pool of 30 tasks (stratify by repository, `n_src_files` 1 vs 2+, and reference lines changed <=10 / 11-30 / >30; `task_features.csv` has all three). Extend to 45 only by the rule in D.4. If you want a harder pool, the profile's explicit-localization flags can enrich it, but state that this is an enrichment choice and confirm on a random stratified pool.
6. **Optional new split**: `audit-split --make-split --sizes train=84,dev=22,heldout=23 --heldout-policy newest` builds a repo-stratified split in which hard-linked tasks stay together. `newest` puts the most recent tasks in the lockbox (less likely to be in pretraining) at the price of a drift between train and lockbox. Re-splitting invalidates earlier claims about the old validation tasks; prefer auditing and quarantining.

### C.3 Contamination probe and leak-channel audit

- **No-tools recall probe** `[P]`. For each dev task, give the model only the issue text and ask for a patch, no repository access, one call each (about a minute per task). Measure token-level or line-level overlap with the reference patch. Plot overlap by `created_at` year. A high overlap on old tasks and low on new tasks is evidence of contamination (and the year where it flips locates the effective cutoff). This costs under an hour of GPU time and decides how much to trust old tasks.
- **Trace grep for dev-only channels**. In every dev run flag a task if any `run_command` text, or any file read, matches: `/wheels`, `pip download`, `pip install` (offline installs are legitimate during setup but not for the library under test), `unzip` or `zipfile` on a `.whl`, `site-packages/<package under test>`, `.git/objects`, `git log`, `git show`, `git reflog`. Record `leak_audit.read_wheels_dir`, `leak_audit.read_site_packages_target_pkg`, `leak_audit.git_history_access`. Exclude flagged runs from outcome comparisons and report how many there were.
- **Do the wheels contain the library under test, and which version?** Open the wheel list in your download and compare each wheel version with the task's `created_at`. This is a ten-minute check `[P]`.

### C.4 What must be true before outcome numbers are quoted

Bundle scan clean; split audit PASS or quarantine applied; healthy-task list applied; scorer-like harness flags recorded; leak-audit counts reported; pool and seeds fixed before the run.

---

## D. Ablation matrix

### D.1 Design rules

1. **One block, one variable.** Assemble the agent prompt from six blocks: Role and tools; Localize; Graph policy; Reproduce/Trace policy; Verify and Stop; Budget. Each arm replaces exactly one block of A0 and the diff of the assembled prompt is stored with the run. Frozen across arms: model, exposed tools, sampling (temperature 0.2, top_p 0.95, top_k 40 `[X]`), the thinking setting (one value for all arms, chosen in step 1 from trace evidence), every `eval_config.yaml` cap, compaction on with the scorer's interval, harness and interpreter versions, task pool and order, seeds, verifier.
2. **Same tasks, same seeds, paired analysis.** Nothing is compared across different pools.
3. **Freeze before running.** Arm text and decision rule are written and hashed first. Failures inspected afterwards may motivate a *new* arm, tested on a fresh pool or the lockbox, never an edit of the arm just run on the same pool (that is T4, adaptive overfitting).
4. **A/A first.** A0 and A0' are identical; they give the noise floor and, through their discordant tasks, the correlation level that sets how many tasks later tests need (D.3).
5. **Mechanism before outcome.** Each arm names the mechanism metric that must move before an outcome change is credited to it.
6. **One server per comparison** when the session allows, so start-up (reported up to 20 min [S5]) is paid once and between-session variance disappears.
7. **Cost is counted in task-minutes**: cost(arm) = n x seeds x mean realized minutes (+ one server start per session). Realized minutes come from step 1, not from the cap. Kaggle bills 4xL4 at 2x quota [S4]: convert with your actual weekly quota, which I do not know.

### D.2 The matrix

A0 is the control. "Only change" is relative to A0. Primary metrics are those of section F.2; `dev_resolved` is the official verifier on a dev task, a proxy and not the leaderboard score.

| ID | Only change | Hypothesis | Compute | Mechanism metric (must move) | Expected failure signal (kill) | Decision rule |
|---|---|---|---|---|---|---|
| **A0** | Disciplined single agent: one root agent, all nine tools exposed, ordered checklist (read issue, lexical localization with `git grep`/`read_file`, minimal edit, run the nearest existing test file, submit); no gate; graph tools allowed but not mentioned; no reproduction mandate; no investigator | Reference point | n x k x m | prevalence of each failure class (F.2) | n/a | step 1 output; no decision |
| **A0'** | None (different seed) | Noise floor | same as A0 | A/A discordant tasks | n/a | calibrates D.3; if A/A discordance is large, raise n or seeds before any A/B |
| **A1** Adaptive confidence gate | Localize block: after each phase state LOW/MEDIUM/HIGH for TARGET, ROOT_CAUSE, EXECUTION, PATCH; spend a tool call only to reduce a named LOW item; stop exploring when TARGET and ROOT_CAUSE are at least MEDIUM | Fewer wasted calls and fewer "explore until the cap" runs, so more patches per minute | about A0 (should be lower) | time to first edit, hit-cap rate, tool calls per task, no-patch rate | more premature edits (share of `wrong_files` up); ratings do not predict outcome | D.4 plus a calibration check: P(resolved given HIGH) must exceed P(resolved given LOW), else the gate is not informative |
| **A2** Symbol-based graph escalation | Graph block: once a candidate symbol is named call `get_code_neighbors` on it; call `get_code_subgraph` only while two or more candidates remain; `search_similar_code` takes symbol names, not issue prose | Symbol-keyed queries localize better than free text | about A0 + graph time | right-file and right-symbol rate (analysis-only labels), graph calls per task, seconds per graph call | graph calls up with no localization gain; time to first edit up; hit-cap up | D.4 plus cost-benefit: extra yield per extra minute must exceed the shadow price lambda of E.4 |
| **A12** Fuse when uncertain | Couples A1's gate to A2's graph rule (graph tools only when the gate says LOW). Compared with **A2**, not A0 | The V2 central question: always fusing costs time that the gate saves | about A2 | graph calls per task, hit-cap, `wrong_files` | same as A2 | run only after A1 and A2 are each non-harmful; D.4 |
| **A3** Reproduce / trace policy | Reproduce block: write a failing reproduction under `/tmp` (never in `/workspace`), run it, edit, rerun; submit only with fail-to-pass evidence or a written reason; if no failing reproduction exists after a stated number of calls or minutes, fall back to a reading-based fix. Variant A3b: trace-first (run the failing scenario once to capture the traceback before localizing) | Executable evidence turns more patches into resolved ones and removes wrong-API-detail failures | above A0 (reproduction costs time) | `fail_to_pass_evidence` rate, `edit_without_verification`, post-edit AttributeError/ImportError/TypeError rate | time to first edit up with no evidence gain; reproduction loops; hit-cap up; scratch files in the patch | D.4; also report P(resolved given evidence) vs P(resolved given none) |
| **A4** Per-task budget | Budget block and the time cap, at 2 or 3 levels chosen in step 2 from the caps that pass the 12 h check (E.4). The whole curve comes from **one long-cap run re-graded at shorter caps** (CPU); **one real confirmation run** at the chosen cap | Yield per minute is concave; minutes beyond some cap buy less than lambda | one long run + one confirmation | Y(c), hit-cap, E[T](c), P(T > 12 h) | truncation curve and confirmation run disagree (the budget is stated in the task message, so behaviour may depend on it [S4]) | E.4: largest cap passing the 12 h test, then the knee of Y(c) |
| **A5** Optional investigator | Sub-agent block: read-only investigator invoked on demand when the root agent has made 15 tool calls without an edit (trigger independent of A1), versus none | A fresh context helps when the root window is cluttered | above A0 (extra tokens and time) | localization hit on tasks where the root agent was stuck, sub-agent calls, sub-agent max prompt tokens | any sub-agent context overflow (sub-agent sessions are not compacted [S6]); time up more than the yield gain; no gain on the stuck subset | D.4, evaluated on the stuck subset and on all tasks |
| **A6** (optional) Thinking on/off | Thinking setting, at fixed `max_output_tokens` | Thinking improves correctness per call but loses calls under a time cap; sources disagree on whether the budget is enforced [S5][S6] | about A0 | reasoning tokens per request, calls per task | calls per task halve with no outcome gain; single requests over 2 min | only if step 1 shows reasoning tokens are a large share of completion tokens |
| **A7** (optional) Output ceiling | `max_output_tokens` 4,096 vs 16,384 | A 32,768-token window leaves only 16,384 prompt tokens when the ceiling is 16,384, and the replica rejects a request whose prompt plus ceiling exceeds the window [S6]; a lower ceiling cuts tail latency and overflow | small | requests with prompt + ceiling > 32,768, p99 request latency, truncated edits | more truncated outputs, malformed edits | coordinate with Researcher 1 (runtime); count-based, may need no A/B |

### D.3 What the sample size can resolve `[D]`

`devset_tools.py power` simulates paired ablations: each task has a latent success probability (Beta with the given baseline and intra-task correlation ICC); arm B multiplies every task's odds by OR; per-task win or loss is which arm solved more seeds; exact sign test. Cells show the **screening rule** of D.4 (one-sided p <= 0.10 and at least 3 wins), with two-sided power at 0.05 in brackets. The OR=1 column is the false-promotion rate. 1,000 simulated experiments per cell, seed 0. Full tables (including the 0.40 and 0.60 baselines relevant to mechanism metrics) are in `design_calculations.md`.

| Regime | tasks n | OR=1 | OR=2 | OR=3 | OR=5 |
|---|---|---|---|---|---|
| Pessimistic: baseline 0.10, ICC 0.6, 1 seed | 22 | 0.002 (0.000) | 0.018 (0.000) | 0.038 (0.000) | 0.060 (0.003) |
| | 45 | 0.017 (0.002) | 0.101 (0.010) | 0.165 (0.032) | 0.334 (0.110) |
| | 58 | 0.034 (0.004) | 0.122 (0.027) | 0.214 (0.067) | 0.420 (0.160) |
| | 129 | 0.068 (0.007) | 0.334 (0.123) | 0.558 (0.279) | 0.843 (0.610) |
| Middle: baseline 0.10, ICC 0.3, 1 seed | 22 | 0.012 (0.000) | 0.076 (0.010) | 0.150 (0.022) | 0.321 (0.092) |
| | 45 | 0.053 (0.003) | 0.190 (0.056) | 0.361 (0.151) | 0.677 (0.401) |
| | 58 | 0.057 (0.009) | 0.249 (0.077) | 0.492 (0.225) | 0.804 (0.551) |
| | 129 | 0.059 (0.015) | 0.469 (0.232) | 0.829 (0.589) | 0.988 (0.930) |
| Optimistic: baseline 0.20, ICC 0.3, 3 seeds | 22 | 0.054 (0.009) | 0.367 (0.154) | 0.671 (0.406) | 0.928 (0.752) |
| | 45 | 0.071 (0.018) | 0.630 (0.368) | 0.940 (0.800) | 0.997 (0.983) |
| | 58 | 0.062 (0.011) | 0.736 (0.464) | 0.971 (0.877) | 1.000 (0.994) |
| | 129 | 0.089 (0.019) | 0.964 (0.838) | 1.000 (1.000) | 1.000 (1.000) |

How to read it. These are assumptions, not Gemma. They say that with 30 to 58 tasks only large effects are visible, and that which regime you are in matters more than anything else. **Choose the regime from data**: after step 3, count the A/A discordant tasks (tasks that flipped between A0 and A0') and pick the ICC for which the simulated "mean discordant tasks" at OR=1 matches it; then read n and seeds off the table. Do not plan on three seeds unless A/A shows tasks that really flip: seeds average out within-task randomness, they do not add tasks. A mechanism metric with a 40% to 60% base rate is better powered than resolve rate but still needs an odds ratio near 3 at n=45 when tasks are strongly correlated.

### D.4 Decision rules (written before any arm runs)

1. **Safety first.** An arm is dropped, or reworked as a budget question, if its context-overflow rate is above control's, if its hit-cap rate or its bootstrap P(T > 12 h) is above control's by more than noise, or if it introduces a new harness-error class.
2. **Outcome path (screening).** Paired one-sided exact sign test on `dev_resolved`, p <= 0.10 with at least 3 wins. Wins needed by number of losses `[C]`: 0 losses: 4 wins; 1: 6; 2: 7; 3: 9; 4: 10; 5: 12.
3. **Mechanism path** (when the outcome path cannot fire at this n). The arm targets a failure class that was at least 10% of runs in step 1, cuts that class by at least half with non-overlapping Wilson 80% intervals, and `dev_resolved` wins >= losses. This relies on prevalence, which a single arm measures well, rather than on a difference of two small outcome rates.
4. **Extend once.** If wins exceed losses but neither path fires at n=30, add 15 reserve tasks (n=45) and re-apply on all of them. No second extension.
5. **Drop** if wins <= losses at n=30 and the mechanism did not move.
6. **Finalists**: at most two arms plus A0. Run them with 3 seeds on the screening pool only if A/A showed tasks that flip; otherwise go straight to the lockbox.
7. **Lockbox is a veto, not a promotion test.** Apply the screening rule *against* the finalist (control beats finalist with one-sided p <= 0.10 and at least 3 losses). If it does not fire, the finalist may go to the leaderboard. Spend the lockbox once per finalist pair and log it.
8. **Leaderboard.** One submission per day [S4]; its standard error at about 58 tasks is about 0.03 to 0.04 `[C]`. Write down the expected score before submitting. Expect to need a net gain of five or six tasks (0.09 to 0.10 at 58 tasks) before a leaderboard difference can be told from noise.

### D.5 Which arm first

Step 1's largest failure class decides.

| Largest class in step 1 | First | Then |
|---|---|---|
| `agent_timeout_*` / high hit-cap | A4 (CPU re-grading, almost free) and the stopping rule of E.4 | A1 |
| `context_overflow` | not an ablation: send the request-level token log to Researcher 1; re-measure after the runtime fix; A7 if the ceiling is implicated | |
| `no_patch_other` (agent stopped or looped without a source edit) | A3 or A1 | A5 |
| `wrong_files` | A2, then A12; A5 on the stuck subset | A1 |
| `right_file_tests_fail`, `regression_p2p`, high `edit_without_verification` | A3 | A2 |
| high malformed tool calls | not an ablation: fix schema/prompt, verify by counts | |

Cost example: n=30, one seed, mean 5 realized minutes is 2.5 GPU-hours per arm (about 5 quota-hours at the reported 2x rate [S4]); eight arms would be about 20 GPU-hours, which is why only the ordered subset is run and why A4 is done on CPU.

### D.6 Running whole-agent evaluations in an eligible Kaggle environment

The real model, harness and verifier could not run in my sandbox (no GPU, no data, no network), so none of this was executed. The route that keeps the harness and verifier official:

1. Copy the official starter notebook [S8]. It is the host's own example of installing the harness from the wheelhouse dataset and serving the model with vLLM on the competition's 4xL4 machine with internet off; reproduce its demo run first (one or two tasks) so that you know the setup works.
2. Attach the competition data. Feed the evaluator only the task ids of the chosen pool (from `task_features.csv` and the split file), never the whole set.
3. Run the official local evaluator (`swegemma eval` [S4][S7]) with explicit caps in `eval_config.yaml`, compaction **on** at the scorer's interval, and the frozen sampling settings. Take the exact flags and output layout from `HARNESS_README.md`; I have only third-party descriptions of them.
4. Optional but needed for context-overflow and per-request cost: a logging proxy between the harness and vLLM that records prompt tokens, completion tokens, reasoning tokens and latency per request (F.4).
5. Run all arms of one comparison back to back in one session against one server; write results per task as they finish, so a cut session loses one task, not the run.
6. Export one flat row per task per arm per seed (Appendix A) and run `summarize`; re-grade patch snapshots on CPU for `budget`.
7. Fidelity limits to record, not fix: notebook runs use a subprocess sandbox and Python 3.12 while the scorer uses Python 3.13 [S4]; local default compaction is off [S6].

---

## E. 12-hour budget strategy

### E.1 The constraint and the knobs

T = S + sum over tasks of (setup_i + wall_i) must stay under 12 h [S2], where S is server start (reported up to 20 min, planning value 15 min [S5]) and wall_i = min(cap, time the agent takes to submit or give up). The only controls are global entries of `eval_config.yaml`: `max_time_minutes` (the cap c), `max_tool_calls`, `max_turns`, and `timeout_seconds`, the per-command limit that also caps the hidden-test run in grading [S5], so a value that is too low can fail a correct patch whose tests are slow. **There is no per-task knob.** Per-task adaptivity must live inside the agent's own stopping behaviour; the cap is only the safety net.

### E.2 Planning arithmetic `[C: budget-arith]`

Parameters are inputs, not measurements: S = 15 min, setup 0.1 min per task, margin 45 min. Reproduces the third-party figures of 10.9 h at a 5-minute cap and 11.9 h at 5.5 minutes for 125 tasks [S5].

| Cap (min) | Worst case, N=120 (h) | Worst case, N=125 (h) | Tasks allowed to hit the cap if the others average 3 min (N=120) | if they average 4 min |
|---|---|---|---|---|
| 5 | 10.45 | 10.88 | 144 (not binding) | 168 (not binding) |
| 6 | 12.45 | 12.96 | 96 | 84 |
| 8 | 16.45 | 17.12 | 57.6 | 42.0 |
| 10 | 20.45 | 21.29 | 41.1 | 28.0 |
| 15 | 30.45 | 31.71 | 24.0 | 15.3 |
| 30 | 60.45 | 62.96 | 10.7 | 6.5 |
| 60 | 120.45 | 125.46 | 5.1 | 3.0 |

Reported single runs, for context only (one run each, a one or two task difference is noise): leaderboard 0.06 at a 3.5-minute cap, 0.10 at 4.5, 0.08 at 5.0, and a 5.5-minute cap that exceeded 12 h [S4]; 0.08 at 4 minutes against 0.12 with no cap, the no-cap run being reported to have finished inside the limit, which implies that its agent ended most tasks itself [S5]. The pattern is that caps from 3.5 to 5 minutes are not the dominant driver of score, while self-termination decides whether a larger cap is safe.

### E.3 Measure these before choosing anything (step 1 and 2)

| Quantity | Symbol | Source |
|---|---|---|
| Fraction of tasks ending by the cap | f | `hit_cap` in the task log |
| Duration of tasks that end themselves | m | `duration_s` |
| Decode speed and per-request overhead on the scorer hardware | tokens/s, s per call | request-level log; compare with 25.5 and 0.6 [S6] |
| Setup time per task and server start | s, S | `setup_s`, notebook log |
| Time to first edit, time to first resolving snapshot | | trace timestamps and re-graded snapshots |
| Share of task time spent in requests longer than 60 s | | request-level log |

### E.4 Policy

**(a) Global cap c\*.** The largest c for which `budget` gives bootstrap P(T > 720 min) <= 1% and E[T] + 60 min <= 720, using at least 30 durations of the *final* agent policy; keep the margin large because private repositories can have slower test suites than the dev repos. **Until f is measured, use c <= 5 min**, the only region whose worst case fits at both N=120 and N=125. Never extrapolate to a cap larger than the one measured; `budget` refuses to.

**(b) Soft deadlines inside the agent**, in elapsed seconds, from measured quantiles of resolved tasks: D_edit = p90 of time to first edit; D_stop = p80 of time to the first snapshot that the verifier resolves. After D_edit without an edit, commit to the best current hypothesis and edit. After D_stop, apply (d). Check what `get_status` returns, and in which units, before wiring this up `[P]`.

**(c) Stopping rule for easy tasks.** Predicate S holds when: a source edit exists; the diff touches no test or config path; changed lines <= L_cap (p95 of `lines_changed_src` over healthy dev tasks, a prior on fix size taken from the dataset profile); and a test that exercises the changed code failed before the last edit and exits 0 after it, or the issue's own traceback no longer reproduces. **Adopt S only if** gain / saved < lambda, where gain = share of S-true tasks that were unresolved at the stop snapshot but resolved at the end, saved = mean minutes between S and the end of those runs, lambda = marginal resolved tasks per expected minute from the `budget` table. `budget --evidence-time-col evidence_time_s --evidence-resolved-col resolved_at_evidence` prints precision, time saved, and the counts of tasks where continuing helped or hurt. The economics: stop when the extra yield from continuing is worth less than what the saved minutes buy elsewhere.

**(d) Escalation rule for hard tasks.** After D_stop continue, up to c\*, only with a progress signal and no thrash signal. Progress: the failing test set or failure-message hash changed since the last check, or passing tests in the targeted file increased; or the diff changed in the last 5 calls and is non-empty; or a new source file was read in the last 5 calls. Thrash: the same command twice in a row with identical output hash; an edit-revert cycle (diff hash returns to an earlier value); five calls with no new file read and no new output hash. **Adopt only if** the conditional yield per minute of the progress group, measured from timelines after D_stop, is at least lambda. Otherwise stop at D_stop.

**(e) Per-request guard.** A single request can cost minutes at 25.5 tokens/s. Log it; if step 1 shows that long requests eat a large share of task time, the matrix arms A6 and A7 are the way to test a remedy.

### E.5 Task starvation, measured

The planner prints, for every candidate cap, the bootstrap P(T > limit) and the number of tasks that fit before the limit (`tasks that fit`). If overrun means whole-submission failure the relevant objective is the constrained one of E.4(a); if the hosts' partial-credit fix is live, the graceful objective printed in the same table (yield x tasks that fit) applies. State which one you assumed.

### E.6 Do not

Set every task to the maximum budget; use tool-call counts as a time proxy; extend the truncation curve beyond the measured cap; choose c\* from a single run without the bootstrap; or tune c\* on the lockbox.

---

## F. Failure taxonomy and per-task logging schema

### F.1 Two layers

The primary outcome class is mutually exclusive and comes from a fixed decision tree. Process flags are non-exclusive and co-occur with it; keep them separate, because a timeout can coexist with a verifier or dependency error and one label would hide that [S9].

Decision tree (first match wins; implemented in `summarize` as `classify`):

1. `resolved`
2. `context_overflow`: any request with prompt + max output tokens > 32,768, an HTTP 400 context error, or a "Sandbox execution error" caused by one
3. `verification_timeout`: Phase 2 pytest hit `timeout_seconds`
4. `agent_timeout_no_patch` / `agent_timeout_patch_failed`: loop ended by the time, call or turn cap, split by whether a source patch exists
5. `test_or_config_edit_only`: non-empty diff touching only tests or config
6. `no_patch_other`: no source change captured, not a timeout
7. `patch_not_applicable`: does not apply to a fresh snapshot
8. `wrong_files` (analysis-only; uses the reference): changed source files disjoint from the reference's
9. `regression_p2p`: target tests pass, rest of the suite fails
10. `right_file_tests_fail`: overlaps the reference files, target tests still fail
11. `patch_failed_unknown`: a patch exists and applies but no diagnostic field is available

### F.2 The listed failure modes and how each is measured

| Failure mode | Operational definition | Measured by | Needs |
|---|---|---|---|
| Wrong localization | final diff's source files (or changed symbols) disjoint from the reference's. **Analysis-only label**; the reference never reaches the agent | `loc_file_hit`, `loc_symbol_hit`; P(resolved given hit) and P(hit given not resolved) | reference patch, final diff |
| Edits with no executable evidence | a source edit exists and no test or reproduction command ran after the last edit (or ever) | `ran_test_after_edit`, `fail_to_pass_evidence`; P(resolved given flag) | trace timestamps |
| Malformed or overlarge patch | does not apply; changed lines above the p95 of reference size; more than 3 files; scratch or binary files; a changed `.py` file that fails `py_compile` | `patch_applies`, `patch_lines`, `scratch_files`, `py_compiles` | final diff, fresh snapshot |
| Test misuse | diff touches tests/config; deleted or skipped tests; `-k` expressions that exclude failing tests; edits to `conftest.py` | `touched_tests`, command regexes | diff, command log |
| Wrong API details | after an edit, command output contains AttributeError, ImportError, NameError, or TypeError about an unexpected argument, naming a symbol the agent introduced or called | count per task from output text | command outputs |
| Tool-schema misuse | calls to an undeclared tool name, missing or extra arguments, invalid JSON, `edit_file` rejects, "token limit" nudges, sessions ended by three turns without a tool call [S6] | `malformed_calls`, `edit_rejects`, `nudges`, `ended_by` | tool-call log |
| Timeouts | loop ended by cap; per-command timeouts; verification timeout, kept **separate** from agent timeouts | `ended_by`, `command_timeouts`, `verify_timeout` | harness errors |
| No patch submitted | two different things: no source change in the final diff, and a patch that exists but `submit_patch` was never called (the diff is captured anyway [S4]) | `non_empty_patch`, `touches_src`, `submitted` | final diff, tool log |
| Task starvation | run-level: tasks not finished before the limit | `budget` P(T > limit) and `tasks that fit` | durations |
| Context overflow (added) | see decision tree | `prompt_plus_ceiling_max`, `n_requests_over_window`; root vs sub-agent | request-level token log |
| Harness or environment errors (added) | missing test dependency, snapshot error | raw `error` string, always kept | harness output |

### F.3 Per-task record (JSON Lines, one object per task per arm per seed)

```json
{
 "schema_version": 1,
 "run": {"run_id": "", "arm": "A1", "seed": 0, "config_sha256": "", "prompt_sha256": "",
         "harness": {"swegemma": "", "adk_submission": "", "google_adk": "", "python": "", "pytest": ""},
         "hardware": "4xL4",
         "eval_config": {"max_time_minutes": 0, "max_tool_calls": 0, "max_turns": 0, "timeout_seconds": 0},
         "compaction": {"enabled": true, "token_threshold": 14336, "interval": 0},
         "sampling": {"temperature": 0.2, "top_p": 0.95, "top_k": 40, "max_output_tokens": 0, "thinking": "on|off", "thinking_budget": 0}},
 "task": {"task_id": "", "repo_short": "", "created_at": "", "pool": "screen|reserve|lockbox|train",
          "strata": {"n_src_files": 0, "lines_changed_src": 0, "issue_type_heuristic": ""}},
 "timing_s": {"setup": 0, "agent": 0, "verify": 0, "first_tool": 0, "first_edit": 0, "first_test_run": 0, "last_edit": 0, "submit": 0},
 "ended_by": "submit_patch|budget_time|budget_calls|budget_turns|no_tool_call_x3|context_overflow|harness_error|crash",
 "tokens": {"completion_total": 0, "reasoning_total": 0, "prompt_max": 0, "prompt_plus_ceiling_max": 0,
            "n_requests": 0, "n_requests_over_window": 0, "p99_request_s": 0, "n_compactions": 0,
            "sub_agent_prompt_max": 0},
 "tools": {"calls_total": 0, "by_tool": {}, "malformed_calls": 0, "edit_rejects": 0, "nudges": 0, "command_timeouts": 0},
 "process": {"repro_written": false, "repro_failed_before_edit": false, "test_runs": 0, "test_runs_after_last_edit": 0,
             "fail_to_pass_evidence": false, "files_read_before_first_edit": 0, "same_command_repeats_max": 0,
             "edit_revert_cycles": 0, "graph_calls": {"neighbors": 0, "subgraph": 0, "similar": 0}, "sub_agent_calls": 0,
             "confidence_ratings": [], "post_edit_api_errors": 0},
 "patch": {"non_empty_raw": false, "touches_src": false, "touches_tests_or_config": false, "scratch_files": [],
           "n_files": 0, "lines_added": 0, "lines_removed": 0, "applies_cleanly": false, "py_compiles": false,
           "sha256": "", "snapshots": [{"t_s": 0, "sha256": "", "exact": true}]},
 "verification": {"resolved": false, "pytest_exit": 0, "f2p_total": 0, "f2p_passed": 0, "p2p_failed": 0, "timed_out": false, "error": ""},
 "analysis_only": {"loc_file_hit": false, "loc_symbol_hit": false},
 "leak_audit": {"read_wheels_dir": false, "read_site_packages_target_pkg": false, "git_history_access": false},
 "classification": {"outcome_class": "", "process_flags": []}
}
```

`devset_tools.py summarize` and `budget` read the flat subset they need (aliases are listed in Appendix A). Extra columns for `budget`: `resolved_at_<seconds>` (patch snapshot re-graded at that elapsed time), `evidence_time_s`, `resolved_at_evidence`, `setup_s`.

### F.4 Instrumentation notes

- **Tokens and latency per request** need a thin logging proxy in front of the local vLLM server (or the server's own request log). The harness result files do not carry them as far as I can tell (`task_results.jsonl` fields reported: `duration_s`, `tool_calls`, `error` [S5]). Without this, context overflow and per-request cost cannot be measured.
- **Patch snapshots over time**: replay the trace's `edit_file`/`write_file` calls onto a fresh snapshot, or take `git diff` after every edit if the local harness lets you wrap tools. A `run_command` that edits files (`sed -i`, `git checkout`) breaks replay; mark such tasks `exact: false` and keep them out of the truncation curve.
- **Re-grading snapshots is CPU-only** with the official Phase-2 verifier (a few seconds per task for small repos [S4]). That is what makes A4 and the stopping-rule evaluation cheap.
- **Write the run adapter last.** After step 1, inspect one `task_results.jsonl` row and one trace, then write a 20 to 40 line script that maps them to the flat rows. I have not seen either file and did not guess their structure.
- **Record versions** in the run header (T8).

---

## G. Boundary between measured, proxy and proposed

| Item | Status | Where |
|---|---|---|
| Dataset schema, scoring rules, limits, hidden-set description | Reported by Kaggle page text, a mirror, and third parties; **not checked against the data or the harness** | A |
| Per-repository counts, median sizes, hint counts quoted from third parties | Third-party reports; used only as regression targets for `profile` | B.3 |
| Any statistic of the 129 tasks computed by me | **None. Not measured.** | B.3 "Measured here" is empty |
| Any Gemma or harness result | **None. Not measured.** | |
| `devset_tools.py` plumbing | Verified on synthetic fixtures; deterministic; says nothing about the competition | Appendix B |
| Power and false-promotion tables | Simulation under stated assumptions | D.3 |
| Worst-case hours, tasks allowed to hit the cap | Arithmetic from stated parameters | E.2 |
| Mention indicators, symbol overlap, `loc_*` hits | **Proxy** (dataset description or analysis-only labels), never a patch-success score | B, F.2 |
| `dev_resolved` from the official verifier | **Proxy** for the leaderboard (contamination, shift, different tasks) | D |
| Yield-vs-cap curves from re-graded snapshots | **Proxy** (counterfactual); one confirmation run required | E |
| Leaderboard score | The only official score; one submission per day; standard error about 0.03 to 0.04 | D.4 |
| Everything in D (arms), E.4 (policies), C.3 (probes), step 0d to 4 | **Proposed future experiments** | |

---

## Appendix A. Command and input reference

```bash
python devset_tools.py profile      --tasks tasks.jsonl [--snapshots-dir snapshots/] --out out/profile
python devset_tools.py audit-split  --tasks tasks.jsonl --splits split.json --out out/audit            # audit an existing split
python devset_tools.py audit-split  --tasks tasks.jsonl --make-split --sizes train=84,dev=22,heldout=23 \
                                    --seed 17 --heldout-policy random|newest --out out/split           # grouped, repo-stratified split
python devset_tools.py scan-bundle  --tasks tasks.jsonl --bundle submission.zip --exclude-ids-file train_ids.txt --out out/scan
python devset_tools.py summarize    --results rows.jsonl [more files] --features out/profile/task_features.csv \
                                    --baseline A0 --aa A0,A0b --out out/summary
python devset_tools.py budget       --results rows.jsonl --arm A0 --n-tasks 120 --measured-cap-min 10 --caps-min 3,4,5,6,8,10 \
                                    [--evidence-time-col evidence_time_s --evidence-resolved-col resolved_at_evidence] --out out/budget
python devset_tools.py budget-arith --n-tasks 120,125 --out out/arith
python devset_tools.py power        --n 22,45,58,129 --seeds 1,3 --p0 0.10,0.20 --icc 0.3,0.6 --odds-ratio 1,2,3,5 --sims 1000 --out out/power
python devset_tools.py selftest
```

`summarize` rows (JSONL or CSV): required `task_id` (alias `instance_id`), `arm`, `resolved`. Optional, used when present: `seed`, `repo`, `non_empty_patch`, `touches_src`, `patch_applies`, `touched_tests`, `submitted`, `hit_cap`, `context_overflow`, `verify_timeout`, `ran_test_after_edit`, `loc_file_hit`, `p2p_regressed`, `duration_s`, `tool_calls`, `turns`, `patch_lines`, `malformed_calls`, `error`, `failure_class`. `valid_patch` is derived as a source edit that applies cleanly. If `hit_cap` is absent it is inferred from an `error` text containing "timeout" or "exceeded". With one seed per task the paired test is the exact McNemar test; with several, per-task means are compared and ties dropped.

Design choices worth knowing: confidence intervals are percentile bootstraps over **tasks** (seeds of one task are averaged first), not over runs; Wilson intervals on pooled runs are printed for reference and are anti-conservative with repeated seeds; the bootstrap, the split and the simulations use fixed seeds; text similarity drops issue-template lines and very common terms, and if hard text-duplicate edges would create a group larger than 20% of the tasks they are demoted to soft edges and the report says so.

## Appendix B. Smoke-test record (synthetic data, plumbing only)

`python devset_tools.py selftest` builds a 40-task synthetic dataset and checks, with assertions: diff parsing on edge cases (a removed line that begins with `-- `, `\ No newline at end of file`, new, deleted and renamed files); Wilson interval, exact sign test and Bayesian screening quantity against hand-computed values; AST symbol mapping, including from a `.tgz` snapshot with a top-level directory prefix; detection of four planted leaks (same base commit, same changed symbol, near-duplicate issue text, same added test); the grouped split keeps hard groups together and hits the requested sizes; an existing split that separates a planted pair returns FAIL; the bundle scan reports a planted copied patch line and none for a clean bundle; paired statistics on a micro example (6 wins, 0 losses, p = 0.03125); budget monotonicity and the identity T_max = S + N (c + s); and **byte-identical outputs across two complete runs**. Final line printed: `SELFTEST OK (synthetic fixtures; ... no number printed here says anything about Gemma)`. The CLI wiring of every subcommand was also exercised from the shell. Neither check validates the real harness, the real data format, or any model behaviour. Tool version tested: `devset_tools.py`, 2,106 lines, sha256 starting `23465258097e3dd9`.

## Appendix C. What I need from you to close the open items

1. The header (first line keys) of your local `tasks.jsonl`, to settle `patch` vs `implementation_patch`.
2. The file that defines the 84/22/23 split, so step 0b can run as written.
3. One `task_results.jsonl` row and the top-level keys of one trace JSON from a local official-harness run (structure only), to finish the run adapter.
4. The `eval_config.yaml` of the 0.06 submission (the actual caps), and your weekly GPU quota, to turn D.1(7) and step 1 into hours.

Items for the other researchers, not diagnosed here: whether prompt + `max_output_tokens` can exceed the 32,768-token window in the current configuration (Researcher 1), and what the highest-scoring public agents do about stopping (Researcher 2).
