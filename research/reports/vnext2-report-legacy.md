# submission-VNEXT2 — report

Evidence labels: **[official]** Kaggle rules/overview text as retrieved 2026-10-04 · **[3p]** public repos/discussions claiming to have read the harness (not verified by me) · **[calc]** my arithmetic from stated assumptions · **[judgment]** my reasoning, unmeasured.
Nothing here was run against Gemma, the real harness or the real tasks. Nothing was submitted to Kaggle.

## Read first
1. **The 84 training tasks were not in the upload** (only the 4-file ZIP). I could not mine them. The playbook is pattern-level priors (your 10 categories + conventions of the repo families the public tasks span: fastapi 67, rich 48, requests 13, httpx 1 [3p]). `tools/mine_train_priors.py` recomputes real family counts from the train split only (leak-guarded); use it to reorder or prune the playbook.
2. **0.00 looks systematic, not marginal.** The public leaderboard (≈50% of test data; 1 task ≈ 0.017) showed top 0.24, a cluster at 0.17, and ≥0.13 down to at least rank 48 [official snapshot]. In that snapshot 0.12 would sit below rank ~48, so "~0.12" is no longer the frontier. Likely causes of an exact zero are in item 3; none can be confirmed from here.
3. **Which zip scored 0.00?** If it carried a placeholder/untrained adapter, VNEXT (no adapter) may never have been scored.

## 1. Why VNEXT is smaller
VNEXT is 3,329 bytes: `agent.yaml` (301 B), `eval_config.yaml` (96), `configs/sampling.yaml` (106), `prompts/system.md` (5,136). No `adapters/`, `skills/` or `sub_agents/`. Its tool list has 8 of the 9 harness tools (no `get_code_subgraph`). Text files cannot make an archive large; MB–GB size can only be `.safetensors` adapters. I was not given the earlier zips, so the exact removed files are inference — send an older zip and I will diff it.

## 2. Does smaller size matter?
No causal link; the cap is 3 GiB [3p] and adapters are optional [official]. Indirect effects only: dropping adapters removes a failure source, dropping sub-agents removes extra model loops. Were the adapters useful? No evidence either way in this ZIP. Public signals are negative-to-neutral: one repo says the scorer's patched vLLM wipes adapters [3p]; vLLM issue #41754 reports Unsloth-trained Gemma-4 adapters loading but being ignored; I found no public adapter win. An untrained adapter could only hurt.

## 3. What the old approach optimized
Localization (22/22 hits) and a ~40-call workflow. It did not optimize "a patch exists when the clock stops". Concrete VNEXT properties:
- Plans ~30 calls and says submit "by about call 30"; in 270 s only ~8–26 turns fit [calc, App. B].
- No rule that a text-only reply ends the run (the session ends on one [3p]).
- First `submit_patch` only at the end; no checkpoint.
- `timeout_seconds: 120`, which one team reads as also capping the grading test run [3p].
- No tool argument names (`filepath`, `old_string`, `new_string`); Gemma 4 has documented missing-argument tool calls.
Ranked suspects for the zero: (a) no patch ever captured (late/never submit, text-only end, time cap); (b) malformed tool calls or loops; (c) grading timeout; (d) polluted or rejected patch; (e) bad adapter in the scored zip. Check per-task logs for: empty-patch rate, calls and wall time used, termination reason.

## 4. What VNEXT2 optimizes
Verified patches per global time budget, not localization. Mechanisms: anytime patch (checkpoint submit after the first edit, free); survival rules on top; confidence tiers so effort tracks uncertainty; a six-line ledger before the first edit; A–G failure classes with a stop-repeating rule; a one-call final gate; conditional playbook (10 family reference files, one loaded at most, only at MEDIUM/LOW or after a failure); batching reads into one `run_command`.

## 5. Training-derived patterns
Not mined (see Read first). Shipped families: dependency-callable, types-annotations, compat-versions, parse-serialize, http-request, render-format, state-cache-lifecycle, contract-errors-validation, async-sync, multi-file-propagation. Each reference file has LOOK (subsystems/symbols to inspect), PITFALL (what a first fix misses), TEST (test pattern). Recurring cross-family patterns encoded: fix classification and its consumer together; mirror sync/async twins and version branches; thread new options through every wrapper/sibling entry point with an old-behavior default; match issue text exactly for errors; expected strings include ANSI/trailing spaces. No keyword→file mappings, no patch text, no validation/held-out content. Treat families as hypotheses until the miner's counts agree.

