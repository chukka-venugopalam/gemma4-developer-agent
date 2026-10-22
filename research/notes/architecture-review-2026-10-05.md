## 1. CURRENT ARCHITECTURE

**What the ZIP is.** It is one root LlmAgent, `gemma_swe_hybrid`, with no sub-agents and no adapters. It has nine tools and one skill (`repo-repair-playbook`, 11 reference notes). Sampling is T 0.2, top_p 0.95, top_k 40, thinking off, max output 4096. The limits are 4.5 min, 50 calls, 80 turns and 300 s per command.

**What the model sees every turn.** It sees system.md (\~2.1k tokens), the nine tool schemas and the skill's name and description. The skill body and references cost a call each to read.

**What the prompt makes it do.** The prompt defines a ten-step protocol:

1. extract anchors
2. localize (search, then `get_code_neighbors` after any credible symbol)
3. an "internal" six-item evidence ledger
4. optionally load a skill reference
5. optional repro
6. edit, with a reread before every `edit_file`
7. a diff inspection after every edit
8. focused test
9. a three-part git check
10. one `submit_patch` at the very end

**Conflicts inside the prompt** (these shape behavior):

1. Prose is capped at two lines, but the model is told to keep an internal six-item ledger. With thinking off, there is nowhere for that reasoning to live.
2. The "deep path" is up to 18–20 calls. At a plausible 15–20 s per turn (my estimate), 4.5 minutes allows about 12–18 turns, so the deep path cannot finish.
3. "Never edit tests" sits next to STEP 7's "focused regression test → edit", which a model can read as "write a test first".
4. Submission is final and single, while the prompt hedges that the harness "may end the session" and that diff recovery "exists". There is no banked patch.
5. "At \~60% of time/calls" has no observable counter. `get_status` is "when budget matters", with no trigger.
6. HIGH/MEDIUM/LOW gates are referenced (subgraph only at LOW) but never defined.
7. "No scratch in /workspace" has no mechanism. `write_file` resolves inside /workspace and untracked files land in the patch.
8. Searches assume `rg`, and `rg` may not exist in the sandbox.
9. Duplicated blocks: the lint block repeats the failure classes, the subgraph rule and the submit rule, and the router repeats the skill.

## 2. FAILURE ANALYSIS

These are priors, not measurements. I have no traces of the 0.06 run, so Phase 0 should replace the percentages with counts. Shares are my estimate of the \~54 lost tasks.

| Rank | Category (your numbering)                      | Est. share of losses | Mechanism in this ZIP                                                                                               | Scaffold-fixable? |
| ---- | ---------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 1    | Root-cause reasoning (4)                       | \~18%                | non-thinking model goes from read straight to edit; no visible reasoning before the edit                            | partly            |
| 2    | Tool-budget exhaustion + over-analysis (8, 11) | \~17%                | 3–5 ceremony calls on the fast path, an infeasible deep path, no banked patch, no repeat guard for empty searches   | yes               |
| 3    | Editing + API/interface mismatch (5, 13)       | \~15%                | near-miss patches; no rule to use the issue's exact names and messages, which hidden tests assert                   | yes               |
| 4    | Localization + navigation (2, 3)               | \~12%                | hotspot priors fitted to 4 dev repos while hidden tasks come from private repos; weak graph; `rg` risk              | mostly            |
| 5    | Context pollution (9)                          | \~8%                 | prompt weight, 150-line reads and neighbor dumps reach the \~14k compaction threshold; compaction blurs exact names | yes               |
| 6    | Validation (6)                                 | \~8%                 | repro is optional; existing tests rarely cover the hidden behavior; wrong test selection                            | yes               |
| 7    | Premature stopping (10)                        | \~6%                 | a text-only reply ends the run; the prompt only warns                                                               | partly            |
| 8    | Recovery after failure (7)                     | \~5%                 | "same failure twice" has no mechanics and usually no time left                                                      | partly            |
| 9    | Regression introduction (14)                   | \~4%                 | no explicit old-behavior check                                                                                      | yes               |
| 10   | Task understanding (1)                         | \~4%                 | issue appears once; blurred after compaction                                                                        | yes               |
| 11   | Wrong-file modification (12)                   | \~3%                 | stale hotspot hints; no scope gate                                                                                  | yes               |

Roughly a third of the losses are process-bound (ranks 2, 5, 7 and part of 6). About another third are capability-bound (ranks 1 and 3). The rest is localization, validation and recovery. Scaffold work can plausibly convert a few of the process-bound tasks and some near-miss edits. It cannot fix the reasoning-bound ones.

