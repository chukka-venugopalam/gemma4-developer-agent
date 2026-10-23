# Submission artifacts

`submission/` at the repository root is the only editable source of the current candidate. `tools/build_submission.py` produces `dist/submission.zip` from that source.

- `archive/` stores immutable historical candidates and the current dated candidate.
- `source_snapshots/` retains a readable snapshot of the October 22 source bundle.
- `manifest.csv` records file names, SHA-256 hashes, byte sizes, dates/status labels, and provenance notes.

A score should only be associated with an archive when the evidence identifies that exact uploaded artifact. The current screenshot records do not expose archive hashes, so historical scores are intentionally left unattributed. Do not overwrite old ZIPs; add a dated file instead.
