# Reference-Calibrated V4 — 2026-10-24

This directory records the source snapshot for the date's candidate. Canonical build source remains in the top-level `submission/` directory; do not edit both locations independently.

- Design: single root agent; all nine documented tools declared; conditional graph retrieval.
- Budget: eight minutes, 28 tool calls, 100 turns; 4,096 reasoning cap; 8,192 output tokens.
- Motivation: public reference settings and the Prompt 7 forensic findings, especially the need to avoid repeated calls and distinguish old-mirror tests from current scorer validation.
- Status: local static validation only. Official current wheelhouse compile, real Gemma inference, and leaderboard score not run.

See `research/reports/2026-10-24-reference-calibrated-v4.md` and `research/forensics/2026-10-24/prompt7/source_bundle/REPORT.md`.
