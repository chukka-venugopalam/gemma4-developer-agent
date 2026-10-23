# PUBLIC_AGENT_RESEARCH.md

**Gemma 4 Developer Agent Competition: public-agent and state-of-the-art research (Researcher 2)**

Compiled 2026-10-10 (session date). Base model under study: `gemma-4-31b-it-qat-w4a16-ct`.
Out of scope by design: our own archive/harness audit (Researcher 1), dev-set ablations (Researcher 3), our Kaggle Error.
Nothing below claims that any design guarantees 0.10. Every recommendation carries a falsifiable test (§F, §H).

---

## 0. Read this first

### 0.1 Bottom line

1. **The target has moved.** In the newest Kaggle leaderboard copy I could read (undated crawl, taken after 2026-09-28) rank 1 is 0.24, ranks 2–6 are 0.18, and ranks 7–38 are 0.17; 0.15 only starts at rank 39. On 2026-09-28 the top was 0.15 and 0.10 still sat inside the top 169 of 736 teams. Treat 0.10 as a floor, not the frontier (§A).
2. **Provenance ceiling (important).** I could not open any notebook source, notebook version history, forum thread, or the official `HARNESS_README` first-hand. Kaggle pages return only meta tags to my fetch tool, and this sandbox has no network or Kaggle CLI. What I have instead: Kaggle page text as returned by a search index; two independent third-party write-ups that downloaded the public ZIPs, hashed them and cited harness source lines; and several repos that measured harness behaviour on their own runs. **The 0.17–0.24 tier is a black box: no accessible code, so no verified architecture.** Everything said about it is marked unknown or hypothesis (§C, Appendix 1).
3. **What the four verifiable 0.10–0.12 public bundles share:** thinking OFF in all four; no LoRA in all four; no skills in the two bundles whose file lists were checked (Roman, Black Cat anchor); at most nine built-in tools; where documented (Roman, Black Cat) temperature 0.1–0.2 and output caps of 2,048–8,192 tokens; tiny bundles (3,277 B and 4,690 B where measured). Three of the four are *coder + read-only analyzer* wired as an `agent_tool` with `skip_summarization: true` (the shape reported for the official sample). The fourth (Parthenos, lean default) is a single agent (§B, §E).
4. **What they do not share:** per-task budgets (none / 4.5 / 5 / 8 min), analyzer tool sets, prompt text. No controlled ablation anywhere isolates one component. Negative controls exist: coder + analyzer at 0.06 (ns-0437 v1), a single agent with all nine tools at 0.05 (rlawoals0529 v0.1), thinking-on single agents at 0.05–0.06 (LogosTopos v2/v4). **Agent shape alone does not separate 0.06 from 0.12.**
5. **Likeliest drivers, ranked in §E:** (1) a per-task envelope that fits the 12-hour / ≈120-task cap and ≈25 tokens/s decode; (2) never triggering the hard-failure paths (context overflow → empty patch, undeclared tool name, `{brace}` crash, malformed calls); (3) thinking off plus explicit loop control; (4) a short, bounded analyzer handoff; (5) cheap reproduce-then-verify discipline. Retrieval sophistication ranks low; LoRA ranks lowest.
6. **Our candidate (as described to me: Adversarial SWE Hybrid) conflicts with the evidence at four points:** 60 min / 100 calls / 500 turns per task; `max_output_tokens: 16384`; thinking on with a 4,096-token budget; and unbounded sub-agent sessions. Exact replacements are in §F.
7. **Noise dominates small differences.** The public board is ≈58 tasks; one task = 0.017; same-agent run-to-run spread is ±2–2.5 tasks. Going 0.06 → 0.10 is +2 tasks (§A.5, §H).
8. **Retrieval is not the lever** under this harness: the official embeddings are weak, `search_similar_code` cannot embed free text, and a better local retriever (Hit@5 28/33) coincided with a leaderboard move of only 0.05 → 0.06 (§C L15, L16, L44).
9. **Five design decisions** (§F) and **sixteen do-not-copy items** (§G) follow, with a staged test plan (§H) that treats leaderboard submissions as integration checks rather than experiments.
10. **Cheapest ways to close the biggest unknowns** (Appendix 2): pull the 0.17–0.18 notebooks with the Kaggle CLI and hash them; refresh the leaderboard export; spend one daily submission re-scoring the byte-identical Roman ZIP to measure platform drift since 2026-09-30.

### 0.2 Evidence tiers and status labels

| Tier | Meaning | Examples |
|---|---|---|
| **P** | Primary text I read this session (Kaggle page text via a search index; third-party pages I fetched in full) | Kaggle leaderboard rows; Kaggle code listing; GitHub mirror of the official pages dated 2026-10-02 |
| **S** | A third party downloaded the artifact (ZIP, notebook, wheel), hashed or line-referenced it; I read their write-up, not the artifact | LogosTopos, Gosling-dude, damsolanke, Maukthik, emiliodavola, usp787, nawazdev |
| **T** | A claim relayed inside an S source, or a single-source measurement | "3P" forum reports, one-off replays |

| Status | Rule |
|---|---|
| **Confirmed** | A P text, or ≥2 independent S sources (different authors who inspected or ran separately) |
| **Strongly inferred** | A mechanism plus ≥1 measurement, or my own derivation from Confirmed facts (derivation shown) |
| **Unknown** | Not accessible, single T source, or sources conflict. Hypotheses are labelled as hypotheses |

Several sources quote the same Kaggle forum threads; I count a thread once however many repos repeat it.

---

## A. Leaderboard / SOTA snapshot (timestamped)

### A.1 What the board measures

- Score = share of hidden tasks whose validation tests pass after the submitted patch is applied (PASS/FAIL per task). [MIR]
- The test set is ≈120 tasks from private repositories, split ≈50/50 into public and private halves. The Kaggle leaderboard page itself says it is computed on about 50% of the test data and that final standings use the other 50%. [K-LB; U787; MIR]
- The whole run (all tasks, including sandbox setup, excluding patch validation) must finish within 12 hours. [K-OV; MIR]
- Main-track dates: entry/merger deadline 2026-11-25, final submission 2026-12-02; prizes $37k / $18k / $10k [U787]. One submission per day, two final selections [GD-PUB, relaying the Rules].

### A.2 Snapshots I could obtain

| # | Observation time | Source (tier) | Top of board | Notes |
|---|---|---|---|---|
| S1 | 2026-09-28 12:06 UTC (CSV export, 736 teams) | LT-CMP (S) | 0.15 ×1; 0.13 ×12; 0.12 ×60; 0.10 ×96; 0.08 ×140; 0.06 ×142; 0.05 ×92; 0.03 ×31; 0.01 ×43; 0.00 ×119 | 309 teams above 0.06; ≥0.10 = top 169 (23%). GD-PUB counted 738 teams (0.12 ×61, 0.08 ×141) slightly later |
| S2 | 2026-10-02 (mirror text) | MIR (P) | 0.24 (mirror says many teams tied at 0.15) | Dated by the mirror's author; its "tied at 0.15" remark does not match S3, so S3 may be later or the remark may be loose. The order of S2 and S3 is unknown |
| S3 | Undated crawl of the Kaggle leaderboard page, after S1 (search-index copy; "last" column shows 20h–10d) | K-LB (P, partial rows) | 0.24 ×1; 0.18 ×5; 0.17 ×32 (derived); 0.15 from rank 39 | Ranks 1–10 and 36–44 are visible. The board is sorted, and ranks 7 and 38 are both 0.17, so ranks 7–38 are all 0.17 (my derivation) |