## 6. Public approaches
| Source | What it does | Evidence | Used? |
|---|---|---|---|
| richie1988 evidence-first graph-guided | one root, 8-stage prompt, graph tools used selectively | no scores published | final diff-review commands, selective graph use; not the 8 mandatory stages |
| Gosling-dude | skills as call compressors, thinking off, grading-timeout and kebab-case findings | never run on real Gemma (self-reported) | timeout 300, thinking off, symbol-name search; no scripts |
| Maukthik | 4.5 min/40 calls, max_output 4096, planned QLoRA + rejection sampling | plan only | budgets |
| ns-0437 | coder + analyzer | measured 0.06 twice | evidence against multi-agent default (1 team) |
| bbkdevops "CIGS-Delta" | thinking 8192, max_output 16384 | "SOTA" claim, no measured score | no; conflicts with App. B |
Leaderboard: prompt-only configs cluster 0.10–0.17 [3p]. I found no published verified-trajectory SFT result.

## 7. Why this should be more efficient
Time, not context, binds: one public datapoint reports ~15 tok/s decode on 4×L4 (discussion title only) [3p]. At 15–40 tok/s a 270 s task affords roughly 3–10K output tokens and 8–26 turns [calc]. Architecture comparison:
| Option | Extra loops | Cost [calc] | Evidence | Verdict |
|---|---|---|---|---|
| A root + playbook | 0 (+1–2 turns if a file is loaded) | ~10–25 s | prompt-only configs lead | **chosen** |
| B + conditional investigator | 1 sub-loop | ~60–120 s | 0.06 ×2 | no |
| C + graph investigator | 1 sub-loop, big outputs | same | none | no; graph tools stay with the root, gated (LOW only, ≤4 symbols, `max_neighbors=8`) |
| D + reviewer | 1 loop at end | ~30–60 s | none; cannot run hidden tests | no; replaced by a one-call gate |
`get_code_subgraph` is kept declared, not removed. Whether it helps hard tasks cannot be measured here; test LOW-confidence tasks with and without it.

## 8. Tool calls (design targets, not measurements)
Fast path ≈ 8–10 calls; deep path ≤ 18; first `submit_patch` at call ≈ 4–8 (VNEXT: ≤ 30). Batching and exact-anchor grep (docs excluded) cut turns; `search_similar_code` only on symbols/short phrases (k=5).

## 9. Reasoning quality
Thinking stays off, so the ledger is the only visible reasoning (~80 tokens). Expect fewer search→guess→edit→fail cycles and fewer repeated identical failures. The cost is a longer prompt (7.4 KB vs 5.1 KB, ~+550 tokens, likely prefix-cached); instruction overload is a real risk [judgment].

## 10. Patch correctness
Gate: production code changed, files related, minimal, old API kept, relevant test passed, symptom gone, no protected/test files, no scratch (`git add -N .` would include untracked files). F-class check uses `git stash -q; CMD; git stash pop -q`. Effect on pass rate: unmeasured.

## 11. Generation config
`temperature 0.2, top_p 0.95, top_k 40` unchanged (no evidence to change; keeps attribution clean). `max_output_tokens 4096 → 3072`. `thinking_config.include_thoughts: false` unchanged (maps to thinking off [3p]).
Why 3072: it bounds one runaway generation (Gemma 4 loops/malformed calls are documented in long agentic contexts) at ~205 s @15 tok/s instead of ~273 s, while legit non-thinking outputs (edits) stay well under 1.5K tokens. 8192+ lets one bad generation eat 2–4 whole task budgets at 15 tok/s (App. B). Thinking on: 1,000 thought tokens ≈ 25–67 s; budget unenforced [3p]; template re-injection loops reported on HF. A larger cap helps only if outputs are legitimately long, which this prompt discourages. These are expected-cost arguments, not measurements.

