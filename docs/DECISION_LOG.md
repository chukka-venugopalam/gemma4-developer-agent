# Decision Log

| ID | Date | Decision | Rationale / evidence | Status |
|---|---|---|---|---|
| D-001 | 2026-10-05 | Keep one canonical `submission/` source | Prevent drift between hand-edited copies and ZIP artifacts | Active |
| D-002 | 2026-10-09/10 | Treat public-agent architecture claims as hypotheses unless source/bytes were inspected | Research report states upper leaderboard sources were inaccessible | Active |
| D-003 | 2026-10-10 | Preserve the VNEXT additive include fix as a historical candidate, not current winner | It passed an older loader, but Kaggle score linkage/current harness were not verified | Active |
| D-004 | 2026-10-15 | Do not claim S0 official compile success | Current official packages were unavailable in preflight environment | Active |
| D-005 | 2026-10-22 | Use Budget-Aware V2 as current editable candidate | Most recent locally assembled candidate, bounded budget and simple architecture; structural validation only | Active; pending Kaggle preflight |
| D-006 | TBD | Promote a candidate only after current-harness compilation and recorded results | Avoid spending submissions on structurally valid but unverified artifacts | Proposed gate |

## DEC-004 — Record the 2026-10-22 notebook exception without guessing its cause

Status: ACTIVE

The newest screenshot shows `Notebook Threw Exception` and the generic message that the notebook hit an unhandled error while rerunning code. No traceback, failing cell, submission ID, public score, or archive hash is visible. Record the event, but do not attribute it to a particular ZIP or infer that the agent itself caused it. Obtain the notebook traceback before changing the agent architecture.