## 3. COMPETITOR GAP

A 0.15–0.24 agent solves about 9–14 of 58 tasks, versus about 4 for you. Four caveats shape how to read that.

- I have not seen any 0.17–0.24 configuration, so everything below is inference.
- The leaderboard top is partly selection noise. The pool is about 1,300 teams with thousands of submissions, so the true skill of the top entries is probably lower than the displayed maximum.
- A realistic competitive target is 0.12–0.15, with 0.24 as the luck-plus-skill ceiling.
- Public data points from my last report apply here. The same design scored 0.12 uncapped and 0.08 under a hard 4-minute cap. Non-thinking Gemma was seen repeating a call 10–80 times on empty output. Minimal single agents score 0.05–0.08, which is where you sit.

What a leader probably does better, in rough order:

1. **Higher patch yield.** Nearly every task ends with a clean, non-empty, applicable patch. A task with no patch cannot pass, so yield multiplies everything else.
2. **Shorter time to first edit** and a median task under about 3 minutes, which leaves room for one repair cycle.
3. **Near-miss control.** Exact names, parameters and messages from the issue, and a repro that mimics the hidden test's assertion style.
4. **A reasoning step before the edit.** This is the one place a non-thinking model gets to reason. Leaders either spend tokens there, use selective thinking, or are adapted or trained.
5. **No loops, no scratch pollution, no compaction surprises.**

Items 1, 2, 3 and 5 are scaffold work and are in this plan. Item 4 is only partly covered: the `WHY/FIX/ASSERT` lines are a cheap substitute. Beyond that it needs thinking or training, which are gated experiments (see §7).

## 4. ARCHITECTURE OPTIONS

| Option                                           | Model loops / time (est.)                 | What it buys                                      | Verdict                                                                        |
| ------------------------------------------------ | ----------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1. Current sequential                            | 1 loop, 12–20 turns                       | nothing beyond baseline                           | baseline, measured 0.06                                                        |
| 2. Investigator → coder → reviewer               | 3 loops, +100–150 s                       | context isolation, but a second-guessing reviewer | reject the reviewer, keep the investigator conditional                         |
| 3. Single agent, structured phases               | 1 loop                                    | clarity                                           | adopt as the root, slimmed (the current weight is the problem, not the phases) |
| 4. Parallel hypotheses → synthesis → implement   | 3–4 loops, +120–200 s                     | diversity                                         | reject: runs sequentially in practice and blows the time cap                   |
| 5. Adaptive task-type routing                    | 0 extra loops                             | spends depth only where uncertain                 | adopt, by observable triggers                                                  |
| 6. Cheap investigation → focused implementation  | 2 loops                                   | context isolation and clean localization          | adopt as the NORMAL/DEEP path                                                  |
| 7. Implementation-first with targeted validation | 1 loop, fastest                           | lowest latency                                    | adopt only as the FAST path (strong anchors)                                   |
| 8. Hybrid of 3 + 5 + 6 + 7                       | FAST ≈ option 1's cost, DEEP ≈ option 6's | highest expected solved tasks per second          | **selected**                                                                   |

**Reviewer.** A separate reviewer sub-agent never pays for itself. It costs about 40–60 s of a \~300 s budget, a non-thinking 31B model has weak discriminative power over its own diff, and a reviewer tends to cause patch churn. The review function is covered for free instead:

- **Before editing:** the `ASSERT:` line forces a self-review of what a hidden test would check.
- **After editing:** a deterministic gate runs inside the verify command (files changed, scope, untracked files, diff size).
- **Low confidence:** low-confidence tasks are exactly the time-starved ones, so extra review is skipped.

**Sub-agents.** Keep exactly one, the read-only `investigator`, and it must earn its place in Phase 2. Without a measured gain it is removed.

**State machine and the adaptive rules I would include** (each has an observable trigger and a mechanism):

