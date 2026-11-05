#!/usr/bin/env python3
"""Score `submission/` with the official harness.

    python scripts/score.py              # 40 public questions
    python scripts/score.py --selftest   # tiny fixture shipped with the harness
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--submission", type=Path, default=KIT / "submission")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cmd = [sys.executable, str(KIT / "harness" / "run_eval.py"), "--submission", str(args.submission)]
    if args.selftest:
        cmd += [
            "--snapshots", str(KIT / "harness" / "selftest" / "snapshots"),
            "--eval", str(KIT / "harness" / "selftest" / "eval.jsonl"),
            "--conflicts-gold", str(KIT / "harness" / "selftest" / "conflicts_gold.json"),
            "--out", str(args.out or KIT / "results" / "selftest"),
            "--repeat-sample", "0",
        ]
    else:
        cmd += [
            "--snapshots", str(KIT / "snapshots"),
            "--eval", str(KIT / "eval" / "public_eval.jsonl"),
            "--out", str(args.out or KIT / "results" / "public"),
        ]
    raise SystemExit(subprocess.call(cmd, cwd=KIT))


if __name__ == "__main__":
    main()
