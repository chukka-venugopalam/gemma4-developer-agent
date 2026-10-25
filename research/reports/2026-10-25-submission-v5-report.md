# Today's submission — 25 October 2026

## Candidate

**Budget-Fit Reference-Aligned V5** is an independently written candidate matching the most completely documented public Budget-Fit configuration reviewed so far. It is not the original author’s ZIP.

- Model: `gemma-4-31b-it-qat-w4a16-ct`
- Root agent: one
- Tools: six (`run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`)
- Sampling: temperature 0.2, top-p 0.95, top-k 40
- Maximum output tokens: 8,192
- Thinking: enabled, budget 4,096, thoughts retained
- Per-task budget: 8 minutes, 28 tool calls, 80 turns
- `timeout_seconds`: 240
- ZIP size: 2885 bytes
- SHA-256: `d9b913d6a401582dd07f3c16e08ff1adb9e7869255478a8c01366bb2c9aba454`

## Why it differs from V4

The previous V4 ZIP declared all nine tools and allowed 100 turns. V5 removes unused graph/similarity tools and follows the documented six-tool configuration, caps turns at 80, uses the reported 240-second command timeout, and makes the early-edit-by-about-call-12 policy explicit. It also enforces one focused validation check and at most one repair attempt. It does not add a sub-agent, skill, LoRA, or separate retrieval layer.

## Evidence and target

The attached evidence shows two successful recent user submissions with displayed scores of 0.18 and a public leaderboard snapshot with four entries at 0.24. Those screenshots are not linked to archive hashes. A newly indexed Kaggle notebook has the title “What Took LB 0.12 to 0.24”, but the full notebook content was not available in this research session; its title is not treated as an explanation of the score. The architecture behind the 0.20–0.24 entries is not verified.

The known Budget-Fit recipe has public score records around 0.18 (with one separate same-config report at 0.13), but no controlled ablation isolates which setting matters. V5 is the best-documented baseline-aligned candidate we can make from current evidence; no score above 0.18 or 0.24 is promised.

## Validation state

- Local structural validation: PASS
- Required root files / include targets: PASS
- YAML parsing and evaluation schema: PASS
- Prompt curly-brace scan: PASS
- Allowed extensions and safe ZIP paths: PASS
- Deterministic build: PASS
- Repository tests: 4/4 PASS
- Official current-wheelhouse compiler: NOT TESTED
- Current tool/argument replay: NOT TESTED
- Real Gemma inference: NOT TESTED
- Hosted Kaggle score: UNKNOWN

**Recommendation:** run the current-wheelhouse preflight and one bounded real Gemma smoke test before using a scored submission opportunity.

## Sources checked on 2026-10-25

- Verified methods research supplied with the task: `VERIFIED_METHODS_0_10_PLUS.md`
- Budget-disciplined method and configuration: https://github.com/sourabghosh108-cc1/gemma4-budget-disciplined-agent
- Budget-Fit variants and local paired-run caveats: https://github.com/TheWayLost/gemmacodeagent
- Official competition overview and rules: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview
- Current public leaderboard snapshot: https://www.kaggle.com/competitions/gemma-4-developer-agent/leaderboard
- Recent analysis notebook title (full content not retrieved): https://www.kaggle.com/code/hitarthjain0/gemma-4-agent-what-took-lb-0-12-0-24
- Publicly mirrored harness guide: https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md