- INIT → LOCALIZE: the first call is `git grep` with the anchors.
- LOCALIZE → HYPOTHESIS: the definition is read and the cause can be stated, or the investigator returned. Stop broad search once the target file is known.
- HYPOTHESIS → IMPLEMENT: after the three `WHY/FIX/ASSERT` lines.
- IMPLEMENT → VALIDATE: after each edit.
- VALIDATE → STOP: repro passes, nearest test passes or is environment-excluded, and the gate is clean. Submit.
- VALIDATE → RECOVER: failure signals per the verify table. RECOVER is limited to two cycles. The third failure reverts the last hunk and submits the earlier state.
- Three searches in a row with no new fact: switch strategy (investigator, or edit the best candidate).
- Over 70% of the budget used: stop exploring and finish.
- Never end with an empty diff. If time is nearly out and a diff compiles, submit it, since an empty diff cannot pass.
- Rules I excluded: "if the symbol is found, inspect neighbors" (mandatory graph calls cost calls without evidence of benefit) and any rule that needs the model to judge its own confidence.

## 5. SELECTED HYBRID ARCHITECTURE

**One root agent, a structured-phase prompt of about 1.1k tokens, and one conditional read-only investigator.**

- **Root tools (six):** `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`, plus the `investigator` agent-tool. The three graph tools move to the investigator.
- **Paths by trigger:**
  - FAST (strong anchors, one definition): about 8 calls.
  - NORMAL (2–4 candidates, or a shared helper): about 12 calls, with one investigator call.
  - DEEP (no anchor hits, multi-layer propagation, or a failed hypothesis): about 16 calls, repro first.
- **Early banking:** submit after the first verified edit and resubmit after later edits.
- **Single combined verify-and-gate command** per edit, replacing the reread, the diff-after-every-edit and the three-part final check.
- **No skills, no adapters, no reviewer sub-agent.**

**Why this maximizes expected solves:** it raises the share of tasks that end in a clean patch, since the time cap is the binding constraint. It adds only one extra model loop, and only on tasks that need it. It also keeps the root context under the compaction threshold and adds a cheap reasoning step where the model otherwise has none.

## 6. EXACT IMPLEMENTATION PLAN

Change register. C-numbers are referenced in §8.

| #   | Current → problem                                                                                      | Proposed behavior                                                                                                            | Why it should raise solves                                                              | Downside                                                                                | File · action                                                |
| --- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| C1  | 2.1k-token, 10-step prompt with duplicates and a silent ledger                                         | \~1.1k-token prompt: rules, paths, workflow, repro by type, verify table, patch gate, STATE, budget                          | frees about 1k tokens per turn and removes contradictions                               | less guidance for rare cases                                                            | `prompts/system.md` · rewrite                                |
| C2  | repetition rule only for failing tests; `rg` assumed                                                   | `git grep -n`; every search ends with `; echo "[exit=$?]"`; no identical command; switch pattern class after an empty result | removes the empty-output loop trigger and the `rg` risk                                 | none material                                                                           | `prompts/system.md` · rewrite                                |
| C3  | single submit at the very end                                                                          | submit after the first verified edit; resubmit after changes                                                                 | a time-out no longer loses a good patch                                                 | if the harness ends the session on submit, no refinement (mitigated by verifying first) | `prompts/system.md` · rewrite                                |
| C4  | reread before every edit; diff after every edit; three-part git check                                  | one verify-and-gate command per edit                                                                                         | saves 3–5 turns per task                                                                | slightly less per-edit inspection                                                       | `prompts/system.md` · rewrite                                |
| C5  | /tmp scratch rule with no mechanism                                                                    | scratch only via `run_command` heredoc under /tmp; `write_file` only for a new production file                               | keeps untracked files out of the patch                                                  | none                                                                                    | `prompts/system.md` · rewrite                                |
| C6  | no visible reasoning before the edit                                                                   | three lines before the first edit: `WHY`, `FIX`, `ASSERT`                                                                    | the only place a non-thinking model gets to reason; `ASSERT` targets interface fidelity | \~60–80 tokens (\~3 s)                                                                  | `prompts/system.md` · add                                    |
| C7  | no exact-name rule; vague scope rules                                                                  | use the issue's exact names and messages; numeric patch-gate limits                                                          | near-miss patches are a main loss mode                                                  | may over-constrain an unusual task                                                      | `prompts/system.md` · add                                    |
| C8  | no context isolation                                                                                   | read-only `investigator` agent-tool, ≤4 calls, fixed return schema                                                           | keeps root context small on NORMAL/DEEP tasks                                           | +1 loop (\~10–20 s) and a possible wrong report                                         | `agent.yaml` · rewrite; `sub_agents/investigator.yaml` · add |
| C9  | graph steps default on; the graph is weak (calls-only edges, no async; one team saw it return nothing) | graph tools only in the investigator, behind three gates                                                                     | avoids empty and slow graph calls                                                       | misses some dependency hints                                                            | `agent.yaml`, `sub_agents/investigator.yaml`                 |
| C10 | 11-file skill duplicating the prompt, tied to dev repos                                                | delete                                                                                                                       | removes 2 calls per use and misleading priors                                           | loses the generic heuristics                                                            | `skills/` · remove; `agent.yaml` · drop `skills:`            |
| C11 | 4096 max output                                                                                        | 2048                                                                                                                         | one runaway turn can no longer burn minutes                                             | a very long edit could truncate                                                         | `configs/sampling.yaml` · rewrite                            |
| C12 | 4.5 min cap                                                                                            | 5.0 min (120 × 5.0 = 10.0 h worst case; keep 4.5 if setup exceeds \~60 s per task)                                           | more tasks reach a patch                                                                | 12-hour limit risk if misjudged (a breach errors the whole run)                         | `eval_config.yaml` · rewrite                                 |
| C13 | failure classes A–G, duplicated                                                                        | six outcomes keyed to output patterns, in the verify table                                                                   | drives the next action                                                                  | none                                                                                    | `prompts/system.md` · rewrite                                |
| C14 | STATE lacks the exact names                                                                            | `STATE:` with `NAMES=` re-emitted after every test result                                                                    | survives compaction                                                                     | \~30 tokens per emission                                                                | `prompts/system.md` · rewrite                                |