**I could not obtain a dated 2026-10-10 export.** Refresh with the CLI command in Appendix 2. The community tracker (https://gemma4agent.kawchar.online; repo kawchar85/gemma4-agent-leaderboard) polls every 5 minutes but loads its data with JavaScript, so I could not read it.

### A.3 Visible rows of S3 (public team names as shown)

| Rank | Team | Score | Entries |
|---|---|---|---|
| 1 | Yurnero | 0.24 | 7 |
| 2 | Shan Yang | 0.18 | 11 |
| 3 | Wilmer E. Henao | 0.18 | 6 |
| 4 | Tsunato Nakai | 0.18 | 3 |
| 5 | noname | 0.18 | 9 |
| 6 | Haoyu Wang | 0.18 | 10 |
| 7 | AGENTS.md | 0.17 | 14 |
| 8 | Anh Nguyen Duong | 0.17 | 2 |
| 9 | Reiji Kobayashi | 0.17 | 5 |
| 10 | Kirill Labzin | 0.17 | 8 |
| 36–38 | Smart Manoj; HeartLumina; yiyu0716 | 0.17 | 13; 6; 9 |
| 39 | Makus (was rank 1 at 0.15 on 2026-09-28 with 2 entries) | 0.15 | 8 |
| 40–44 | sergiomalv; GopiPitchai; Gabriel; Baidalin Adilzhan [dsmlkz]; Ajeya | 0.15 | 12; 2; 11; 7; 8 |

### A.4 Public notebooks by recorded score (Kaggle code listing, undated copy)

"Updated Nd ago" labels are relative to an unknown crawl date, so I omit them. Only the recorded Score column counts; titles that advertise a score do not.

| Notebook | Recorded score | Votes | Note |
|---|---|---|---|
| Gemma 4 Agent: Budget-Fit Single Agent | **0.18** | 133 | Title says single agent. Code not accessible to me |
| Gemma 4 SuperAgent (copied with edits from Mizero Lucky Gall, the Pathfinder author) | 0.17 | 42 | Edits unknown |
| Gemma 4 Autonomous Developer Agent: Calibrated Sin… (copied with edits from Wilmer E. Henao) | 0.17 | 28 | Title truncated in my copy. The source author is rank 3 at 0.18 |
| Gemma + Gemini – The Ultimate Duo | 0.15 | 38 | Title suggests a non-Gemma model somewhere; the rules require the single Gemma model (§G) |
| Black Cat SWE Agent \| Pack Instinct | 0.12 | 140 | §B1, §D |
| GEMMA: EDA, Baseline for a start \| LB TOP 1 (Roman Rozen) | 0.12 | 218 | §B2 |
| Gemma 4 Baseline \| LB 0.24 | 0.13 | 0 | Title claims 0.24; recorded 0.13 |
| [0.10]: Gemma 4 Developer Agent Submission (nihilisticneuralnet) | 0.10 | 25 | §B5 |
| Gemma 4 \| Walkthrough & First Submission | 0.10 | 84 | Copied from a private notebook |
| GEMMA 4 developer agent EDA (copied from Roman Rozen) | 0.10 | 10 | Fork of the 0.12 bundle scores 0.10 |
| Gemma 4 \| Budget-Aware Coding Agent v2 | 0.10 | 18 | |
| Gemma 4: Measure Before You Tune | 0.10 | 17 | |
| Gemma Developer Agent: 0.13 Submission | 0.10 | 17 | Title claims 0.13; recorded 0.10 |
| Getting Started – Gemma 4 Developer Agent (host, ryanholbrook) | not scored | 1,021 | Official local-run recipe |

### A.5 What a score means in tasks (my derivation, strongly inferred)

The community inferred a 58-task public split from the rounding pattern (forum thread 743506, relayed by LT-CMP and GD-PUB; not host-confirmed). I re-checked it: with N = 58 and scores floored to two decimals, k tasks give floor(100·k/58)/100, i.e. the values below. The S1 histogram contains exactly these values and none of the unreachable ones (0.02, 0.04, 0.07, 0.09, 0.11, 0.14), and two independent teams state "7/58" and "3/58" for their own Kaggle results [U787].

| Score | 0.01 | 0.03 | 0.05 | 0.06 | 0.08 | 0.10 | 0.12 | 0.13 | 0.15 | 0.17 | 0.18 | 0.24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tasks (k of 58) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 14 |

- One task = 0.0172. Binomial 1σ at p = 0.12, n = 58 is ≈2.5 tasks (≈0.043). Measured same-artifact spread is similar: ±2.2 tasks per run on 70 local tasks [U787]; one Roman reproduction scored 0.08 against the author's 0.12 [LT-CMP, T].
- Consequences: 0.06 → 0.10 is **+2 tasks**; 0.12 vs 0.10 is **one task**; differences below ≈3 tasks (0.05) are not evidence on a single leaderboard run. The top public scores are also winner's-curse inflated (many submissions, one public half); the final score uses the other half.

---

## B. The five most informative public submissions / versions

Why these five: each either has third-party-verified bytes, documents a version-to-version change, or bounds what the 0.17–0.24 tier could be. None of the Kaggle notebook sources was opened by me (§0.1 item 2).

### B1. Black Cat SWE Agent \| Pack Instinct (lucifer19)
URL: https://www.kaggle.com/code/lucifer19/black-cat-swe-agent-pack-instinct

- **Score trail.** Author's own table (relayed): single agent 4 min / 24 calls = 0.08 → + analyzer 5 min / 40 calls = 0.10; a temperature-1.0 variant = 0.06 [GD-PUB, T]. The task brief reports V10 at 0.12; the Kaggle listing shows 0.12.
- **Verified by a third party (S).** The notebook's `anchor_submission.zip` (4,690 bytes, SHA256 `18b20200ba4a42f99ecaa0c889664ead4b78848835317bc114f4e4095f759916`, equal to the notebook's own ANCHOR_SHA256): six files including `eval_config.yaml`; root = nine built-in tools + `code_analyzer`; analyzer = run_command, read_file, get_code_neighbors, get_code_subgraph; thinking off; root T 0.2, out 4,096; analyzer T 0.1, out 2,048; 5 min / 40 calls / 100 turns / 120 s [LT-ARCH §4, LT-CMP]. The notebook's 2026-09-28 *challenger* code builds a different bundle (8 min / 100 calls / 150 turns / 300 s, root out 8,192) with no recorded score.
- **Why it matters.** It is the only public line with a version table, the only prompt set built around *tool failure* (empty searches, repeated identical calls, `python3 -c` one-liners, log tails), and the only inspected bundle documented as injecting the issue via ADK state (`{problem_description?}`) instead of making the main agent retype it (Roman retransmits it in the request; Pathfinder and Parthenos were not inspected at that level). The author reports that thinking-off Gemma repeats the same call 10–80 times and that an empty `git grep` result triggers loops [GD-PUB, T].
- **Unknown.** Bytes and config of V10; what changed between anchor and V10; the claimed 209-run lab.

### B2. GEMMA: EDA, Baseline for a start \| LB TOP 1 (Roman Rozen)
URL: https://www.kaggle.com/code/romanrozen/gemma-eda-baseline-for-a-start-lb-top-1

- Recorded 0.12; 218 votes. Third-party-verified ZIP: 3,277 bytes, SHA256 `f3534769cd8c7761b8ae83722b0f2fd381c0349587a10e84bd63e0554a4a7aa4`, five files (`agent.yaml`, `configs/sampling.yaml`, `prompts/system.md`, `prompts/analyzer.md`, `sub_agents/code_analyzer.yaml`); coder `swe_coder` (six base tools + `code_analyzer`), analyzer (run_command, read_file, search_similar_code, get_code_neighbors, get_code_subgraph); T 0.2, top_p 0.95, top_k 40, out 8,192; `include_thoughts: false` (the 4,096 `thinking_budget` in the file is inert); **no `eval_config.yaml`** [LT-ARCH §3, §8].
- **Why it matters.** It is the de facto reference bundle and the most forked: one fork records 0.10; one reproduction reports 0.08 after 14.5 hours (thread 743140, relayed [LT-CMP], T). That spread is the best available picture of reproducibility.
- **Unknown.** Whether the downloaded ZIP is byte-identical to the scored run (LT notes there is no strict binding).

### B3. Pathfinder (mizeroluckygall) and its "Gemma 4 SuperAgent" fork
URL: https://www.kaggle.com/code/mizeroluckygall/pathfinder-gemma-4-agent-eda-baseline

- Pathfinder default: coder + analyzer, no LoRA, no eval_config, thinking off, "complete issue" and budget checks; recorded 0.12 (rank 40 at the time). Its v1 scored 0.08 (author-reported [LT-CMP]); a third-party note attributes a hard 4-minute per-task cap to that run, relayed from the Black Cat notebook [GD-PUB, T]. The notebook "Gemma 4 SuperAgent", copied with edits from the same author, records **0.17** [K-CODE].
- **Why it matters.** The only visible lineage that moved by ≈3 tasks through edits (0.08 → 0.12 → 0.17), and a direct test of whether small edits or platform drift explain the 0.17 cluster. The edits are unread (§0.1 item 2).

### B4. Gemma 4 Agent: Budget-Fit Single Agent
Slug unknown (not exposed in the text I could retrieve); listed in K-CODE.

- Recorded 0.18, 133 votes. The title says single agent and budget-fit. Nothing else is verified.
- **Why it matters.** It is the highest-scoring public notebook visible to me and it is described as a single agent. If the title is accurate it undercuts "coder + analyzer is necessary" and supports "envelope first". It is the first notebook to pull (Appendix 2).

### B5. [0.10] Gemma 4 Developer Agent Submission (nihilisticneuralnet; handle Gemminem/Parthenos)
URL: https://www.kaggle.com/code/nihilisticneuralnet/0-10-gemma-4-developer-agent-submission

- Third-party inspection: default bundle is a **lean single agent**, nine built-in tools, four files, 4.5 min / 40 calls / 100 turns / 60 s, thinking off; its experiment card marks the candidate `not_evaluated` and the 0.10 as a *previous* user-reported score [LT-CMP, LT-ARCH §12]. An earlier version was described as coder + localizer + verifier, T 0.15, 4.5 min [GD-PUB].
- **Why it matters.** 0.10 has been reached by both single- and multi-agent shapes, and it is a live example of a score badge bound to a different version than the code you download.

### B6. Evidence that is not a notebook but quantifies effects

- **usp787 (a main-track team that reports Kaggle results of 7/58 and 8/58 for its own agent; agent repo returns 404):** thinking on vs off, run-to-run noise, context-overflow losses, tool audits, as of 2026-10-07 [U787].
- **LogosTopos, ns-0437, rlawoals0529:** 0.05–0.06 controls with different shapes [LT-README, NS, RL].
- **nawazdev (FaultLines):** a 16-task official-harness pilot with labelled failures [FL].
---

## C. Claim-by-claim source ledger

### C.0 Source key (all URLs retrieved or returned by search this session)

| Code | Source | URL | Date / version | Tier |
|---|---|---|---|---|
| K-LB | Kaggle leaderboard page (search-index copy) | https://www.kaggle.com/competitions/gemma-4-developer-agent/leaderboard | undated crawl, after 2026-09-28 | P (partial rows) |
| K-CODE | Kaggle Code tab sorted by score (search-index copy) | https://www.kaggle.com/competitions/gemma-4-developer-agent/code?competitionId=149921&sortBy=scoreDescending&excludeNonAccessedDatasources=true | undated crawl, relative "updated" labels | P (partial) |
| K-OV | Kaggle Overview page (search-index excerpt) | https://www.kaggle.com/competitions/gemma-4-developer-agent | crawl labelled "8 days ago" at retrieval | P (excerpt) |
| MIR | Mirror of Overview/Data/Rules plus snapshot box | https://github.com/sweeden-ttu/developer-agent | states 2026-10-02 | P (third-party mirror) |
| LT-README | LogosTopos repo README | https://github.com/LogosTopos/gemma-4-developer-agent | status 2026-09-28 | S |
| LT-CMP | LogosTopos public-baseline comparison | https://github.com/LogosTopos/gemma-4-developer-agent/blob/main/analysis/2026-09-28-public-baselines/comparison.md | queried 2026-09-28 12:06–12:12 UTC via Kaggle CLI | S |
| LT-ARCH | LogosTopos architecture study (ADK 1.36.1, adk_submission 0.2.11, swegemma 0.2.7 line references) | https://github.com/LogosTopos/gemma-4-developer-agent/blob/main/docs/research/2026-09-28-agent-architecture.md | 2026-09-28 | S |
| GD-README, GD-PUB | Gosling-dude README and `docs/public_research.md` | https://github.com/Gosling-dude/gemma4-developer-agent ; …/blob/main/docs/public_research.md | snapshot 2026-09-28 | S/T (reads notebook sources via Kaggle's public API; own agent never run on real Gemma) |
| DK | damsolanke scorer-replica kit | https://github.com/damsolanke/gemma4-swe-kit | undated; refers to the 2026-09-30 harness | S |
| MK | Maukthik design notes ("verified against swegemma 0.2.7, adk-submission 0.2.11, google-adk 1.36.1") | https://github.com/Maukthik/gemma4 | undated | S |
| ED56 | emiliodavola PR #56: organizer forum findings | https://github.com/emiliodavola/kaggle-gemma-agent/pull/56 | merged 2026-10-04 | S (forum threads read via Kaggle CLI, per its text) |
| ED73 | emiliodavola issue #73 / PR #74 / issue #86 (local run audit, harness notes) | https://github.com/emiliodavola/kaggle-gemma-agent/issues/73 ; …/pull/74 ; …/issues/86 | ≈2026-10-06 to 2026-10-08 (from relative ages) | S |
| U787 | usp787 paper-track repo (forum audits, thinking on/off, noise) | https://github.com/usp787/Gemma4_paper_track | state 2026-10-07/08 | S |
| FL | nawazdev FaultLines (16-task official-harness pilot) | https://github.com/nawazdev/faultlines | pilot 2026-09-29, RQ4 2026-10-04 | S |
| HI32 | mangeshraut712/Hindai PR #32 (official compiler contract) | https://github.com/mangeshraut712/Hindai/pull/32 | 2026-09-28 | S |
| NS, RL, BS | ns-0437 lab; rlawoals0529 JAgent; bansal1600 notes | https://github.com/ns-0437/gemma4-agent-lab ; https://github.com/rlawoals0529/gemma-4-developer-agent ; https://github.com/bansal1600/kaggle-finetune-gemma | undated | T (self-reported scores) |
| Forum | Kaggle discussion threads cited by the sources above (not read first-hand) | https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/ + ID: 743063, 743663, 743964, 743573, 743683, 743140, 743506, 743973, 742911, 744040, 744577, 745731, 745998, 744941 | 2026-09-24 to 2026-10-07 | T via S |
| Notebooks | Roman, Pathfinder, Black Cat, Parthenos, official starter | see §B; starter: https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent | versions not retrievable | not read by me |

