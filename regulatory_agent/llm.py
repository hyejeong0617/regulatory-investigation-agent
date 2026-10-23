"""OpenAI Responses adapter using only Python's standard library.

No automatic retry of a potentially billed request. The planner can repair a
completed but malformed response within the question's total call allowance.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .budget import BudgetError, BudgetLedger, Pricing
from .config import Config
from .schemas import validate


class InferenceError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise InferenceError("API redirects are disabled")


class OpenAIProvider:
    mode = "openai"

    def __init__(self, config: Config, purpose: str = "development", transport=None):
        if not config.run_paid_tests:
            raise BudgetError("Paid inference disabled: set RUN_PAID_TESTS=true only with authorization")
        if not config.model or "[" in config.model:
            raise BudgetError("Set the exact shared INFERENCE_MODEL; no model is chosen automatically")
        if not os.getenv("OPENAI_API_KEY"):
            raise BudgetError("OPENAI_API_KEY is not configured")
        if not config.pricing_file:
            raise BudgetError("PRICING_FILE with recently verified rates is required")
        self.config = config
        self.pricing = Pricing(config.pricing_file, config.model)
        self.ledger = BudgetLedger(config.state_dir / "budget.sqlite3", config.budget_usd)
        self.purpose = purpose
        self.transport = transport or self._http
        self.events = []
        self.attempts = 0
        self.question_id = ""

    def start_question(self, question_id):
        self.events = []
        self.attempts = 0
        self.question_id = question_id

    def _http(self, endpoint, payload, timeout):
        request = urllib.request.Request(
            "https://api.openai.com/v1/" + endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"},
            method="POST")
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Do not echo response bodies, requests, credentials or hidden reasoning.
            raise InferenceError(f"API HTTP {error.code}; request not retried") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise InferenceError(f"API transport failure ({type(error).__name__}); request not retried") from None

    def complete(self, stage, instructions, payload, schema, remaining_seconds):
        if self.attempts >= self.config.max_llm_calls:
            raise BudgetError("Question LLM call limit reached")
        began = time.monotonic()
        request = {"model": self.config.model, "instructions": instructions,
                   "input": json.dumps(payload, ensure_ascii=False),
                   "text": {"format": {"type": "json_schema", "name": stage, "strict": True, "schema": schema}}}
        if self.config.reasoning_effort != "omit":
            request["reasoning"] = {"effort": self.config.reasoning_effort}
        timeout = min(self.config.timeout, remaining_seconds)
        if timeout <= 0:
            raise InferenceError("Question deadline reached")
        # Reserve the full model context at its highest applicable rate. This
        # needs neither an unreserved token-count API call nor a tokenizer guess.
        reserved_input = self.pricing.context_window
        amount = self.pricing.reserve_cost(reserved_input, self.config.max_output_tokens)
        timeout = min(self.config.timeout, remaining_seconds - (time.monotonic() - began))
        if timeout <= 0:
            raise InferenceError("Question deadline reached before generation")
        call_id = self.ledger.reserve(amount, self.purpose, self.question_id)
        self.attempts += 1
        event = {"event": "llm_call", "stage": stage, "call_id": call_id, "model": self.config.model,
                 "reserved_usd": float(amount), "input_tokens": None, "output_tokens": None,
                 "reasoning_tokens": None, "api_cost_usd": None, "error": None}
        self.events.append(event)
        request.update({"max_output_tokens": self.config.max_output_tokens, "store": False, "service_tier": "default"})
        try:
            response = self.transport("responses", request, timeout)
        except Exception:
            self.ledger.uncertain(call_id)
            event["error"] = "Transport/API failure; billing uncertain; further paid calls stopped"
            raise
        finally:
            event["wall_seconds"] = round(time.monotonic() - began, 4)
        usage = response.get("usage") or {}
        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")):
            self.ledger.uncertain(call_id)
            event["error"] = "Usage missing; billing uncertain"
            raise BudgetError("Verified usage unavailable; further paid calls stopped")
        event.update({"response_id": response.get("id"), "input_tokens": usage["input_tokens"],
                      "output_tokens": usage["output_tokens"],
                      "reasoning_tokens": usage.get("output_tokens_details", {}).get("reasoning_tokens"),
                      "input_tokens_details": usage.get("input_tokens_details")})
        if response.get("model") not in [self.config.model, *self.pricing.metadata.get("accepted_response_models", [])]:
            self.ledger.uncertain(call_id)
            raise BudgetError("Response model differs from verified model/pricing")
        if response.get("service_tier") != "default":
            self.ledger.uncertain(call_id)
            raise BudgetError("Response service tier differs from verified standard pricing")
        # No prompt_cache_options or per-part breakpoints: documented 30m default.
        cost = self.pricing.actual_cost(usage, write_ttl="30m")
        self.ledger.settle(call_id, cost)
        event["api_cost_usd"] = float(cost) if cost is not None else None
        if cost is None:
            raise BudgetError("Cache usage unavailable; exact cost unknown; further calls stopped")
        if response.get("status") != "completed":
            raise InferenceError("Model response incomplete; increase output allowance only within budget")
        texts = [part["text"] for item in response.get("output", []) if item.get("type") == "message"
                 for part in item.get("content", []) if part.get("type") == "output_text"]
        # Reasoning objects and summaries are deliberately never persisted.
        try:
            value = json.loads("".join(texts))
            validate(value, schema)
            return value
        except (ValueError, TypeError) as error:
            raise InferenceError(f"Invalid structured response: {error}") from None
