"""Cross-process spend reservations. Unknown billing stops subsequent calls."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from urllib.parse import urlparse

from .util import now


class BudgetError(RuntimeError):
    pass


def money(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise BudgetError("Budget/prices must be finite nonnegative values")
    return result


def nano_usd(value):
    return int((money(value) * 1_000_000_000).to_integral_value(rounding=ROUND_CEILING))


class Pricing:
    def __init__(self, path: Path, model: str):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("model") != model or data.get("verified") is not True:
            raise BudgetError("Pricing must be explicitly verified for the exact INFERENCE_MODEL")
        if urlparse(data.get("source_url", "")).hostname not in {"developers.openai.com", "platform.openai.com", "openai.com"}:
            raise BudgetError("Pricing needs an official source URL")
        checked = datetime.fromisoformat(data["verified_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        if age < 0 or age > 7 * 86400:
            raise BudgetError("Pricing verification must be within the last seven days")
        if data.get("reservation_strategy") != "full_context" or data.get("standard_text_only") is not True:
            raise BudgetError("Verified full-context reservation and standard text billing are required")
        self.context_window = data["context_window_tokens"]
        self.long_threshold = data["long_context_threshold_tokens"]
        if type(self.context_window) is not int or type(self.long_threshold) is not int or not 0 < self.long_threshold < self.context_window:
            raise BudgetError("Invalid verified context bounds")
        self.long_input = money(data["long_context_input_multiplier"])
        self.long_output = money(data["long_context_output_multiplier"])
        if min(self.long_input, self.long_output) < 1:
            raise BudgetError("Invalid long-context multipliers")
        self.input = money(data["input_usd_per_million"])
        self.cached = money(data["cached_input_usd_per_million"])
        self.output = money(data["output_usd_per_million"])
        self.write30 = money(data["cache_write_30m_usd_per_million"])
        self.write12 = money(data["cache_write_12h_usd_per_million"])
        if self.input <= 0 or self.output <= 0 or self.cached > self.input:
            raise BudgetError("Invalid pricing rates")
        self.metadata = data

    def reserve_cost(self, input_tokens, output_tokens):
        # Reserve the highest cache-write tier for every input token; actual
        # writes/reads are settled only when their usage is fully reported.
        rate = max(self.input, self.write30, self.write12)
        long = input_tokens > self.long_threshold
        return (input_tokens * rate * (self.long_input if long else 1) + output_tokens * self.output * (self.long_output if long else 1)) / 1_000_000

    def actual_cost(self, usage, write_ttl=None):
        incoming, outgoing = usage["input_tokens"], usage["output_tokens"]
        cached = usage.get("input_tokens_details", {}).get("cached_tokens")
        if cached is None:
            return None
        if not isinstance(cached, int) or not 0 <= cached <= incoming:
            raise BudgetError("Invalid cache usage")
        details = usage.get("input_tokens_details", {})
        writes = details.get("cache_write_tokens")
        if writes is None:
            return None
        if not isinstance(writes, int) or writes < 0 or writes + cached > incoming:
            raise BudgetError("Invalid cache write usage")
        # No retention preference is requested. If writes occur, require an
        # explicit billed retention breakdown rather than guess their cost.
        if writes:
            write_details = details.get("cache_write_tokens_details", {})
            w30, w12 = write_details.get("ttl_30m_tokens"), write_details.get("ttl_12h_tokens")
            # The adapter sends only plain text, with no per-part overrides.
            # An aggregate write count therefore uses the documented request TTL.
            if not write_details and write_ttl == "30m":
                w30, w12 = writes, 0
            if type(w30) is not int or type(w12) is not int or w30 < 0 or w12 < 0 or w30 + w12 != writes:
                return None
        else:
            w30 = w12 = 0
        long = incoming > self.long_threshold
        input_cost = (incoming - cached - writes) * self.input + cached * self.cached + w30 * self.write30 + w12 * self.write12
        return (input_cost * (self.long_input if long else 1) + outgoing * self.output * (self.long_output if long else 1)) / 1_000_000


class BudgetLedger:
    def __init__(self, path: Path, limit_usd: str):
        self.path = path
        self.limit = nano_usd(limit_usd)
        if self.limit <= 0:
            raise BudgetError("A positive explicit API spending limit is required")
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, time TEXT, purpose TEXT, question TEXT, reserved INTEGER, actual INTEGER, state TEXT)")

    @contextmanager
    def connect(self):
        # sqlite's own context manager commits/rolls back but does NOT close the
        # connection. Explicit close is essential for Windows file handles.
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def reserve(self, amount, purpose, question):
        cost = nano_usd(amount)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM calls WHERE state IN ('uncertain','pending')").fetchone()[0]:
                raise BudgetError("Unsettled API reservation: reconcile billing before further paid calls")
            total = db.execute("SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM calls").fetchone()[0]
            if total + cost > self.limit:
                raise BudgetError("Spending limit cannot cover the worst-case next call")
            call_id = str(uuid.uuid4())
            db.execute("INSERT INTO calls VALUES (?,?,?,?,?,NULL,'pending')", (call_id, now(), purpose, question, cost))
        return call_id

    def settle(self, call_id, actual):
        with self.connect() as db:
            reserved = db.execute("SELECT reserved FROM calls WHERE id=?", (call_id,)).fetchone()[0]
            billed = nano_usd(actual) if actual is not None else None
            if billed is None or billed > reserved:
                db.execute("UPDATE calls SET state='uncertain', actual=? WHERE id=?", (billed, call_id))
            else:
                db.execute("UPDATE calls SET state='settled', actual=? WHERE id=?", (billed, call_id))
        if billed is not None and billed > reserved:
            raise BudgetError("Usage exceeded the reserved upper bound; further inference stopped")

    def uncertain(self, call_id):
        with self.connect() as db:
            db.execute("UPDATE calls SET state='uncertain' WHERE id=?", (call_id,))

    def account_uncertain_upper_bound(self, call_id):
        """Explicit reconciliation: permanently consume the full reservation.

        Actual usage remains NULL. This never refunds funds or invents usage;
        subsequent reservations still include this entire amount in the cap.
        Pending requests cannot be reconciled while they may still be running.
        """
        with self.connect() as db:
            row = db.execute("SELECT state, actual FROM calls WHERE id=?", (call_id,)).fetchone()
            if row != ("uncertain", None):
                raise BudgetError("Only uncertain calls without actual usage can consume their reserved upper bound")
            db.execute("UPDATE calls SET state='bounded' WHERE id=?", (call_id,))

    def summary(self):
        with self.connect() as db:
            rows = db.execute("SELECT purpose, COUNT(*), SUM(COALESCE(actual,reserved)), SUM(CASE WHEN state!='settled' THEN 1 ELSE 0 END) FROM calls GROUP BY purpose").fetchall()
        return {purpose: {"calls": count, "charged_or_reserved_usd": total / 1e9, "unsettled_calls": uncertain}
                for purpose, count, total, uncertain in rows}
