"""Explicit paid Q5-only smoke. Run only with development authorization."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from regulatory_agent.cli import main
from regulatory_agent.util import write_json

if __name__ == "__main__":
    os.chdir(ROOT)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise SystemExit("OPENAI_API_KEY is MISSING")
    os.environ.update(INFERENCE_MODEL="gpt-6-luna", REASONING_EFFORT="medium",
                      MAX_DEVELOPMENT_TEST_API_SPEND_USD="2", STATE_DIR=".state",
                      PRICING_FILE="config/pricing.verified.json", RUN_PAID_TESTS="true",
                      MAX_SECONDS_PER_QUESTION="600", API_TIMEOUT_SECONDS="120")
    questions = json.loads((ROOT / "data/benchmark_questions_v1.json").read_text(encoding="utf-8"))["questions"]
    context = ROOT / "validation/q5_context.json"
    write_json(context, {"preceding_question": questions["Q4"], "preceding_answer": None})
    raise SystemExit(main(["--output-dir", "outputs/live-smoke", "ask", questions["Q5"],
                          "--id", "Q5", "--context", str(context), "--paid"]))
