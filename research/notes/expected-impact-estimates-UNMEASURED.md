# 15. EXPECTED IMPACT

Estimates are judgments, not measurements, and the effects are not additive. They assume a public split of about 58 tasks, where one task is worth about 0.017.

| Change | Mechanism | Estimated effect |
|---|---|---|
| Anti-loop rules, early banking, less ceremony, 5.0 min cap | more tasks reach a patch before the time cap | +1 to +3 tasks |
| Read-only investigator (context isolation) | no mid-task compaction on the main path; cleaner localization | 0 to +2 tasks |
| Scratch rule, interface-fidelity rule, patch-quality gate | fewer polluted or near-miss patches | 0 to +2 tasks |
| Dropping dev-repo priors and the skill | removes misleading and wasted calls | about 0; removes downside |

## Projected range

- Current: 0.06.
- After the plan: roughly 0.09 to 0.13.

## Rough odds for the next submission

These are judgment calls, not guarantees.

- 0.10 or higher: somewhat better than even.
- 0.15 or higher: about one in five.
- 0.20 or higher: not from this plan alone; it would need training or luck.

## Noise caveat

Single-run noise on a ~58-task split is about ±0.04. A result between 0.07 and 0.14 is consistent with the same underlying agent, so judge changes by process KPIs (timeouts, calls to first edit, repeated-call streaks, stray files) and paired runs, not one leaderboard number.
