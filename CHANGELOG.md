# Changelog

## 2026-10-25 — Budget-Fit Reference-Aligned V5

- Canonical `submission/` now uses the best-documented six-tool Budget-Fit configuration reviewed in the supplied research.
- Added explicit contract-first localization, early evidence-backed edit, one focused check plus at most one repair, and bounded final review.
- Set 8 minutes / 28 tool calls / 80 turns and 240-second command timeout.
- Added the verified-methods report, V5 report, immutable source snapshot, candidate archive/hash manifest row, screenshots, and score-observation ledger.
- Added `tools/check_repo.py`, `tools/register_artifact.py`, and `docs/ADDING_ARTIFACTS.md` for ongoing maintenance.
- Local static validator/build and repository tests pass. Current official harness compilation, real Gemma inference, and V5 public score remain untested.

## 2026-10-26 — Evidence Repair V6

- Canonical `submission/` now uses all nine registered tools while making graph/code-intelligence calls conditional and symbol-grounded.
- Retained the reference-aligned temperature 0.2 / top-p 0.95 / top-k 40 / 8,192 output / 4,096 thinking envelope.
- Reworked the prompt around exact `edit_file` strings, rapid escape from repeated calls, narrow reproduction/verification, and final diff inspection.
- Added the V6 candidate archive, immutable source snapshot, SHA-256 manifest record, report, and 26 October score screenshot.
- Updated the stale tool-count unit test to assert the intended nine-tool registry; local tests now pass 4/4.
- Current official Kaggle compile, current-wheelhouse replay, real Gemma inference, and V6 hosted score remain NOT TESTED.