### C.1 Rules and harness mechanics

| ID | Claim (paraphrased) | Status | Sources | What was verified, by whom, and caveats |
|---|---|---|---|---|
| L01 | Score = share of tasks whose validation tests pass (PASS/FAIL per task) | Confirmed | MIR | Mirror text read by me; Kaggle's own page not directly retrievable |
| L02 | 12-hour limit covers patch submission for all tasks, including sandbox setup, excluding patch validation | Confirmed | K-OV, MIR | Excerpt of the Kaggle page and the mirror agree |
| L03 | ≈120 hidden tasks from private repos; the leaderboard uses ≈50% of them, final standings the other 50% | Confirmed | K-LB text, U787, MIR | Leaderboard page states the 50% rule |
| L04 | The public half is 58 tasks | Strongly inferred | LT-CMP, GD-PUB (thread 743506); U787 ("7/58", "3/58"); my re-derivation (§A.5) | Not host-confirmed. Histogram of 736 teams fits floor(100k/58) exactly |
| L05 | Only `gemma-4-31b-it-qat-w4a16-ct` may be used, for every agent and sub-agent | Confirmed | MIR, HI32 | Compiler check reported in HI32 |
| L06 | Tool registry is closed: nine built-ins plus `agent_tool`; unknown names fail compile; skills load via `skills:` paths; ZIP extensions limited to .yaml .yml .md .txt .py .json .safetensors (no .sh) | Confirmed | HI32, LT-ARCH §9, MK | HI32 ran the real compiler locally (adk_submission 0.2.11 + google-adk 1.36.1) |
| L07 | Per-task limits come only from `eval_config.yaml` (four fields: timeout_seconds, max_tool_calls, max_time_minutes, max_turns); a missing field means no limit; tasks run sequentially; overrunning 12 h currently errors the submission (planned change: unfinished tasks score 0) | Confirmed | GD-PUB (host thread 743063), ED56 §10.3, MK, DK | Two independent summaries of host replies. I did not read the thread |
| L08 | The scorer does not support parallel model calls; multi-agent gets no speed-up | Confirmed | LT-CMP (host reply 743964, 2026-09-28 10:32 UTC) | Single relay of one host reply; consistent with L07 sequential execution |
| L09 | Any request with prompt tokens + `max_tokens` above 32,768 gets HTTP 400, which the harness turns into "Sandbox execution error" and an empty patch (an earlier `submit_patch` is discarded) | Strongly inferred | DK (mechanism, 33 overflow requests in one 12-task run, a scorer-stack run lost a task at 28,673 + 4,096 prompt+output), U787 (context overflow discards the working patch on 3–4 of 70 tasks per run) | Two independent measurements; scorer-stack case is one task |
| L10 | The main session is compacted at ≈14,336 tokens; the compaction interval parameter is ambiguous (5 in the README, 15 in the host notebook). The summary keeps only text parts (tool calls, tool results, sub-agent answers dropped); sub-agent sessions are never compacted | Threshold: Confirmed (the scorer compacts). "Text parts only" and "sub-agent never compacted": Unknown (single source). **Conflict:** MK states there is no compaction inside a task, most likely reading the local `swegemma eval` default, which DK says leaves compaction off | DK; ED56 §10.1 (states ≈14,336 as the effective context); MK (conflicting) | A prompt of 28,673 tokens (L09) shows prompts can far exceed 14,336 between compactions |
| L11 | In adk_submission 0.2.11 (`resolvers/generation.py`, ≈lines 60–118) `include_thoughts: false` or `thinking_level: none` becomes `enable_thinking=false`; as of 2026-09-28 `thinking_budget` was not forwarded | Confirmed (for 0.2.11) | LT-ARCH §8 (line references), MK, GD-README | Three authors, same wheel. Scorer-side version on any later date not verified |
| L12 | Since the 2026-09-30 harness: tool results arrive as one-level JSON; `edit_file` retries without escapes; `thinking_budget` and `seed` are now sent and the budget is a hard cap (vLLM forces the end of thought) | Confirmed | DK, ED56 §10.2 | Two sources; date from both |
| L13 | Thoughts were dropped between tool calls (fixed, no rescore) | Unknown | ED56 §10.2 only | Single source; matters for thinking-on scores recorded before the fix |
| L14 | LoRA adapters were silently zeroed in the scorer's vLLM until a fix (v23); high-rank adapters shrink KV cache (rank-64 report ≈7,600-token effective context); adapters slow decode 8–21% | Confirmed | ED56 §10.1/§10.5, GD-PUB (threads 743213/743508), U787 | Three authors |
| L15 | `search_similar_code` cannot embed free text: it only looks up a stored vector by node id or node source; free-text queries returned nothing in >400 calls; its output was unbounded (host promised a cap); `get_code_neighbors` matches exact ids only, no edge direction, alphabetical, cut at 50 | Confirmed | U787 (threads 745731, 744577), GD-README ("symbol names, not sentences"), LT-ARCH §3 | Three authors, matching the brief's warning |
| L16 | Official embeddings are weak: gold file in top 10 for 35/129 tasks vs 67/129 for plain grep; TF-IDF top-10 hit 52% vs embeddings 9%; graphs have no `async def` nodes, no module nodes, one edge type (`calls`); released graphs hold 14–21% of runtime call pairs | Confirmed | U787 (threads 744040, 745731, 742911), GD-PUB (woldywei benchmark: file recall@1 TF-IDF 0.21 vs embedding 0.05) | Two authors, different measurements |
| L17 | Public dev set = 129 tasks (fastapi 67, rich 48, requests 13, httpx 1); hidden tasks come from private repos; the host says no private task touches an async function (≤1.8% of functions) | Confirmed | U787 (thread 745998), MIR | |
| L18 | Some public dev tasks are unsound offline (109–119 of 129 sound): missing test deps, py3.13 SSL strictness | Confirmed (range) | U787 (109), GD-PUB (119), ED56 §10.4 | Relevant to local evaluation, not to the hidden set |
| L19 | A well-formed call to an undeclared tool name makes ADK raise and the task loses its patch (host: graceful handling planned); a `{identifier}` token in an instruction raises KeyError and crashes every task | Undeclared tool: Confirmed. Brace crash: Strongly inferred | DK, ED56 §10.2 (undeclared tool); MK (validator rule and ADK instruction templating) | The brace rule rests on MK's reading of ADK templating and its own validator; not independently reproduced |
| L20 | AgentTool semantics (ADK 1.36.1): the sub-agent sees only a `request` string; parent state (minus `_adk*`) is copied in; the harness writes `problem_description` into state, so `{problem_description?}` expands to the full issue; `skip_summarization: true` ends the invocation and the harness continues with a nudge (`max_nudges=3` counts consecutive nudges, reset by tool calls); sub-agent tools share the task budget | Strongly inferred | LT-ARCH §5–6 (wheel line references) | One careful reader; not re-read by me |
| L21 | The official sample is coder + analyzer via `agent_tool` with `skip_summarization: true`; its `eval_config.yaml` (1 min / 10 calls) explains ≈0 early scores | Shape: Strongly inferred. 1 min / 10 calls claim: Unknown | HI32 (compiler note on the official `sample_submission/agent.yaml`); consistent with the `sub_agents/code_analyzer.yaml` naming in LT-ARCH §3–4; MK (single source for 1 min / 10 calls) | The sample itself was not read by me |

### C.2 Public agents and versions

