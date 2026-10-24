# Prompt 7 forensic source bundle

- `GEMMA_FORENSICS_FOLLOWUP_ORIGINAL.zip` is the uploaded archive preserved byte-for-byte.
- `source_bundle/` is its extracted working copy. Text files in this directory have normalized LF line endings and stripped trailing spaces for clean Git diffs; substantive content was not intentionally edited.
- `source_bundle/SOURCE_ARCHIVE_SHA256SUMS.txt` is the checksum list as delivered inside the original archive.
- `source_bundle/SHA256SUMS.txt` is regenerated for the normalized working copy.
- The full original ZIP is the source of truth if any byte-level discrepancy matters.