**Rejected, with reasons:**

- A separate reviewer sub-agent (cost, weak signal, churn).
- Parallel hypotheses (time).
- Adapters for now (no demonstrated inference-time benefit yet; the data is thin and they cost KV memory).
- New skills (generic advice, call overhead).
- Thinking on by default (no evidence it fits the time cap).
- Graph-first localization (weak graph).

## 7. EXPECTED EFFECT

These are conservative judgments, not measurements. Noise is ±0.04, so a single result cannot confirm or refute them.

| Group                                                              | Mechanism                         | Estimated effect                        |
| ------------------------------------------------------------------ | --------------------------------- | --------------------------------------- |
| C2–C5, C11, C12 (time and hygiene)                                 | more tasks reach a clean patch    | +1 to +2 tasks                          |
| C6, C7, C13 (pre-edit reasoning, interface fidelity, verify table) | fewer near-miss patches           | +0 to +2 tasks                          |
| C8, C9 (investigator)                                              | context isolation on harder tasks | +0 to +1 task                           |
| C1, C10, C14 (leaner prompt, no skill)                             | recovered time and context        | \~0 by themselves; they remove downside |

**Total:** +1 to +4 tasks, so 0.07–0.12 with a central estimate near 0.10. I put ≥0.10 slightly better than even and ≥0.15 at roughly one in six.

**What this does not close.** None of this explains the whole gap to 0.24. What remains is reasoning and edit quality (capability-bound). After Phase 2 I would test, as gated experiments: selective thinking for the `WHY/FIX` step, repetition penalties in the sampling config, and an adapter under the earlier gates. Each stays out of the next submission unless a paired run shows it helps.

## 8. IMPLEMENTATION INSTRUCTIONS

Do not modify the original ZIP. Work in a copy.