## 12. Budget strategy
`eval_config`: 4.5 min, 40 calls, 70 turns, `timeout_seconds` 120 → 300. 12 h worst case: N=120: 9.5/10.0/11.0 h; N=125: 9.9/10.4/11.5 h for setup 15/30/60 s [calc]; a final generation can overrun the cap, so I did not raise 4.5 min. Agent-side `timeout 90` guards its own commands. FAST/DEEP paths via HIGH/MEDIUM/LOW; `get_status` after localization and each failure; >60% used → stop exploring.

## 13. Adapter decision: none
84 tasks yield at best ~10 verified agent trajectories per sweep (≈6 h per sweep at 4.5 min × 84; ~10–15% resolve); too few for a LoRA, and gold patches alone do not teach the harness's tool-call format. Training against bf16 then serving on w4a16 plus Gemma-4 LoRA serving bugs and the possible adapter wipe make an unverified adapter a risk. Revisit only with ≥300 verified trajectories in the exact tool format, LoRA r=16–32 (alpha=2r) on language-tower attention+MLP projections only, and proof the adapter changes outputs in a scorer-like vLLM. No placeholder adapter shipped.

## 14. Validation performed
Done: `tools/validate_submission.py` on directory and zip — one root `agent.yaml`, model string, tool names, `!include` paths (no `..`), skill dir/name/frontmatter/kebab-case, reference-file ↔ router consistency, allowed extensions (.yaml .yml .md .txt .py .json .safetensors [3p]), no symlinks/traversal, no ADK `{placeholder}` braces in the prompt, size, 12 h projection, prompt lint, diff vs VNEXT; `unzip -t`; miner self-test (synthetic rows; poisoned non-train row skipped; train/val overlap aborts).
Not done: official compile, any model run, any task run, any score. **No 22/22-style claim is made.**

## 15. Remaining uncertainties
- Cause of the 0.00 and which zip it belongs to.
- Harness details I could not read: default budgets, context compaction (reports differ: none vs 14,336-token threshold), `get_status` format, what happens to the patch at timeout.
- Whether `references/` is the directory `load_skill_resource` reads, and whether ADK's own skill instruction makes Gemma load the skill on every task (+1–2 turns).
- Decode speed (15 tok/s is one title-only datapoint); all time numbers hinge on it.
- Compliance of a 31B non-thinking model with a 7.4 KB prompt; if ablations show no gain, drop the FAMILIES block (−1.7 KB).
- Noise: 1 public task ≈ 0.017, public LB ≈ 50% of tests; final standing uses the other half.

## Appendix A — files
`agent.yaml`, `eval_config.yaml`, `configs/sampling.yaml`, `prompts/system.md`, `skills/repo-repair-playbook/SKILL.md` + 10 `references/*.md` (5.3 KB total). 15 files, 9,856 B zipped. Changed vs VNEXT: all four original files; added: skill; removed: none.

## Appendix B — time arithmetic [calc]
Full-length generation time and share of a 270 s task:
| max_output_tokens | 15 tok/s | 25 tok/s | 40 tok/s |
|---|---|---|---|
| 2048 | 137 s (51%) | 82 s (30%) | 51 s (19%) |
| 3072 | 205 s (76%) | 123 s (46%) | 77 s (28%) |
| 4096 | 273 s (101%) | 164 s (61%) | 102 s (38%) |
| 8192 | 546 s (202%) | 328 s (121%) | 205 s (76%) |
| 12288 | 819 s (303%) | 492 s (182%) | 307 s (114%) |
| 16384 | 1092 s (405%) | 655 s (243%) | 410 s (152%) |
Turns in 270 s (prefill 1,500 new tokens at 1,200 tok/s; 6 s tool):
| output tokens/turn | 15 tok/s | 25 tok/s | 40 tok/s |
|---|---|---|---|
| 120 | 17.7 | 22.4 | 26.3 |
| 250 | 11.3 | 15.7 | 20.0 |
| 400 | 8.0 | 11.6 | 15.7 |

## Appendix C — cheapest next measurements
1. Run VNEXT and VNEXT2 on the 22 validation tasks in the official harness (Kaggle 4×L4 notebook); log per task: calls, wall time, first-submit call index, termination reason, patch non-empty. Gross differences only (≈0 vs ≥3 passes) are detectable at n=22.
2. Run `mine_train_priors.py` on `tasks.jsonl` + your 84 train IDs; reorder/prune the families.
3. Then ablate one thing at a time: FAMILIES block, `get_code_subgraph`, checkpoint submit.
