from __future__ import annotations
import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SubmissionToolTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)

    def test_static_validation_passes_and_disclaims_official_run(self):
        result = self.run_tool('tools/validate_submission.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('STATIC VALIDATION: PASS', result.stdout)
        self.assertIn('Not tested: official Kaggle compiler', result.stdout)

    def test_build_has_root_agent_and_only_submission_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'submission.zip'
            result = self.run_tool('tools/build_submission.py', '--output', str(out))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(out) as zf:
                self.assertIn('agent.yaml', zf.namelist())
                self.assertIn('configs/sampling.yaml', zf.namelist())
                self.assertIn('prompts/system.md', zf.namelist())
                self.assertNotIn('README.md', zf.namelist())
                self.assertIsNone(zf.testzip())

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.zip', Path(tmp)/'b.zip'
            ra = self.run_tool('tools/build_submission.py', '--output', str(a))
            rb = self.run_tool('tools/build_submission.py', '--output', str(b))
            self.assertEqual(ra.returncode, 0, ra.stdout + ra.stderr)
            self.assertEqual(rb.returncode, 0, rb.stdout + rb.stderr)
            self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(), hashlib.sha256(b.read_bytes()).hexdigest())

    def test_repository_manifest_and_secret_scan(self):
        result = self.run_tool('tools/check_repo.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('REPOSITORY CHECK: PASS', result.stdout)

if __name__ == '__main__':
    unittest.main()