1. Copy the extracted original into `submission_v2/`. Keep the layout with `agent.yaml` at the ZIP root.
2. Delete `submission_v2/skills/` entirely.
3. Overwrite or create exactly these files with the contents below: `agent.yaml`, `eval_config.yaml`, `configs/sampling.yaml`, `prompts/system.md`, `sub_agents/investigator.yaml`. No other files may exist except what the original had at those paths (`prompts/investigator.md` is not used; the investigator's instruction is inline to avoid include-path ambiguity).
4. Validate before zipping:
   - Every YAML parses.
   - No `{` or `}` appears in `prompts/system.md` or in the instruction text of `sub_agents/investigator.yaml`. ADK templates `{word}` in instructions.
   - Tool names are spelled exactly.
   - Only `.yaml` and `.md` files exist.
   - Estimate system.md tokens as characters ÷ 4 and trim to ≤1.2k if above.
5. Run the same official compiler/validator you used for the current ZIP. If it rejects the `agent_tool` entry, copy the exact `agent_tool` and `config_path` form from `sample_submission/agent.yaml` and change nothing else.
6. Smoke test on 3 dev tasks. Confirm:
   - The root can call `investigator`. The tool argument is normally `request`; if the argument name differs, edit that one word in the prompt.
   - `git grep` works.
   - A heredoc under /tmp does not appear in `git status`.
7. Zip from inside the folder so `agent.yaml` sits at the archive root: `cd submission_v2 && zip -r ../submission_v2.zip . -x '.*'`.
8. Do not submit to Kaggle until the Phase 0 and Phase 1 checks from my previous report are done. In particular, read HARNESS_README for the submit_patch semantics, what is captured at the time cap, the exact grader pytest flags and whether `rg` exists.
9. Rollback: if Phase 1 KPIs (time-cap hits, calls to first edit, identical-call streak, stray files) don't improve over the current ZIP, stop and review the traces before adding the investigator.

**`agent.yaml`**

```yaml
agent_class: LlmAgent
name: gemma_swe_hybrid
model: gemma-4-31b-it-qat-w4a16-ct
description: >
  Repository repair agent: adaptive-depth search, smallest correct patch,
  verified and submitted early.
instruction: !include prompts/system.md
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
generate_content_config: !include configs/sampling.yaml

```

**`eval_config.yaml`**

```yaml
evaluation:
  timeout_seconds: 300
  max_tool_calls: 50
  max_time_minutes: 5.0
  max_turns: 80

```

**`configs/sampling.yaml`**

```yaml
temperature: 0.2
top_p: 0.95
top_k: 40
max_output_tokens: 2048
thinking_config:
  include_thoughts: false

```

**`sub_agents/investigator.yaml`**

```yaml
agent_class: LlmAgent
name: investigator
model: gemma-4-31b-it-qat-w4a16-ct
description: >
  Read-only code locator. Input: anchors and symptom in under 100 words.
  Output: FILE, SYMBOL, WHY, CALLERS, TESTS, CONF, ALT.
instruction: |
  You are a read-only code locator for a repository repair task. Never edit or
  create files and never run git checkout, stash or apply. You have at most 4
  tool calls.
  Input: a short request with anchors and the symptom.
  Method:
  1. Search with git grep -n -I -e ANCHOR -- '*.py'. End every search command
     with: ; echo "[exit=$?]". Never repeat a command. After an empty result
     change the pattern: symbol, then error text, then test name, then file name.
  2. Find the def or class line in non-test code. Read at most 100 lines around it.
  3. Callers: git grep -n "NAME(" -- '*.py' | head -15
  4. Graph tools only if the target is a sync function with 3+ callers in 2+
     files, or the issue is about a value passed through layers.
     get_code_neighbors(node, edge_type='calls', max_neighbors=6): copy the node
     id from a tool result or build it as dotted module path plus qualname. If
     not found or empty, stop using graph tools. Use get_code_subgraph at most
     once and only with 2-4 known symbols. Use search_similar_code only after
     two text searches found nothing, with a 3-6 word behavior phrase.
  5. Tests: git grep -l SYMBOL -- 'tests*' | head -5
  Return exactly these lines, under 120 words:
  FILE: path:startline-endline
  SYMBOL: qualified name
  WHY: one sentence naming the cause and the line you read
  CALLERS: up to 3 as path:line
  TESTS: up to 2 test file paths
  CONF: HIGH if you read the definition and a distinctive anchor is in the same function, otherwise LOW
  ALT: one alternative file::symbol, or none
  If no definition is found in 4 calls, return CONF: LOW with the two best
  candidates and what you searched.
tools:
  - run_command
  - read_file
  - search_similar_code
  - get_code_neighbors
  - get_code_subgraph
generate_content_config:
  temperature: 0.2
  top_p: 0.95
  top_k: 40
  max_output_tokens: 1024
  thinking_config:
    include_thoughts: false

```

**`prompts/system.md`**

```
You are an autonomous software engineer fixing one repository issue. A hidden test suite decides success. Work only in /workspace; the environment is offline, so never install anything. The task text arrives as the user message.

RULES
1. Every turn must contain a tool call. A text-only reply ends the run, so reply without a tool call only after submit_patch has returned.
2. Prose before a tool call: one line, except the three-line analysis and the STATE line.
3. Never edit tests, conftest.py, pytest.ini, setup.cfg, tox.ini or pyproject.toml.
4. Scratch files only through run_command heredocs under /tmp. write_file writes inside /workspace and pollutes the patch, so use it only for a new production file.
5. Search with git grep -n. End every search command with: ; echo "[exit=$?]". An empty result is information, not a reason to repeat.
6. Never run an identical command twice. After an empty result change the pattern: symbol, then error text, then test name, then file name.
7. Read at most 120 lines per read_file. Do not reread text already in context.
8. Use the issue's exact identifiers, parameter names, exception types and message text. Hidden tests assert them.

PATHS (decide after at most 2 searches)
FAST: the issue names an exact symbol or error text, one non-test definition is found, and the change is local to one function. Max 8 calls.
NORMAL: 2-4 candidate files, or the target has 3+ non-test callers in 2+ files, or the issue describes behavior without identifiers. Call investigator once, then continue. Max 12 calls.
DEEP: two searches found no definition, or the value passes through 3+ layers, or a sync/async or class/function twin is likely, or the repro still fails after one revised hypothesis. Call investigator, write the repro first and run it before editing. Max 16 calls.
Move up a path when its trigger appears. Move down only when investigator returns one HIGH candidate.
investigator(request): pass 2-4 anchors and the symptom in under 100 words. It returns FILE, SYMBOL, WHY, CALLERS, TESTS, CONF, ALT. Never ask it the same question twice.

WORKFLOW
1. Anchors: pick 2-4 exact identifiers, error strings, parameters or test names from the issue.
2. Locate: git grep, then read the definition and only the nearest test. Stop exploring once you can say which function is wrong and why. Three searches in a row with no new fact means call investigator or edit the best candidate.
3. In the same turn as the first edit_file call write exactly three lines:
   WHY: root cause with the evidence line
   FIX: file::symbol - the smallest change
   ASSERT: what a hidden test would check (names, messages, values)
4. Edit with edit_file using a short unique old_string from your latest read. If it fails, reread 10 lines around it and retry once.
5. Verify once per edit with a single command (see VERIFY).
6. Submit as soon as verify passes, then reply in one sentence. If you change code afterwards, verify again and call submit_patch again. Never end with an empty diff: if time is nearly out and the diff compiles, submit it.

REPRO by issue type (create /tmp/repro.py with a heredoc inside the verify command)
Wrong output or crash: run the issue's own example.
New parameter, function or option: call it with the issue's exact name and confirm old calls still work.
Error or validation: assert the exception type and message text.
Typing or compatibility: import the module and exercise old and new call forms.

VERIFY
cd /workspace && python3 -m py_compile FILES && python3 /tmp/repro.py; echo "[repro exit=$?]"; timeout 90 env PYTHONSAFEPATH=1 PYTHONNOUSERSITE=1 python3 -s -m pytest TESTFILE -p no:anyio -o 'python_classes=Test* *Test' -x -q --tb=short 2>&1 | tail -35; git status --short; git diff --stat
Find TESTFILE with: git grep -l SYMBOL -- 'tests*'
Act on the result:
- SyntaxError or ImportError from your lines: fix that hunk only.
- ModuleNotFoundError outside your diff: environment problem, rely on the repro.
- No tests ran: find the right test file once, otherwise rely on the repro.
- Repro still shows the old symptom: wrong target or the path is not executed. Print func.__code__.co_filename, try investigator's ALT, revert the hunk.
- Different assertion in code you touched: incomplete fix. Check twin paths and exports, revise once.
- Failure with no frame in your changed files: pre-existing, ignore.
- A previously passing test now fails through your function: regression. Keep old behavior by default or branch.
- Same failure twice: change the hypothesis. Third time: revert the last hunk and submit the earlier state.

PATCH GATE
Only files needed for the fix. No test files, no untracked scratch, no whitespace-only hunks, no import reordering, no refactors. FAST patches stay under about 40 changed lines in at most 2 files; above 80 lines or 3 files, shrink or justify. New parameters are keyword arguments with defaults, added last. Keep return types and old-input behavior. Handle None and empty input when the issue's domain suggests it.

STATE
After the first edit and after every test result emit one line before the next tool call:
STATE: FIX=file::symbol | NAMES=exact issue strings | EDIT=yes/no | TEST=short result
Context may be compacted; this line keeps the exact names.

BUDGET
Call get_status once right after the first edit. If it shows more than 70% of the time or call budget used, stop exploring and submit the best verified state. Do not spend remaining time on cosmetic work.

```

Several details are unverified and should be checked at implementation: the `agent_tool` syntax, the investigator's argument name, the grader's exact pytest flags, `rg` and `git` availability, and what the harness captures on a time-out or on repeated `submit_patch` calls. The plan assumes the worst case for each.
