"""Contract shape, plus the official scorer on the harness fixture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "submission"))

from solution import build  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_build_answers_and_lists_conflicts(self):
        ks = build()
        answer = ks.answer("What is the 6-month certificate APY?")
        self.assertEqual(answer.text, "I don't know.")
        self.assertFalse(answer.confident)
        self.assertEqual(answer.sources, [])
        self.assertEqual(ks.conflicts(), [])

    def test_selftest_eval_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(KIT / "harness" / "run_eval.py"),
                    "--submission", str(KIT / "submission"),
                    "--snapshots", str(KIT / "harness" / "selftest" / "snapshots"),
                    "--eval", str(KIT / "harness" / "selftest" / "eval.jsonl"),
                    "--conflicts-gold", str(KIT / "harness" / "selftest" / "conflicts_gold.json"),
                    "--out", tmp,
                    "--repeat-sample", "0",
                ],
                cwd=KIT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads((Path(tmp) / "report.json").read_text())
        self.assertEqual(report["questions"], 5)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["by_category"]["should_refuse"]["score"], 1.0)
        self.assertIn("conflicts", report)


if __name__ == "__main__":
    unittest.main()
