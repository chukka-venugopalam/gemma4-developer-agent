# Competition Reference (last checked: 2026-10-22)

Competition: **Google – The Gemma 4 Developer Agent Competition**.

## Verified public contract

- Required base model: `gemma-4-31b-it-qat-w4a16-ct` for every agent and sub-agent.
- Submission artifact is `submission.zip`, with `agent.yaml` at the archive root.
- Agent configuration is declarative YAML; tools/model are resolved from a closed host registry.
- Main scoring is patch-level pass/fail: a task resolves when the submitted patch applies and hidden validation passes.
- Overall patch-generation budget is 12 hours; per-task limits can be set in root `eval_config.yaml` under an `evaluation:` mapping.
- Current public page lists paper write-up deadline 2026-11-12, entry/team-merger deadline 2026-11-25, and main final submission deadline 2026-12-02. Always recheck the live rules before planning around a deadline.

## Primary links

- [Official Kaggle overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Official leaderboard](https://www.kaggle.com/competitions/gemma-4-developer-agent/leaderboard)
- [Official paper track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper)
- [Public harness guide mirror](https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md)
- [Public research: agent findings](../research/reports/public-agent-research-2026-10-10.md)

## Source quality warning

The official Kaggle pages are authoritative for current competition rules. The linked harness file is a public mirror, not a guarantee that the scorer's installed wheelhouse has the same revision. The research report labels third-party findings by evidence tier. Recompile with the current competition wheelhouse before relying on any version-specific behavior.
