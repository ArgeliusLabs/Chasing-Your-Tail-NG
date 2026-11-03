import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReplayCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "cyt_core", *args], cwd=ROOT,
                              capture_output=True, text=True, timeout=10)

    def test_demo_is_machine_readable_and_ignore_removes_identifier(self):
        args = ["research/example-route.jsonl", "--at", "1200"]
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"][0]["wildcard_probes"], 3)
        ignored = self.run_cli(*args, "--ignore", "wifi,02:00:00:00:00:01")
        self.assertEqual(ignored.returncode, 0, ignored.stderr)
        self.assertEqual(json.loads(ignored.stdout)["observed_identifiers"], 0)

    def test_nonfinite_replay_time_fails_without_report(self):
        result = self.run_cli("research/example-route.jsonl", "--at", "NaN")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("finite number", result.stderr)

    def test_missing_input_fails_without_empty_success_report(self):
        result = self.run_cli("research/does-not-exist.jsonl", "--at", "1200")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
