# Engineering Decisions

## DEC-000 — Submission as source of truth

Status: ACTIVE

`submission/` is the canonical source used to construct the final
competition archive. Research and notebooks must not create unmanaged
copies of production submission files.


## DEC-001 — Use a reference-calibrated budget before adding complexity

Status: PROVISIONAL

The 2026-10-24 candidate uses the 28-call / 8-minute / 4,096-token reasoning envelope reported in the public Budget-Fit single-agent study. This is a reference-informed configuration, not the exact public reference bundle. Keep one root agent and conditionally use graph tools. No hosted score is attributed to this candidate. The next gate is current-wheelhouse preflight, followed by a bounded real Gemma smoke test.




## 2026-10-25 — Reference-aligned baseline before new complexity

**Decision:** V5 uses the documented six-tool Budget-Fit configuration and bounded edit/verification policy.

**Reason:** V4 had nine tools and 100 turns, while the highest-confidence published configuration uses six tools and 80 turns. The methods behind the current 0.24 leaderboard frontier were not available for verification.

**Not claimed:** V5 has no real Gemma run or hosted score yet; it is not claimed to beat 0.24.

**Next gate:** compile using the current official wheelhouse and perform a bounded real Gemma smoke test before any scored run.
