from __future__ import annotations
import csv
import hashlib
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RepositoryToolTests(unittest.TestCase):
    def test_submission_source_passes_static_validator(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_submission.py"), str(ROOT / "submission")],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATIC RESULT", result.stdout)

    def test_build_is_reproducible_and_root_layout_is_correct(self):
        out = ROOT / "dist" / "submission.zip"
        first = subprocess.run([sys.executable, str(ROOT / "tools" / "build_submission.py")], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        h1 = hashlib.sha256(out.read_bytes()).hexdigest()
        second = subprocess.run([sys.executable, str(ROOT / "tools" / "build_submission.py")], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        h2 = hashlib.sha256(out.read_bytes()).hexdigest()
        self.assertEqual(h1, h2)
        with zipfile.ZipFile(out) as z:
            self.assertIsNone(z.testzip())
            names = set(z.namelist())
        self.assertEqual(names, {"agent.yaml", "eval_config.yaml", "configs/sampling.yaml", "prompts/system.md"})
        with (ROOT / "submissions" / "manifest.csv").open(newline="", encoding="utf-8") as f:
            manifest_rows = list(csv.DictReader(f))
        current = [r for r in manifest_rows if r["current_candidate"].lower() == "yes"]
        self.assertEqual(len(current), 1)
        self.assertEqual(h2, current[0]["sha256"], "deterministic build should reproduce the canonical candidate archive")

    def test_submission_manifest_hashes_match_archives(self):
        manifest = ROOT / "submissions" / "manifest.csv"
        with manifest.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 15)
        self.assertEqual(len({r["sha256"] for r in rows}), len(rows), "manifest has duplicate SHA rows")
        for row in rows:
            p = ROOT / row["archive_path"]
            self.assertTrue(p.is_file(), row["archive_path"])
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(digest, row["sha256"], row["archive_path"])
            with zipfile.ZipFile(p) as z:
                self.assertIsNone(z.testzip(), row["archive_path"])

    def test_research_reports_and_progress_docs_exist(self):
        expected = [
            "docs/RESEARCH_PROGRESS.md",
            "docs/UPDATE_EXISTING_REPOSITORY.md",
            "research/reports/submission-event-2026-10-22-notebook-threw-exception.md",
            "docs/RESEARCH_FINDINGS.md",
            "docs/NEXT_STEPS.md",
            "research/reports/public-agent-research-2026-10-10.md",
            "research/reports/submission-forensics-2026-10-10.md",
            "research/reports/s0-preflight-2026-10-15.md",
            "research/ablation/development-set-and-ablation-plan.md",
            "research/prompts/prompt-07-forensics-followup.txt",
            "notebooks/preflight-s0/gemma_s0_preflight.ipynb",
            "research/evidence/screenshots/2026-10-22-notebook-threw-exception.png",
        ]
        for rel in expected:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_latest_exception_observation_has_no_fabricated_score_or_hash(self):
        path = ROOT / "evaluation" / "results" / "score_observations.csv"
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        latest = [r for r in rows if r["observation_id"] == "OBS-008"]
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["status"], "Notebook Threw Exception")
        self.assertEqual(latest[0]["public_score"], "")
        self.assertEqual(latest[0]["candidate_sha256"], "")
        self.assertEqual(latest[0]["attribution"], "UNATTRIBUTED")

if __name__ == "__main__":
    unittest.main()
