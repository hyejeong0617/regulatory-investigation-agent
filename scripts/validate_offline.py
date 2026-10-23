"""Reproducible offline validation. Does not execute the supplied benchmark."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "validation"
REPORT.mkdir(exist_ok=True)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def main():
    began = time.perf_counter()
    report = {"started_at": timestamp(), "python": sys.version, "executable": sys.executable,
              "paid_calls": 0, "api_cost_usd": 0, "full_benchmark_executed": False, "checks": []}
    env = dict(os.environ, RUN_PAID_TESTS="false", PYTHONIOENCODING="utf-8")
    env.pop("OPENAI_API_KEY", None)
    commands = [
        ("unit_tests", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("doctor", ["-m", "regulatory_agent", "doctor"]),
        ("index", ["-m", "regulatory_agent", "--output-dir", "validation/corpus", "index"]),
        ("offline_smoke", ["-m", "regulatory_agent", "--output-dir", "validation/smoke", "ask",
                           "For dried figs from Türkiye, investigate aflatoxin limits, import documentation and operator withdrawal duties.", "--id", "offline-multi-provision-smoke"]),
    ]
    for name, args in commands:
        start = time.perf_counter()
        result = subprocess.run([sys.executable] + args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
        (REPORT / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        report["checks"].append({"name": name, "command": [sys.executable] + args,
                                  "exit_code": result.returncode, "wall_seconds": round(time.perf_counter()-start, 4),
                                  "log": str((REPORT / (name + ".log")).relative_to(ROOT))})
        print(name + ": " + ("PASS" if result.returncode == 0 else "FAIL"), flush=True)
        if result.returncode:
            break
    originals = [ROOT / "TASK_BRIEF.md"] + sorted((ROOT / "data").iterdir())
    report["starter_files"] = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in originals if p.is_file()]
    report["finished_at"] = timestamp()
    report["wall_seconds"] = round(time.perf_counter()-began, 4)
    report["passed"] = len(report["checks"]) == len(commands) and all(c["exit_code"] == 0 for c in report["checks"])
    (REPORT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
