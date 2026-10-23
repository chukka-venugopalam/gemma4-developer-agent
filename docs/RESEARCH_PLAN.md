# Research plan

## Completed desk research

- Public-agent and score-trend review.
- Archive forensic review of the historical VNEXT include defect.
- S0 structural preflight design.
- Budget-Fit/evaluator-change review on 2026-10-23.

## Remaining experiments

1. **Run-level incident forensics:** obtain the complete traceback for the latest `Notebook Threw Exception`; establish whether the error occurred before, during, or after agent evaluation.
2. **Official compile smoke test:** compile the exact current ZIP against the actual wheelhouse in Kaggle.
3. **Real Gemma smoke test:** one or two public development tasks, with saved tool traces and verifier outcomes.
4. **Paired reasoning ablation:** compare the previous thinking-disabled S0 with bounded reasoning on the same tasks/seeds. Measure solve outcomes, repeat streaks, malformed calls, patch capture, and elapsed time.
5. **Budget feasibility:** measure time distribution and estimate whether the 12-hour run can finish. Do not extrapolate from the per-task cap alone.
6. **Optional small-model track:** only after checking the live competition rules and pending/recorded small-model scores; keep a different final candidate if the bonus is pursued.

No new agent architecture should be added without a concrete observed failure and a test that can falsify the proposed fix.
