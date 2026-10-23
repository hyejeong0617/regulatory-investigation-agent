"""Explicit settings; merely importing configuration cannot enable inference."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    source_dir: Path = Path("data")
    benchmark_file: Path = Path("data/benchmark_questions_v1.json")
    output_dir: Path = Path("outputs")
    state_dir: Path = Path(".state")
    model: str = "gpt-6-luna"
    reasoning_effort: str = "medium"
    run_paid_tests: bool = False
    max_llm_calls: int = 12
    max_tool_calls: int = 32
    max_rounds: int = 4
    max_output_tokens: int = 6000
    max_evidence_chars: int = 110000
    max_seconds: int = 240
    timeout: int = 60
    budget_usd: str = "2"
    pricing_file: Path | None = None

    @classmethod
    def from_env(cls) -> "Config":
        c = cls(
            source_dir=Path(os.getenv("SOURCE_DIR", "data")),
            benchmark_file=Path(os.getenv("BENCHMARK_FILE", "data/benchmark_questions_v1.json")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")),
            state_dir=Path(os.getenv("STATE_DIR", ".state")),
            model=os.getenv("INFERENCE_MODEL", "gpt-6-luna"),
            reasoning_effort=os.getenv("REASONING_EFFORT", "medium"),
            run_paid_tests=os.getenv("RUN_PAID_TESTS", "false").lower() == "true",
            max_llm_calls=int(os.getenv("MAX_LLM_CALLS_PER_QUESTION", "12")),
            max_tool_calls=int(os.getenv("MAX_TOOL_CALLS_PER_QUESTION", "32")),
            max_rounds=int(os.getenv("MAX_INVESTIGATION_ROUNDS", "4")),
            max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "6000")),
            max_seconds=int(os.getenv("MAX_SECONDS_PER_QUESTION", "240")),
            timeout=int(os.getenv("API_TIMEOUT_SECONDS", "60")),
            budget_usd=os.getenv("MAX_DEVELOPMENT_TEST_API_SPEND_USD", "2"),
            pricing_file=Path(os.environ["PRICING_FILE"]) if os.getenv("PRICING_FILE") else None,
        )
        c.validate()
        return c

    def validate(self) -> None:
        if not 1 <= self.max_llm_calls <= 12:
            raise ValueError("MAX_LLM_CALLS_PER_QUESTION must be 1..12")
        if not 1 <= self.max_tool_calls <= 100 or not 1 <= self.max_rounds <= 10:
            raise ValueError("Tool or investigation limits out of range")
        if not 256 <= self.max_output_tokens <= 32000:
            raise ValueError("MAX_OUTPUT_TOKENS must be 256..32000")
        if not 1 <= self.timeout <= 120 or not 1 <= self.max_seconds <= 1800:
            raise ValueError("Timeout limits out of range")
        if self.reasoning_effort not in {"medium", "omit"}:
            raise ValueError("Comparison uses medium; use omit only for a model without reasoning support")
