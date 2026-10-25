# Changelog

## 2026-10-25 — Budget-Fit Reference-Aligned V5

- Canonical `submission/` now uses the best-documented six-tool Budget-Fit configuration reviewed in the supplied research.
- Added explicit contract-first localization, early evidence-backed edit, one focused check plus at most one repair, and bounded final review.
- Set 8 minutes / 28 tool calls / 80 turns and 240-second command timeout.
- Added the verified-methods report, V5 report, immutable source snapshot, candidate archive/hash manifest row, screenshots, and score-observation ledger.
- Added `tools/check_repo.py`, `tools/register_artifact.py`, and `docs/ADDING_ARTIFACTS.md` for ongoing maintenance.
- Local static validator/build and repository tests pass. Current official harness compilation, real Gemma inference, and V5 public score remain untested.
