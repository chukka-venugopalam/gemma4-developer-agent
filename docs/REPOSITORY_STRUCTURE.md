# Repository Structure and Maintenance

```text
submission/                    Canonical editable candidate source
submissions/archive/           Immutable historical and candidate ZIPs
submissions/manifest.csv       Candidate hashes, sizes, aliases, attribution notes
research/reports/              Research, forensic, validation, and incident reports
research/prompts/              Research/implementation prompts and revisions
research/ablation/             Development-set plan and helper utilities
research/bundles/              Original research-output bundles
research/raw/                  Raw command output snapshots
research/evidence/screenshots/  Cropped and indexed status evidence
notebooks/preflight-s0/         Kaggle preflight notebook and run order
evaluation/logs/                Captured preflight outputs
evaluation/results/             Score observations and experiment registry
tools/                          Build, validation, registration, and inventory tools
docs/                           Status, findings, policies, procedures, and decisions
```

## Single source of truth

Only edit `submission/` for the next candidate. Keep ZIPs in `submissions/archive/` immutable. `dist/` is generated locally and ignored by Git. The local build manifest is regenerated with `python tools/update_build_manifest.py`.

## New submission candidate

1. Edit `submission/`.
2. Run `python tools/validate_submission.py submission`.
3. Run `python tools/build_submission.py`.
4. Confirm the generated candidate hash and compare it with prior candidates.
5. Run official current-harness preflight in Kaggle before submission.
6. Register the exact ZIP with `tools/register_artifact.py`; never overwrite historical archives.
7. After the Kaggle run finishes, append its actual result to `evaluation/results/score_observations.csv`.

## New research result

Store the full source report in `research/reports/`, and keep its prompt in `research/prompts/` when applicable. Register it with `tools/register_artifact.py`, document the evidence level, and update `docs/RESEARCH_FINDINGS.md` only when the result changes a decision. Then update the build manifest and run the repository checks.
