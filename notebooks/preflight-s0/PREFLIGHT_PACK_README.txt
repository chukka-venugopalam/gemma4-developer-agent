GEMMA S0 preflight pack (diagnostics only)

DO NOT upload this pack to the competition. The only file that may ever be uploaded as a competition submission is
candidate/submission.zip, and only after the gate in GEMMA_S0_KAGGLE_RUN_ORDER.md reports SAFE TO TRY.

candidate/submission.zip   the S0 candidate, SHA-256 359a50986e9c23926cd99da853ad30fa399291947a9e9fc68b5906339156cf1b (four files, unchanged)
GEMMA_S0_PREFLIGHT_REPORT.md      what was run, what is blocked, evidence, risks
GEMMA_S0_KAGGLE_RUN_ORDER.md      exact notebook cell order for the official checks and the one-task smoke test
notebook/gemma_s0_preflight.ipynb the "ours" cells of that run order (rehearsed on synthetic fixtures only)
scripts/validate_s0_v2.py         static validator with mutation self-test (emulates documented rules; not the official compiler)
scripts/official_harness_check.py discovery-first official checks; reports BLOCKED when the official packages are absent
scripts/preflight_tools.py        read-only helpers used by the notebook (python3 preflight_tools.py selftest)
scripts/build_s0_zip.py           deterministic builder that produced the candidate (refuses to overwrite)
logs/                             logs and results from the run that produced the report

Quick check:  sha256sum -c candidate/SHA256SUMS.txt   (run inside candidate/)
Self-tests:   python3 scripts/preflight_tools.py selftest ; python3 scripts/validate_s0_v2.py candidate/submission.zip --selftest
