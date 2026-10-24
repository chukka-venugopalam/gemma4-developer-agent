import hashlib
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_submission import validate


class SubmissionTests(unittest.TestCase):
    def test_static_validator(self):
        notes = validate()
        self.assertTrue(any(note.startswith("Model:") for note in notes))

    def test_package_root_and_files(self):
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_submission.py")], check=True, cwd=ROOT, capture_output=True, text=True)
        archive = ROOT / "dist" / "submission.zip"
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            names = set(z.namelist())
            self.assertIn("agent.yaml", names)
            self.assertIn("prompts/system.md", names)
            self.assertNotIn("submission/agent.yaml", names)

    def test_build_is_reproducible(self):
        script = ROOT / "tools" / "build_submission.py"
        subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT, capture_output=True, text=True)
        one = hashlib.sha256((ROOT / "dist" / "submission.zip").read_bytes()).hexdigest()
        subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT, capture_output=True, text=True)
        two = hashlib.sha256((ROOT / "dist" / "submission.zip").read_bytes()).hexdigest()
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