| ID | Claim | Status | Sources | Verification and caveats |
|---|---|---|---|---|
| L22 | Roman ZIP: 5 files, 3,277 B, SHA256 `f3534769…4a7aa4`; coder + analyzer; T 0.2/top_p 0.95/top_k 40/out 8,192; thinking off; no eval_config; prompt = analyzer first with full issue → verify → small repro → small edits → compile/tests → diff → submit | Confirmed (third-party artifact inspection) | LT-CMP, LT-ARCH §3, §8, GD-PUB (grep-first, no per-task limit) | Two authors; not re-hashed by me; ZIP-to-score binding not proven |
| L23 | Black Cat anchor ZIP: 6 files, 4,690 B, SHA256 `18b20200…f759916`, equals the notebook's ANCHOR_SHA256; 5 / 40 / 100 / 120 s; root out 4,096 (T 0.2), analyzer out 2,048 (T 0.1); thinking off; no LoRA/skills | Confirmed (third-party) | LT-CMP, LT-ARCH §4 | Score 0.10 is author-declared |
| L24 | Black Cat 2026-09-28 challenger code: 8 / 100 / 150 / 300 s, root out 8,192, new prompt rules; score None. Author table: single 4 min/24 calls 0.08 → +analyzer 5 min/40 calls 0.10; T 1.0 variant 0.06; "209 official-harness runs" | Challenger config: Confirmed. Author table and 209 runs: Unknown (single relay of author prose) | LT-ARCH §4 (challenger); GD-PUB (table) | V10 bytes unknown |
| L25 | Pathfinder: coder + analyzer, no LoRA, no eval_config, thinking off; v1 = 0.08 (self-reported; a relay attributes a hard 4-min cap) | Confirmed (config); reported (v1 score) | LT-CMP, GD-PUB | |
| L26 | Parthenos default = lean single agent, 9 tools, 4 files, 4.5 min/40/100/60 s, thinking off, `not_evaluated`; the 0.10 belongs to an earlier version | Confirmed | LT-CMP, LT-ARCH §12; GD-PUB (earlier multi-agent shape) | Different dates describe different versions |
| L27 | Budget-Fit Single Agent 0.18; SuperAgent (Pathfinder fork) 0.17; Calibrated Sin… (fork of the rank-3 team's notebook) 0.17; architecture and edits | Scores: Confirmed. Architecture: **Unknown** | K-CODE | No code access |
| L28 | Reproducibility: a Roman fork scored 0.08 after 14.5 h (thread 743140); another fork records 0.10 | Unknown/T | LT-CMP; K-CODE | No hashes or per-task results |
| L29 | Low controls: ns-0437 v1 coder + analyzer 0.06 and v2 (direct search, optional analyzer) 0.06; rlawoals0529 single agent with nine tools 0.05; "Super Basic" minimal single agent 0.08 and a starter kit with thinking on and 16k tokens 0.05 (both relayed by GD-PUB); LogosTopos v4 0.06 (single agent + deterministic context skill; thinking on, out 8,192, 4.5 min / 40 calls / 64 turns / 60 s) and v2 0.05 (thinking low, out 3,072, 3 min / 24 calls / 32 turns / 45 s) | Reported (self-declared scores) | NS, RL, GD-PUB, LT-README, LT-ARCH §2 | Different dates and settings; not controlled |

### C.3 Leaderboard, noise, cadence

| ID | Claim | Status | Sources | Notes |
|---|---|---|---|---|
| L30 | Distribution on 2026-09-28 12:06 UTC (§A.2 S1) | Confirmed | LT-CMP, GD-PUB | Two exports within 1–2 teams per bucket |
| L31 | Later snapshots: 0.24 top by 2026-10-02 (mirror); an undated copy (after 2026-09-28) with 0.18 ×5 and 0.17 ×32 | Confirmed (partial) | MIR, K-LB | Undated crawl is the weakest link; refresh |
| L32 | Titles can contradict recorded scores ("LB 0.24" → 0.13; "0.13 Submission" → 0.10; Parthenos 0.10 badge vs lean default) | Confirmed | K-CODE, LT-CMP | |
| L33 | Score ↔ task-count mapping (§A.5) | Strongly inferred | derivation | |
| L34 | Local dev resolution rates do not predict the leaderboard: the same zip scored 25/70 locally and 7/58 on Kaggle; another team's 48 rich tasks resolved 29/48 locally | Confirmed | U787, ED73 | |
| L35 | Run-to-run noise on 70 local tasks: 16 always solved, 40 never, 14 flip (≈±2.2 tasks per run) | Reported | U787 | One team; three runs |
| L36 | One submission per day, two final selections; scoring takes roughly 6–10 h; 4×L4 notebook sessions queue 4–9+ h; host: patch validation (≈2 h) is excluded from the 12 h and a no-patch run takes ≈10 min in total | Reported | GD-PUB (Rules/HOST threads 743663, 743600/743901), BS | Setup overhead per task is therefore small (≈5 s average if the 10 min figure holds) |

### C.4 Measured effects (third-party)

| ID | Claim | Status | Sources | Caveats |
|---|---|---|---|---|
| L37 | Scorer cost per call ≈ 0.6 s + completion tokens / 25.5 tok/s on 4×L4; a base-model decode of 28.4 tok/s was measured on another stack | Strongly inferred | DK, U787 | DK's figure is slightly pessimistic (three arms shared one server) |
| L38 | Thinking on vs off on one team's agent: local 25/70 vs 19/70; Kaggle 7/58 vs 3/58; with thinking on, thinking takes 65–71% of agent time. The same team's second thinking-on run scored 20/70, so the local gap can shrink to one task. Against it: every verified public ≥0.10 bundle runs thinking off; a thinking-budget-256 arm solved 7/12 vs 9/12 with thinking off | **Conflicting** | U787; LT-CMP; DK | Single runs, ±2.2 tasks; harness changed on 2026-09-30 |
| L39 | Thinking off ⇒ more loops and malformed calls: repeat-identical-call share 50% vs 9%; malformed 24% vs 2.2%; after one malformed call the next is malformed 92% vs 47% | Confirmed | U787, GD-PUB (Black Cat text: 10–80 repeats) | Two independent teams |
| L40 | Code-literal shell command examples in prompts get emitted as tool names: malformed names 31% vs 5% when rewritten as prose bound to `run_command` | Unknown (single source) | DK | Local Ollama/MLX replays, 96 samples each arm, not the scorer |
| L41 | Official-harness 16-task pilot: tool-call syntax valid in 518 of 520 turns; argument encoding, exact loops and the 50-turn budget sank most runs; a prompt-only addendum raised submitted patches from 4 to 11 of 16 (p = 0.04) but resolutions only from 2 to 3 | Reported | FL | A non-empty patch is necessary, not sufficient |
| L42 | Local audit of 48 rich tasks: 9 of 19 failures were process failures (6 session timeouts, 2 budget exhaustions, 1 no submission); failing tasks used ≈2× the wall time of passing ones; 26 of 46 submitted patches carried scratch files | Reported | ED73 | Local, not hidden tasks |
| L43 | Budget sensitivity: 4-minute caps appear in both 0.08 results (Black Cat single agent; Pathfinder v1); 4.5–5 min / 40 calls appears in 0.10; a 12-min/task version overran 12 h (3P) | Reported | GD-PUB, LT-CMP | Not controlled: caps changed with other settings |
| L44 | Retrieval: a deterministic hybrid retriever raised local validation Hit@5 from 26/33 (v3) to 28/33 (v4); the leaderboard moved 0.05 (v2) → 0.06 (v4) with prompt, tool and budget changes bundled in | Reported | LT-ARCH §2 | Hit@5 is not repair success; not a single-variable test |
| L45 | Date confounds: 09-27 LoRA fix; 09-28 host replies; 09-30 harness change (L12); scores recorded before/after are not like-for-like for thinking-on or edit-heavy agents | Strongly inferred | LT-CMP, ED56, DK | Why a byte-identical re-score is valuable (§H.7) |


---

## D. Score / version evolution of the strongest accessible agent

**Strongest accessible = Black Cat** (0.12; its anchor bundle was downloaded and hashed by a third party). The strongest *visible* entries (Budget-Fit 0.18, the 0.17 forks, rank-1 0.24) have no accessible code, so no evolution can be traced for them.
Observed facts and inference are separated in each row. Public-score variation is not a controlled ablation (§A.5).

### D.1 Black Cat

| Step | Version (as far as it can be identified) | What changed (observed unless marked) | Score | Evidence | Confounds / reading |
|---|---|---|---|---|---|
| 1 | "single agent" | One agent, 4 min / 24 calls (author table) | 0.08 | T: author text relayed by GD-PUB | First row; 5 tasks |
| 2 | "+ analyzer" = anchor bundle (SHA256 `18b20200…f759916`) | Added `code_analyzer` **and** raised the budget to 5 min / 40 calls / 100 turns / 120 s; root out 4,096, analyzer out 2,048, thinking off (bytes verified by LT) | 0.10, author-declared; the manifest binds it to this hash | S for bytes, T for score | Two changes at once (structure and budget). +1 task, inside noise |
| 3 | "T 1.0 variant" | Temperature 0.2 → 1.0 (author table) | 0.06 | T | Single change by the author's account, −2 tasks vs step 2: suggests temperature matters, but one run |
| 4 | "challenger" (notebook code on 2026-09-28) | Budget 8 min / 100 calls / 150 turns / 300 s; root out 8,192; prompt adds explicit `NO MATCHES` for empty searches, no repeated identical calls, ≤2 repro calls, no multi-statement `python3 -c` | none recorded (`challenger_score = None`) | S (config read from notebook code) | Cannot be credited with any score. 8 min × 120 tasks = 16 h if every task used its cap (L07) |
| 5 | V10 (public page) | Unknown | **0.12** (public page and code listing) | P for the score only; code unread | Several versions between steps 2 and 5 are invisible; harness changed on 2026-09-30 (L12); +1 task over the anchor |

What this table can support: the author's own step-1 → step-2 contrast is the only controlled-looking comparison and it changes two things. The direction of travel (more budget, failure-mode rules in the prompt) coincides with the best public version, but no step in the table is distinguishable from ±2.5 tasks of noise by itself.
What it cannot support: any claim that the analyzer, the failure rules, or the budget *caused* 0.12.

### D.2 Other lineages visible in public data

| Lineage | Observation | Score | Source | Reading |
|---|---|---|---|---|
| Roman | Original bundle (3,277 B) | 0.12 | LT-CMP | Reference point |
| Roman | Fork "GEMMA 4 developer agent EDA" | 0.10 | K-CODE | One task below the original |
| Roman | A participant's direct fork reported after 14.5 h (thread 743140) | 0.08 | LT-CMP (T) | Score and wall-time spread for one bundle; settings of that run unknown |
| Pathfinder | v1 (author-reported; a relay attributes a hard 4-min cap) | 0.08 | LT-CMP, GD-PUB | Tight caps probably cost tasks; not controlled |
| Pathfinder | Default coder + analyzer, thinking off | 0.12 | LT-CMP | +2 tasks after v1 |
| Pathfinder | "Gemma 4 SuperAgent" fork | 0.17 | K-CODE | +3 tasks after the default; edits unread; date confound (§D.3) |
| Parthenos | Earlier coder + localizer + verifier, T 0.15, 4.5 min | 0.10 | GD-PUB | Multi-agent at 0.10 |
| Parthenos | Current default lean single agent | not evaluated | LT-CMP | Same author, different shape, no score |
| Field | Makus: rank 1 at 0.15 with 2 entries on 09-28; rank 39 at 0.15 with 8 entries later | 0.15 | LT-CMP, K-LB | The field moved up by ≈2–3 tasks while this entry stood still |

### D.3 Platform events that confound any version comparison

| Date (UTC) | Event | Source | Why it matters |
|---|---|---|---|
| 2026-09-27 | LoRA loading fix applied (host reply of 09-28 says the day before) | LT-CMP (thread 743964) | Adapter-based results from before are not like-for-like |
| 2026-09-28 10:32 | Host: 12-h overrun handling not fixed; no parallel model calls; use `eval_config` for per-task budgets | LT-CMP | |
| 2026-09-28 12:06 | Leaderboard export S1, top 0.15 | LT-CMP | Last view of the pre-jump board |
| 2026-09-30 | Harness change: one-level JSON tool results; `thinking_budget` and `seed` forwarded; `edit_file` retries without escapes | DK, ED56 | Thinking-on and edit-heavy agents scored before this are not like-for-like |
| by 2026-10-02 | Top 0.24 (mirror); an undated copy of the board shows 0.18 ×5 and 0.17 ×32 | MIR, K-LB | The 0.17 cluster is absent on 09-28 and present in the undated copy; whether it follows the 09-30 harness change is a hypothesis (part of it may be platform drift) |
| 2026-10-04 | Forum findings compiled: undeclared tool call loses the patch, fix "to be implemented" | ED56 | |

**Cheapest separation of drift from edits:** a byte-identical re-score of the Roman ZIP. LogosTopos submitted exactly that on 2026-09-28 13:01:54 UTC (submission 56641493) and the material I read lists it as PENDING; check that repository's later commits before spending a daily submission (§H.7).

---

## E. Comparison matrix and ranked score drivers

Cells contain only what a source states for that bundle. "Unknown" means no accessible evidence, not absence. "0.17–0.24 tier" is entirely unknown except for the Budget-Fit title ("single agent").

### E.1 Structure and policy

| Dimension | Roman (0.12) | Black Cat anchor (0.10; V10 0.12) | Pathfinder (0.12) | Parthenos lean (0.10 badge) | 0.17–0.24 tier | Control: LT v4 (0.06) |
|---|---|---|---|---|---|---|
| Single vs multi-agent | Coder `swe_coder` + `code_analyzer` AgentTool | Coder + analyzer; author table says single 0.08 → +analyzer 0.10 (T) | Coder + analyzer (default) | Single agent, 9 built-ins (earlier version: coder + localizer + verifier) | Unknown (Budget-Fit: single) | Single agent + deterministic `repo-context` skill |
| Prompts and routing | Analyzer first with the whole issue, then verify at the reported spot; analyzer returns ≤250 words in six fields (LOCATION, ROOT CAUSE, FIX PLAN, RELATED, TESTS, CONFIDENCE) | Analyzer usually once, skipped when file and function are given; short request, issue injected by state; analyzer ≤≈6 calls, ≤≈200 words (soft) | Full issue to analyzer; budget checks | Not described | Unknown | ≈255-word prompt: load skill, run script, then fix |
| Tool-call policy | Six base tools + AgentTool; analyzer has run/read + `search_similar_code` + two graph tools; soft bans on installs, test edits, packaging | Root declares `search_similar_code` yet forbids it; analyzer lacks it; challenger adds: no repeated calls, `NO MATCHES`, ≤2 repro calls, no multi-statement `python3 -c` | Not described | Nine built-in tools | Unknown | One navigation entry; no graph tools |
| Retrieval | Grep-first plus graph tools; treats `search_similar_code` as concept search (does not match harness semantics, L15) | Lexical/graph via the analyzer; no similarity search | Not described | Not described | Unknown | Deterministic hybrid retriever (local Hit@5 28/33) |
| Context management | Main sees only the short report; analyzer has its own session | Short line ranges, no whole-file reads, scratch in `/tmp`, test logs saved then tailed; analyzer out cap 2,048 | Not described | Not described | Unknown | Tool trims returned material (median 3,590 chars) |
| Reproduction before edit | Yes: small repro | At most 2 calls (challenger) | Not described | Not described | Unknown | Not described |
| Patch-size discipline | "Small precise replacements" | Not described | Not described | Not described | Unknown | Not described |
| Tests and verification | Compile, re-run repro, nearby tests, read the diff | Logs saved then tailed | Not described | Not described | Unknown | Not described |
| Failure recovery | Prompt only | "Change approach on failure"; loop rules (author reports 10–80 repeats when thinking off, T) | Not described | Not described | Unknown | Not described |

### E.2 Envelope and parameters

| Dimension | Roman (0.12) | Black Cat anchor (challenger) | Pathfinder | Parthenos lean | 0.17–0.24 tier | LT v4 control |
|---|---|---|---|---|---|---|
| Time / call budgets | None declared (missing = no limit, L07) | 5 min / 40 calls / 100 turns / 120 s (8 / 100 / 150 / 300 s) | None by default (v1: hard 4 min → 0.08) | 4.5 min / 40 / 100 / 60 s | Unknown | 4.5 min / 40 / 64 / 60 s |
| Thinking and sampling | Off; T 0.2, top_p 0.95, top_k 40, out 8,192 | Off; root T 0.2, out 4,096 (8,192); analyzer T 0.1, out 2,048; a T = 1.0 variant scored 0.06 | Off | Off | Unknown | **On**; T 0.1; out 8,192 |
| Skills / adapters | None / none | None / none | No LoRA stated; skills not stated | 4 files; no adapter stated | Unknown | One skill / none |
| Repository or domain priors | None seen | None seen | None seen | None seen | Unknown | None (generic) |
| Patch submission behaviour | Submit after reviewing the diff (soft) | Not described | Not described | Not described | Unknown | Not described |
| Runtime failures and reproducibility | Fork 0.10; reproduction 0.08 after 14.5 h (T) | Anchor bytes hash-matched; 209-run lab claimed (unverified) | v1 0.08; "SuperAgent" fork 0.17 | Badge belongs to an earlier version | Unknown | v2 → v4 0.05 → 0.06 with several changes at once |

### E.3 Ranked likely score drivers

Ranking weighs (strength of evidence) × (plausible effect size) × (relevance to our candidate). "Gap" asks whether the factor can explain why public 0.10–0.12 bundles beat 0.06-scoring entries that used the same envelope.

| Rank | Driver | Evidence (ledger IDs) | Confidence | Explains the 0.06 → 0.12 gap? | What would falsify it |
|---|---|---|---|---|---|
| 1 | **Per-task envelope that fits the 12 h / ≈120-task cap and ≈25 tok/s decode** (and avoids both too-tight caps and 60-min caps) | L07, L36, L37, L43; 4-min caps in both 0.08 results; 4.5–5 min / 40 calls in 0.10; 12-min version overran (T); 8 min × 120 = 16 h | High on direction; low on the optimum | Not for 4.5 min / 40-call entries (same envelope); **yes for the 60 / 100 / 500 plan, which is the opposite of every verified ≥0.10 bundle** | An 8-min arm beating a 5-min arm by ≥3 tasks at ≤11 projected hours |
| 2 | **Avoiding hard-failure paths**: context overflow → empty patch, undeclared tool name, `{brace}` crash, malformed calls | L09, L19, L12, L40; 3–4/70 and ≈1/12 tasks lost locally | High that it exists; medium that it separates winners from controls | Partly: the control's 8,192 output cap leaves 24.6k of prompt headroom, a 4,096 cap leaves 28.7k; overflow counts of the controls are unknown | Overflow count driven to 0 with no change in empty-patch rate |
| 3 | **Thinking off plus explicit loop control** | L11, L38, L39, L40, L41; the one config axis between LT v4 (on, 0.06) and public (off, 0.10–0.12) | Medium-low (conflicting data); high that the *time* effect is real | Yes, as the only visible config difference, but confounded by output cap, prompts, dates | A paired low-budget-thinking arm beating thinking-off by ≥4 points within the hour budget |
| 4 | **Short, bounded analyzer handoff** (context isolation) | L22–L24, L20; single agents at 0.10 (L26) and 0.18 (L27, title only); coder + analyzer at 0.06 (L29) | Low-medium | Unclear: coder + analyzer also appears at 0.06 | A single-agent baseline matching coder + analyzer under identical envelope |
| 5 | **Cheap reproduce → targeted verify → early, repeatable submit** | L41 (submitted patches 4 → 11 of 16, resolved 2 → 3), L42 (9/19 failures were process failures) | Medium for non-empty patches; low for resolution | Possible (empty or unverified patches) | Non-empty rate rises but resolved does not, over ≥3 seeds |
| 6 | Retrieval sophistication (semantic, graph) | L15, L16, L44 | Low (negative evidence) | No | A harness-compatible retriever lifting resolved by ≥3 tasks |
| 7 | LoRA / training | L14, L38 (U787: round-0 adapter 8/70 vs base 23/70, decode −21% at rank 64); no inspected ≥0.10 bundle uses one | Low / negative for this timeline | No | A verified adapter bundle ≥0.15 with code |
| 8 | Selection and drift (noise, harness changes, winner's curse) | L33–L35, L45 | High that it exists | Explains ±2–3 tasks and perhaps the 0.17 cluster | Byte-identical re-score staying at its old value |

**Things that look important and are not supported by any evidence I could find:** repository-specific priors (hidden tasks are private repos, L17); semantic search quality; the number of agents; having more tools; having more prompt text.

---

## F. Recommended architecture delta for our candidate

### F.0 What the delta is applied to

The candidate is taken as described to me (Adversarial SWE Hybrid). If a row is wrong, only the "Current" column changes.

| Setting | Current | Recommended | Why (ledger IDs) |
|---|---|---|---|
| Per-task time (`max_time_minutes`) | 60 | **5** | Mean budget is 6 min per task (12 h / 120); 12 tasks at 60 min would use the whole 12 h (L02, L07, L36, L37) |
| `max_tool_calls` | 100 | **50**, shared with any sub-agent | Sub-agent calls spend the same budget (L20); public 0.10 bundles use 40 (L23, L26) |
| `max_turns` | 500 | **100** | Public 0.10 bundles use 100 (L23, L26) |
| `timeout_seconds` | 300 | **300**, plus an agent-side 60-second rule for long commands | Judgment call: the 0.10 bundles used 60–120 s (L23, L26) and the Black Cat challenger 300 s (L24); 300 leaves room for slow test files while the prompt rule stops one hung command from eating a 5-min budget |
| `max_output_tokens` | 16,384 | **3,072** main, **1,536** investigator | Prompt + `max_tokens` must stay ≤ 32,768 (L09): 16,384 leaves 16.4k of prompt, 3,072 leaves 29.7k. One generation of 16,384 tokens takes ≈10.7 min at 25.5 tok/s, longer than the whole budget (L37) |
| Thinking | `include_thoughts: true`, budget 4,096 | **Arm A: off.** Arm B: on, budget 512 | A 4,096-token thought is ≈161 s *per turn* (L12, L37). All verified public ≥0.10 bundles run it off (L11, L22–L26); evidence on benefit is conflicting (L38) |
| Sampling | T 0.2, top_p 0.95, top_k 40 | keep | Identical to Roman and the Black Cat root (L22, L23) |
| Retrieval | semantic + lexical from the start | **lexical-first through `run_command`; no `search_similar_code`; no graph tools in S0 or S1** | Official embeddings and the search tool cannot serve natural-language queries; its output was unbounded (L15, L16) |
| Sub-agent | read-only adversarial investigator, no stated limits | **None in S0.** S1: gated, ≤6 calls, ≤150 words, issue injected by state | No public evidence for an adversarial role; sub-agent sessions reportedly are not compacted (single source) and delegation is sequential (L08, L10, L20) |
| Skills / LoRA | none stated | none | L14, L29 |
| Prompt rules | no test edits, no installs, no network, scratch in `/tmp` | keep, and add the loop, notes and submit rules in §F.3 | L39–L42 |

### F.1 Build order (one change per leaderboard submission)

| Stage | Contents | Purpose |
|---|---|---|
| **S0** | Single agent, six base tools, envelope and output caps from §F.2, thinking off, prompt from §F.3 without the helper paragraph | Establishes an envelope-fixed baseline and attributes everything after it |
| **S1** | S0 + gated investigator (§F.2, §F.3) | Tests the adversarial role against S0 on identical tasks, seeds and caps |
| **S2** (optional) | S0 or S1 with arm B (thinking on, budget 512) | Only if the paired local data in §H favours it |
| Not scheduled | Graph tools, a local BM25/TF-IDF skill, LoRA | No supporting evidence yet (§E.3 ranks 6–7) |

### F.2 Exact files

`eval_config.yaml` (ZIP root; only these four fields are read, L07):

```yaml
max_time_minutes: 5
max_tool_calls: 50
max_turns: 100
timeout_seconds: 300
```

`configs/sampling.yaml` (main agent, arm A). Key names mirror the public bundles; confirm with the official compile step before packing (L06):

```yaml
temperature: 0.2
top_p: 0.95
top_k: 40
max_output_tokens: 3072
thinking_config:
  include_thoughts: false
```

Arm B differs only here, and only if the installed `resolvers/generation.py` forwards `thinking_budget` (it did not on 2026-09-28; the 2026-09-30 change reports it does, L11, L12):

```yaml
thinking_config:
  include_thoughts: true
  thinking_budget: 512
```

`configs/sampling_investigator.yaml` (S1 only):

```yaml
temperature: 0.1
top_p: 0.95
top_k: 40
max_output_tokens: 1536
thinking_config:
  include_thoughts: false
```

`agent.yaml` (S1 shown; delete the `agent_tool` entry for S0). Include style and `config_path` rules follow the public bundles (no `..` in `config_path`, L06):

```yaml
name: swe_coder
model: gemma-4-31b-it-qat-w4a16-ct
description: Fixes one repository issue and submits a patch.
instruction: !include prompts/system.md
generate_content_config: !include configs/sampling.yaml
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
  - agent_tool:
      config_path: sub_agents/investigator.yaml
      skip_summarization: true
```

`sub_agents/investigator.yaml` (S1 only; copy the include style of Roman's `sub_agents/code_analyzer.yaml`, whose path resolution I could not read):

```yaml
name: investigator
model: gemma-4-31b-it-qat-w4a16-ct
description: Read-only adversarial check of a proposed fix. Call at most once.
instruction: !include prompts/investigator.md
generate_content_config: !include configs/sampling_investigator.yaml
tools:
  - run_command
  - read_file
```

`skip_summarization: true` is chosen because every inspected public coder + analyzer bundle uses it (L20, L22, L23). The control flow it implies (the invocation ends, then a harness nudge resumes the main agent) must be confirmed in traces before it is changed.

### F.3 Exact prompts

Both prompts avoid curly braces (the only exception is the single state token in the investigator prompt, L19) and avoid code-literal shell lines, which were emitted as tool names in replays (L40). If you edit them, keep both properties.

`prompts/system.md` (S0; S1 appends the helper paragraph below it):

```text
You are a software engineer fixing one GitHub issue in the repository at /workspace. Hidden tests decide success, and only your final change to the repository counts.

Budget: about 5 minutes and 50 tool calls for the whole task. Every token you write costs time, so keep replies short. The tools get_status and submit_patch are free.

Workflow
1. Read the issue once. Note the symptom, the most likely function or file, and what correct behaviour looks like.
2. Locate the code. Search by calling run_command with a recursive grep for identifiers, error strings and parameter names from the issue, and add a fallback that prints the words NO MATCHES when the search finds nothing. Read code with read_file in ranges of at most 120 lines.
3. Reproduce only if it is cheap, in at most 2 calls. Create scratch files under /tmp by calling run_command with a here-document. Never use write_file for scratch, and never leave scratch files in /workspace.
4. Edit with edit_file. Make the smallest change that fixes the root cause and touch as few files as possible. Do not edit tests, test configuration or build files. Do not install anything. There is no network.
5. Verify. Re-run your reproduction and the most relevant existing test file or test names. Put the timeout utility with a 60 second limit in front of long commands and pipe output through tail so it stays short. Never run a whole test suite.
6. Submit with submit_patch as soon as you have a plausible fix. It is free and repeatable. If you change code afterwards, submit again. Before your last submission, check that the diff contains no stray files.

Rules
- Do not repeat a tool call that already returned the same result unless the code changed in between. If a search returns nothing, change the pattern or the directory. If an edit fails twice on the same text, re-read those exact lines and copy the text exactly.
- After every tool result, begin your next reply with one plain sentence of notes, at most 20 words: what you learned and what you will do next. Notes survive context trimming; tool outputs may not.
- Keep outputs small: use line ranges, head and tail. Never print whole large files.
- End every reply with a tool call until you are finished. A reply without a tool call after a submission ends the task, so send one only when you are done, and make it a single sentence.
- Around tool call 35, stop exploring and submit your best fix.
```

Helper paragraph (S1 only, appended to `prompts/system.md`):

```text
Helper
You have one read-only helper named investigator. Call it at most once, and only after you have a concrete plan or edit, when your change touches code that has more than one caller or sibling implementation, or when the first relevant test still fails after an edit. Send a short request: the file and function, the cause you believe, and the change you made or plan. The helper already has the issue text. Treat its reply as evidence to check, not as an order.
```

`prompts/investigator.md` (S1 only):

```text
You are a read-only code investigator working in the same repository as the engineer who called you. You never edit files and you never submit a patch.

The issue the engineer is fixing: {problem_description?}

The request you receive states the engineer's current hypothesis: a file and function, the cause they believe, and the change they made or plan. Try to refute it quickly, using at most 6 tool calls.

Check in this order: (1) does the cited code really produce the reported symptom; (2) are there other callers, overrides or sibling implementations that need the same change; (3) is there an existing test that encodes the intended behaviour; (4) would the planned change break an obvious caller.

Use read_file in ranges of at most 120 lines, and run_command with a recursive grep for exact identifiers. Do not repeat a search that returned nothing; change the pattern. If a search is empty, say so explicitly.

Reply in at most 150 words, in exactly this form:
VERDICT: supported, refuted or uncertain
EVIDENCE: file and line facts you actually read
MISSED: other places that need changes, or none
TEST: the best existing test file or test name to run, or none
```

State injection of the issue relies on the harness writing `problem_description` into session state (L20, one reader). If your harness build does not, the investigator sees only the short request; check this in the first fake-model replay (§F.5).

### F.4 The five decisions

#### D1. Fit the per-task envelope to the 12-hour cap and the decode speed

- **Change:** `eval_config.yaml` as in §F.2; the prompt states the budget and a 35-call checkpoint.
- **Mechanism:** tasks run sequentially under one 12-h cap (≈6 min mean per task, including setup), decode is ≈25.5 tok/s, and a 60-min cap is not a plan: 12 stuck tasks consume the whole budget. At 5 min the worst case is 10.0 h plus ≈10 min of setup (L07, L36, L37). Public results bracket the choice: 4-min caps appear in both 0.08 results, 4.5–5 min / 40 calls in 0.10, no limit in 0.12 at the price of a 14.5-h reproduction (L28, L43).
- **Risks:** 5 min may truncate hard tasks; the optimum between 4.5 and 8 min is untested; behaviour at a hard budget stop (whether unsubmitted edits are captured) is not verified.
- **Complexity:** trivial (config).
- **Confidence:** high that 60 / 100 / 500 is unsafe; medium that 5 / 50 is near-optimal.
- **Falsifiable test:** projected 120-task hours ≤ 10.5 with p95 task time ≤ 5 min (scorer-time estimator, §H). Paired local run, ≥40 tasks × 2 seeds: resolved(5 min) ≥ resolved(8 min) − 1. **Falsified** if the 8-min arm solves ≥3 more tasks and its projected total stays ≤ 11 h; then move to 6–7 min.

#### D2. Make context overflow structurally impossible

- **Change:** `max_output_tokens` 3,072 main / 1,536 investigator; no `search_similar_code` and no graph tools; 120-line reads, head/tail on every command; investigator ≤6 calls and ≤150 words; one-sentence notes after each tool result; no `{identifier}` braces; no shell literals in prompts.
- **Mechanism:** a request with prompt + `max_tokens` above 32,768 returns HTTP 400 and the harness records an empty patch, discarding an earlier submission. Two independent teams lost patches this way (3–4 of 70 tasks per run; ≈1 of 12), and one scorer-stack case was 28,673 + 4,096, one token over (L09). Compaction (≈14,336) does not guarantee headroom because prompts reached 28.7k, and sub-agent sessions reportedly are not compacted (L10, single source). The notes exploit the reported text-only summary (L10, single source).
- **Risks:** a 3,072 cap can truncate a very long `edit_file` argument; notes cost ≈1 s per turn (≈40 s over 40 turns); the notes-survive-compaction mechanism is single-source.
- **Complexity:** low.
- **Confidence:** high on mechanism, medium on magnitude for private repos.
- **Falsifiable test:** a proxy that enforces the 32,768 rule over ≥40 tasks × 2 seeds must log **0** requests with prompt + `max_tokens` > 32,768 and **0** "Sandbox execution error" outcomes; empty-patch rate should fall by ≥3 points against the current settings. **Falsified** if overflows reach 0 and the empty-patch rate does not change. A second paired arm without the notes line tests the compaction rationale.

#### D3. Thinking off plus loop control, against one low-budget thinking competitor

- **Change:** arm A as in §F.2/§F.3 (off; repeat, empty-search and prose-bound-command rules). Arm B: thinking on, budget 512, same prompt.
- **Mechanism:** with thinking on, thinking takes 65–71% of agent time; with it off, 50% of calls repeat an earlier call and 24% are malformed, and the Black Cat rules (no repeats, explicit empty results, short reads) target exactly those failures (L38, L39). Replays show prose-bound commands cut malformed names from 31% to 5% (L40).
- **Risks:** the evidence conflicts (L38: one team found thinking on better, 7/58 vs 3/58, but a second thinking-on run fell to 20/70 locally); the harness changed on 2026-09-30, so older thinking-on scores are not like-for-like.
- **Complexity:** low (config and prompt).
- **Confidence:** medium-low on direction; high that thinking costs minutes.
- **Falsifiable test:** paired local arms A and B, ≥40 tasks × 3 seeds. Decision rule: choose B only if resolved improves by ≥4 points **and** projected hours stay ≤ 10.5. **Falsified** if arm A keeps a repeat-call share above 20% after the rules (the prompt is not controlling loops), which would justify trying B or a harder guard.

#### D4. Sub-agent contract: single-agent baseline first, then a bounded, gated, state-injected check

- **Change:** S0 has no sub-agent. S1 adds the investigator in §F.2/§F.3 with the call gate, ≤6 calls, ≤150 words and the four-field verdict.
- **Mechanism:** isolates exploration from the main context and returns a short, checkable verdict; delegation is sequential and spends the shared budget (L08, L20). Public evidence does not show that structure decides scores: a single agent at 0.10, a single agent at 0.18 (title only) and coder + analyzer at 0.06 all exist (L26, L27, L29).
- **Risks:** no public evidence for an *adversarial* role; sub-agent context overflows caused 3 of the 5 losses in one measured arm (DK); one extra model loop costs minutes; `skip_summarization` depends on the harness nudge; the state key may be absent.
- **Complexity:** medium.
- **Confidence:** low-medium.
- **Falsifiable test:** S0 vs S1 on identical tasks, seeds and caps. Primary: resolved and minutes per task. **Falsified** if S1 does not beat S0 by ≥2 tasks (pooled over seeds) or adds more than 1 minute per task. Secondary: among tasks where the verdict was REFUTED, how often did the next edit differ and then pass?

#### D5. Submission discipline and failure recovery

- **Change:** submit early and repeatedly; end every turn with a tool call until finished; check the diff for stray files; scratch via `run_command` only; no test edits; checkpoint at call 35.
- **Mechanism:** guarantees a non-empty change under budget pressure and avoids ending the session by accident (a text-only reply after a submission ends the task, and three consecutive nudges end it too, L20). One 16-task official-harness pilot raised submitted patches from 4 to 11 of 16 with a prompt-only addendum while resolutions moved only 2 → 3; 9 of 19 failures in a local audit were process failures (L41, L42).
- **Risks:** an early submission can anchor the agent on a wrong fix; whether the last `submit_patch` or the final working tree is graded at a hard stop is not verified; non-empty is necessary, not sufficient.
- **Complexity:** low.
- **Confidence:** medium.
- **Falsifiable test:** process gates over ≥40 tasks × 2 seeds: non-empty rate ≥95% (excluding explicit no-fix cases), nudge exhaustion 0, scratch or test files in the patch 0. **Falsified** if the non-empty rate rises but resolved does not move over ≥3 seeds; then the effort belongs in correctness (localization, verification), not discipline.

### F.5 Pre-flight checklist (offline, before any submission)

1. Run the official compile path (`validate_directory`, `discover_declared_models`, `compile_submission`) in a Python 3.12 environment with the distributed wheels, as HI32 did; the model list must be exactly `gemma-4-31b-it-qat-w4a16-ct`.
2. Search every prompt file for `{`: zero hits in `system.md`; exactly one (`{problem_description?}`) in `investigator.md`.
3. ZIP root contains `agent.yaml` and `eval_config.yaml`; every file ends in .yaml, .yml, .md, .txt, .py, .json or .safetensors; no `.sh`; no `..` in any `config_path`.
4. Scripted-model replay through the real harness (fake LLM): confirm per-agent sampling values, tool-result encoding, that every declared tool resolves, and that the investigator receives the issue text.
5. Proxy run that enforces the 32,768 rule: overflow count 0; log malformed names, repeat share, nudge exhaustion.
6. Scorer-time projection: p95 task ≤ 5 min and 120-task total ≤ 10.5 h.
7. Record which harness date and library versions you targeted (adk_submission 0.2.11, swegemma 0.2.7, google-adk 1.36.1 were the versions the sources inspected; the scorer's current versions are not verified).

### F.6 Harness facts worth hard-coding into review (all from §C)

- Closed tool registry; custom named Python tools do not exist; `run_skill_script` and `load_skill_resource` are not tool names (L06).
- An undeclared tool name loses the patch (L19); keep prompts from inviting tool names that are not declared.
- `write_file` on a `/tmp` path may land under `/workspace/tmp` and end up in the patch (MK); another source mentions a harness-side `/tmp` rejection (ED73, unverified). Either way, use a here-document through `run_command` for scratch.
- Test files are reset before grading; `pytest.ini` and `conftest.py` are harness files (MK).
- `thinking_budget` is a hard cap only from the 2026-09-30 harness on (L12).

---

## G. Do not copy

Techniques that are unverified, fragile, costly, or incompatible with the harness. "Tier" is the evidence behind the warning.

| # | Do not copy | Why | Ledger / tier |
|---|---|---|---|
| 1 | Any public ZIP as "the 0.12 recipe" | No controlled ablation; the downloaded bytes are not proven to be the scored bytes; one reproduction reported 0.08 after 14.5 h; two forks differ by 0.02 | L22, L28; S/T |
| 2 | Natural-language `search_similar_code` queries, or prompts that rely on them (Roman's analyzer treats it as concept search) | It looks up stored vectors by node id or source; free text returned nothing in >400 calls; output was unbounded (≈130k characters for one class) | L15; Confirmed |
| 3 | A tool that is declared but forbidden in the prompt (Black Cat root keeps `search_similar_code` yet bans it) | Adds attention load for no evidenced benefit; either leave it out of both places or keep them consistent | L23; S, effect unmeasured |
| 4 | Per-task envelopes of ≥8 min, or none (Black Cat challenger, Roman) | 8 min × 120 tasks = 16 h; a 12-min version overran 12 h; the 12-h overrun currently errors the submission | L07, L24, L43; Confirmed rule, T for the overrun report |
| 5 | `thinking_budget` as a control knob on harness builds before 2026-09-30, or paired with `include_thoughts: false` (Roman's 4,096 is inert) | Not forwarded before the change; thinking is off whenever `include_thoughts` is false | L11, L12; Confirmed |
| 6 | Large thinking budgets, 16k output caps, `include_thoughts: true` at scale (starter kit at 0.05; our candidate's current settings) | ≈161 s per 4,096-token thought; 16,384 tokens ≈10.7 min; halves the prompt window | L09, L12, L29, L37 |
| 7 | LoRA / adapters for this build | Silent-zeroing bug until a fix; −8% to −21% decode; high ranks shrink KV cache; round-0 adapter lost 8/70 vs 23/70 for base; no inspected ≥0.10 bundle uses one | L14, L38; Confirmed / T |
| 8 | Repository-specific priors from fastapi, rich, requests, httpx | Hidden tasks come from private repos; 115 of 129 public tasks are fastapi or rich | L17; Confirmed |
| 9 | Local dev-set resolution as a proxy for the leaderboard | Same zip: 25/70 locally vs 7/58 on Kaggle; 29/48 locally on rich tasks | L34; Confirmed |
| 10 | Trusting titles or score badges | "LB 0.24" recorded 0.13; "0.13 Submission" recorded 0.10; a 0.10 badge belongs to a different version than the downloadable default | L32; Confirmed |
| 11 | Parallel, multi-candidate or voting pipelines | No parallel model calls; sequential tasks under one 12-h cap | L08; Confirmed (single relay of one host reply) |
| 12 | Notebook-side analysis (EDA, TF-IDF, edit simulation) as if it shipped | Not in the ZIP, so it is not part of what is scored | L22; Confirmed by file listing |
| 13 | Code-literal shell commands inside prompts | Emitted as tool names in replays (31% vs 5% when written as prose bound to `run_command`); an undeclared name loses the patch | L19, L40; single-source rate |
| 14 | Any `{identifier}` in an instruction | ADK treats it as a state key and raises when absent | L19; Strongly inferred |
| 15 | `.sh` files, custom-named Python tools, `run_skill_script` or `load_skill_resource` as tool names | Rejected by the compiler or the closed registry | L06; Confirmed |
| 16 | Putting a non-Gemma model in the loop (a 0.15 notebook is titled "Gemma + Gemini"), or reusing third-party prompt text verbatim | Single-model rule for every agent and sub-agent; prompts were inspected for structure only, with no licence stated | L05; Confirmed rule, effect of title unknown |

---

## H. Test plan: do the recommendations improve actual patch success?

### H.1 Principles

1. **Process metrics are the primary signal; resolved counts are secondary.** Repeat-call share, malformed-call share, empty-patch rate, overflow count and minutes per task are far less noisy than a resolved count [U787].
2. **One change per stage, paired design.** Same tasks, same seeds, same caps; compare per-task success fractions.
3. **Local resolution is not an absolute measure.** The same zip scored 25/70 locally and 7/58 on Kaggle (L34). Only paired local deltas mean anything.
4. **The leaderboard is an integration check, not an experiment.** 58 tasks, one submission a day, ±2.5 tasks of noise (§A.5).
5. **Pre-register thresholds** (§H.7) before looking at results. The thresholds below are my proposals, not source values.

### H.2 Arms

| Arm | Contents | Tests |
|---|---|---|
| **A0** | Current candidate (thinking on 4,096; out 16,384; adversarial investigator), run under the **same 5 min / 50-call cap** as the others | Isolates generation and prompt effects from the envelope. Optionally run 10 tasks under its own 60-min cap only to see the time distribution |
| **A1 = S0** | Single agent, D2 + D3(A) + D5 (§F) | Baseline for everything below |
| **A1-8** | A1 under 8 min / 100 calls / 150 turns | D1 (5 vs 8 min) |
| **A2 = S1** | A1 + gated investigator | D4 |
| **A3** | A1 with thinking on, budget 512 | D3 (arm B) |
| **A4** | A1 without the one-sentence-notes rule | D2's compaction rationale |

### H.3 Gates

| Gate | What runs | Pass condition |
|---|---|---|
| **G0 Offline** | Official compile; brace and extension scan; fake-LLM replay through the real harness (§F.5) | All checks pass; investigator receives the issue text |
| **G1 Process** | Proxy that enforces the 32,768 rule; ≥40 tasks × 2 seeds per arm | Overflow requests 0; "Sandbox execution error" 0; malformed tool names ≤2%; repeat-call share ≤15% (thinking-off baseline in U787 was 50%); nudge exhaustion 0; scratch or test files in patches 0; empty-patch rate ≤5% |
| **G2 Time** | Scorer-time projection from per-call completion tokens | p95 task ≤5 min and projected 120-task total ≤10.5 h |
| **G3 Paired** | A1 vs A0, A1-8, A2, A3, A4; ≥40 tasks × 3 seeds | Per-arm decision rules in §F.4 |
| **G4 Leaderboard** | One submission per stage, in the order S0, S1, then S2 if justified | Integration only: non-error completion, runtime inside the cap, score within the noise band of expectations |

### H.4 Statistics (my arithmetic)

- **Leaderboard:** 58 tasks; one task = 0.017; binomial 1σ at p = 0.12 is 2.5 tasks (0.043). A difference under ≈3 tasks (0.05) is not evidence on one run. The public half also carries winner's-curse inflation at the top.
- **Single-seed paired local comparison, exact McNemar:** with ≈15 discordant pairs, 12 vs 3 gives two-sided p = 0.035 and 11 vs 3 gives 0.057; with ≈9 discordant pairs, 8 vs 1 gives 0.039 and 7 vs 1 gives 0.070. So a single seed needs a net gain of roughly **7–9 tasks** to be credible. Pooling three seeds per task and using a paired permutation test on per-task success fractions lowers that bar. Run a quick simulation from your own observed flip rates before fixing sample sizes (U787 saw 14 of 70 tasks flip between runs).
- **Process metrics** can be judged on far fewer tasks because their per-turn counts are large.

### H.5 Where to run things

| Option | Good for | Limits |
|---|---|---|
| Official recipe in a Kaggle notebook (wheelhouse → vLLM TP4, 32k, gemma4 parsers → harness evaluator) | Real scorer-stack behaviour; the host's starter ran 2 tasks in 944 s on 4×L4 | 4×L4 sessions queue 4–9+ h (L36); a 12-h session limit |
| Scorer-replica proxy over a local backend (DK) | Overflow, malformed-call and loop metrics; time projection | Different weights and kernels; sampled outputs differ in detail; local servers hide failure modes, so never trust an Ollama-only run for overflow or call-parsing results |
| Fake-model replay through the real harness | Plumbing: tool resolution, encoding, state injection | Tests wiring, not model behaviour |

### H.6 Leaderboard cadence (1 submission per day)

1. Optional day 0: check LogosTopos' later commits for the outcome of its byte-identical Roman re-score; if there is none, spend one submission on it (§H.8).
2. S0, then S1, one change each; record ZIP SHA256, date, library versions and the score.
3. Choose the two final selections from paired local evidence plus the leaderboard, never the leaderboard alone.

### H.7 Pre-registered decision log (fill before running)

| Decision | Metric | Threshold | Outcome | Action |
|---|---|---|---|---|
| D1 envelope | Resolved (5 vs 8 min), projected hours | 8-min arm +3 tasks at ≤11 h projected | | Move to 6–7 min, else keep 5 |
| D2 overflow | Overflow count; empty-patch rate | 0 overflows; ≥3-point drop in empty patches | | Keep caps; else investigate other causes |
| D3 thinking | Resolved; repeat share; hours | B beats A by ≥4 points at ≤10.5 h | | Choose B only if met |
| D4 investigator | Resolved; minutes per task | S1 ≥ S0 + 2 tasks and ≤ +1 min | | Keep gate, else drop |
| D5 discipline | Non-empty rate; nudge exhaustion; scratch files | ≥95%; 0; 0 | | Keep; else revise prompt |
| Notes rule | Resolved with vs without | No loss, ≤40 s per task | | Keep or remove |

### H.8 Calibration submission (platform drift)

Re-score a byte-identical Roman ZIP (SHA256 `f3534769cd8c7761b8ae83722b0f2fd381c0349587a10e84bd63e0554a4a7aa4`; rebuild with the LogosTopos script that enforces the hash). If it scores ≥0.15 now, a share of the jump from 0.12 to the 0.17 cluster is platform drift rather than agent edits (L45). If it stays near 0.12, the 0.17–0.18 notebooks contain real changes worth pulling and reading (Appendix 2).

---

## Appendix 1. Method and access log

| # | Attempt | Outcome |
|---|---|---|
| 1 | Fetched the Kaggle Overview, Leaderboard, Code listing and the Black Cat notebook URL | Each returned only HTML meta tags (client-side rendering) |
| 2 | Fetched a GitHub `tree/` page | Refused by robots; `blob/` pages and repo root pages worked |
| 3 | Fetched a private repository link (usp787/Gemma4_kaggle_repo) | HTTP 404 |
| 4 | Community leaderboard tracker dashboard | JavaScript shell ("Tracker initializing…"); a constructed data URL was rejected because it had not appeared in earlier results |
| 5 | Network from the bash sandbox | Disabled, so no Kaggle CLI or API, and no credentials |
| 6 | Searched for distinctive notebook phrases and slugs | Only listing pages and third-party repos; no notebook text |
| 7 | Search-index copies of Kaggle pages | Partial text (leaderboard rows, code listing, overview excerpt), undated or with relative dates |
| 8 | Re-fetched the load-bearing third-party pages late in the session (LT-CMP, LT-ARCH, GD-PUB, DK, U787, ED56, HI32, MK) | Every hash, count and date cited from them was re-checked against the page text |
| 9 | Not re-fetched: GD-README, ED73, FL, NS, RL, BS, CLIST and the Kaggle search-index excerpts | Figures from them come from my first reading in this session |

Claims most exposed to the access limit: L22–L28 (bundle contents, version table, the 0.17–0.24 tier).

## Appendix 2. Commands to close the biggest unknowns

Flags are from my knowledge of the Kaggle CLI; confirm with `--help`. Record version numbers and hashes in a manifest, as LogosTopos did.

```bash
# 1. Fresh, dated leaderboard export
kaggle competitions leaderboard gemma-4-developer-agent --download

# 2. Public notebooks for the competition, best score first
kaggle kernels list --competition gemma-4-developer-agent --sort-by scoreDescending --page-size 50 --csv

# 3. Source and outputs of a notebook (repeat per slug)
kaggle kernels pull lucifer19/black-cat-swe-agent-pack-instinct -p work/black-cat -m
kaggle kernels output lucifer19/black-cat-swe-agent-pack-instinct -p work/black-cat-out
sha256sum work/black-cat-out/*.zip
unzip -l work/black-cat-out/submission.zip
```

Slugs known to me: `lucifer19/black-cat-swe-agent-pack-instinct`, `romanrozen/gemma-eda-baseline-for-a-start-lb-top-1`, `mizeroluckygall/pathfinder-gemma-4-agent-eda-baseline`, `nihilisticneuralnet/0-10-gemma-4-developer-agent-submission`, `ryanholbrook/getting-started-gemma-4-developer-agent`. For the 0.17–0.18 tier (Budget-Fit Single Agent, Gemma 4 SuperAgent, Calibrated Sin…) take the slugs from command 2. Forum threads can be read with `kaggle competitions topics show <id>` (the method ED56 reports using); the useful IDs are 743063, 743663, 743964, 743140, 743506, 745731, 744577.

## Appendix 3. Arithmetic

**Time (12 h cap).** 720 min / ≈120 tasks = 6.0 min mean per task including setup. The host reports patch validation (≈2 h) is excluded and a no-patch run takes ≈10 min in total, so setup is ≈5 s per task on average (L36).

| Per-task cap | Worst case if every task hits it |
|---|---|
| 5 min | 10.0 h (+≈0.2 h setup) |
| 8 min | 16.0 h |
| 60 min | 120 h; any 12 tasks at the cap use the full 12 h |

Per-call cost model (DK): 0.6 s + completion tokens / 25.5 tok/s.

| Completion tokens | 100 | 400 | 1,000 | 3,072 | 4,096 | 8,192 | 16,384 |
|---|---|---|---|---|---|---|---|
| Seconds per call | 4.5 | 16.3 | 39.8 | 121.1 | 161.2 | 321.9 | 643.1 |

A 6-minute mean allows ≈9.2k generated tokens per task with zero tool time (≈8.4k after 50 calls of overhead).

**Context (32,768 ceiling).** Prompt headroom = 32,768 − `max_tokens`:

| `max_tokens` | 16,384 | 8,192 | 4,096 | 3,072 | 1,536 |
|---|---|---|---|---|---|
| Max prompt tokens | 16,384 | 24,576 | 28,672 | 29,696 | 31,232 |

The scorer-stack overflow in DK (28,673 + 4,096) was one token over.

**Score ↔ tasks.** floor(100·k/58)/100: k = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 give 0.01, 0.03, 0.05, 0.06, 0.08, 0.10, 0.12, 0.13, 0.15, 0.17, 0.18, 0.20, 0.22, 0.24.
