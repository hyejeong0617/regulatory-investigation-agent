"""Offline regression suite. No tests access the network or run the benchmark."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from regulatory_agent.agent import Investigator, validate_claims
from regulatory_agent.budget import BudgetError, BudgetLedger, Pricing
from regulatory_agent.cli import load_questions, main, safe_filename, save_result
from regulatory_agent.config import Config
from regulatory_agent.corpus import Corpus, DOM, table_grid
from regulatory_agent.llm import InferenceError, OpenAIProvider
from regulatory_agent.retrieval import SearchIndex
from regulatory_agent.util import digest, now, write_json

ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP = ROOT / ".test_tmp"
TEST_TEMP.mkdir(exist_ok=True)


def temporary_directory():
    # Keep every test artifact inside the connected project's write boundary.
    return tempfile.TemporaryDirectory(dir=TEST_TEMP)


def action(tool, query="", regulation="", location="", evidence_id=""):
    return dict(tool=tool, query=query, regulation=regulation, location=location, evidence_id=evidence_id)


def price_file(directory):
    path = directory / "pricing.json"
    write_json(path, {"model": "gpt-6-luna", "verified": True, "verified_at": now(),
                     "source_url": "https://developers.openai.com/api/docs/pricing",
                     "input_usd_per_million": "0.10", "cached_input_usd_per_million": "0.01",
                     "output_usd_per_million": "0.50", "cache_write_30m_usd_per_million": "0.125",
                     "cache_write_12h_usd_per_million": "0.25", "context_window_tokens": 1050000,
                     "long_context_threshold_tokens": 272000, "long_context_input_multiplier": "2",
                     "long_context_output_multiplier": "1.5",
                     "reservation_strategy": "full_context", "standard_text_only": True})
    return path


class ScriptedProvider:
    """Contract double, not a language model or legal-quality evaluation."""
    mode = "test_double"

    def __init__(self, behavior="valid"):
        self.behavior = behavior
        self.stages = []
        self.events = []
        self.turn = 0

    def start_question(self, question_id):
        self.turn = 0
        self.events = []
        self.stages = []

    def complete(self, stage, instructions, payload, schema, remaining_seconds):
        self.stages.append(stage)
        # Mock usage is intentionally absent: never pretend this is API usage.
        if stage == "investigate":
            self.turn += 1
            return {"issues": ["storage", "reporting"], "missing_evidence": [], "ready": self.turn > 1,
                    "actions": [] if self.turn > 1 else [action("search", "port declaration temperature") ]}
        if stage == "assess":
            if self.behavior == "missing":
                return {"claims": [], "unknown_facts": ["Shipment temperature unknown"],
                        "verification_needed": ["Requested external rules are absent from the corpus"],
                        "unanswered_issues": ["No source for the requested external rule"]}
            chosen = [r for r in payload["evidence"] if r["regulation"] == "2099/1" and "Article" in r["location"]]
            claims = [{"id": f"C{i+1}", "issue": "storage" if i == 0 else "reporting",
                       "category": "direct_answer", "statement": r["text"].split("\n")[-1],
                       "conditions": [], "supports": [{"evidence_id": r["id"], "quote": r["text"]}]}
                      for i, r in enumerate(chosen[:2])]
            if self.behavior == "fabricated" and claims:
                claims[0]["supports"][0]["evidence_id"] = "NONEXISTENT"
            return {"claims": claims, "unknown_facts": ["Shipment temperature unknown"],
                    "verification_needed": [], "unanswered_issues": []}
        if self.behavior == "review_failure":
            raise InferenceError("Simulated incomplete reviewer")
        return {"verdicts": [{"claim_id": c["id"], "supported": self.behavior != "reject",
                               "problem": "Unsupported requirement" if self.behavior == "reject" else ""}
                              for c in payload["assessment"]["claims"]],
                "coverage_gaps": ["External rule absent"] if self.behavior == "missing" else [], "follow_up_actions": []}


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = Corpus(ROOT / "data")
        cls.index = SearchIndex(cls.corpus)

    def test_all_five_sources_and_provenance(self):
        self.assertEqual(len(self.corpus.manifest), 5)
        self.assertEqual({m["regulation"] for m in self.corpus.manifest}, {"178/2002", "2017/625", "2019/1793", "2019/1013", "2023/915"})
        hashes = {m["file"]: digest((ROOT / "data" / m["file"]).read_bytes()) for m in self.corpus.manifest}
        for record in self.corpus.records:
            self.assertTrue(record.text)
            self.assertGreater(record.line_start, 0)
            self.assertGreaterEqual(record.line_end, record.line_start)
            self.assertEqual(record.source_sha256, hashes[record.document])
        for manifest in self.corpus.manifest:
            self.assertGreater(manifest["records"], 0)

    def test_div_paragraphs_are_retained(self):
        records = self.corpus.lookup("178/2002", "Article 19")
        text = " ".join(r.text for r in records)
        self.assertIn("1.", text)
        self.assertIn("4.", text)
        self.assertIn("immediately initiate procedures to withdraw", text)
        self.assertIn("if necessary, recall", text)

    def test_numeric_limits_keep_headers_and_exceptions(self):
        hits = self.index.search("dried figs aflatoxin maximum level", 1)
        record = hits[0][0]
        self.assertEqual(record.regulation, "2023/915")
        self.assertIn("entry 1.1.3", record.location)
        self.assertIn("6,0", record.text)
        self.assertIn("10,0", record.text)
        self.assertIn("μg/kg", record.text)
        self.assertIn("Sum of B1", record.text)
        self.assertIn("80 %", record.text)
        neighbors = self.corpus.neighbors(record.id, 2)
        self.assertTrue(any("except products listed in 1.1.3" in r.text for r in neighbors))

    def test_import_row_has_explicit_block_context(self):
        record = next(r for r in self.corpus.records if r.regulation == "2019/1793" and r.kind == "table_row" and "C3: — Dried figs |" in r.text)
        self.assertIn("ANNEX II", record.location)
        self.assertEqual(record.table["cells"][1]["text"], "Türkiye (TR)")
        self.assertEqual(record.table["cells"][5]["text"], "")
        self.assertFalse(record.table["blank_cells_inferred"])
        self.assertIn("Aflatoxins and", record.text)
        self.assertIn("Ochratoxin A", record.text)
        self.assertIn("C7: 30", record.text)
        self.assertNotIn("Pistachios", " ".join(record.table["context"]))
        # One referenced note must not accidentally absorb all notes below it.
        self.assertNotIn("Cereulide", record.text)

    def test_original_act_discovered_by_topic(self):
        record = self.index.search("prior notification consignment", 1)[0][0]
        self.assertEqual(record.regulation, "2019/1013")
        self.assertIn("Article 1", record.location)
        self.assertIn("one working day", record.text)

    def test_unrelated_topic_and_missing_source(self):
        hits = self.index.search("confidentiality professional secrecy", 5)
        self.assertTrue(any("confidential" in r.text.lower() for r, _ in hits))
        self.assertEqual(self.corpus.lookup("9999/9999", "Article 9"), [])
        self.assertEqual(self.index.search("zzquuxnonexistent"), [])

    def test_exact_article_boundaries(self):
        self.assertTrue(self.corpus.lookup("2017/625", "Article 1"))
        self.assertFalse(any(r.location.startswith("Article 10") for r in self.corpus.lookup("2017/625", "Article 1")))

    def test_anchors_exist(self):
        content = {m["file"]: (ROOT / "data" / m["file"]).read_text(encoding="utf-8") for m in self.corpus.manifest}
        for record in self.corpus.records:
            if record.anchor:
                self.assertIn('id="' + record.anchor + '"', content[record.document])

    def test_offline_actual_question_no_network(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Network forbidden")):
            result = Investigator(self.corpus, Config()).run("For dried figs from Türkiye, investigate aflatoxin limits and operator withdrawal duties.", "smoke-offline")
        self.assertEqual(result["status"], "evidence_only")
        self.assertEqual(result["metrics"]["llm_calls"], 0)
        self.assertEqual(result["metrics"]["api_cost_usd"], 0)
        self.assertGreater(result["metrics"]["retrieved_records"], 0)
        self.assertEqual(result["assessment"]["claims"], [])
        self.assertIn("No legal conclusions", result["final_answer"])


class TableTests(unittest.TestCase):
    def test_rowspan_colspan_and_inline_subscript(self):
        html = '<table><tr><th rowspan="2">Country</th><th colspan="2">B<span>1</span></th></tr><tr><td>A</td><td>B</td></tr></table>'
        table = next(n for n in DOM(html).root.walk() if n.tag == "table")
        rows = table_grid(table)
        self.assertEqual([c["text"] for c in rows[0]["cells"]], ["Country", "B1", "B1"])
        self.assertEqual([c["text"] for c in rows[1]["cells"]], ["Country", "A", "B"])
        self.assertEqual(rows[1]["cells"][0]["origin_row"], 1)

    def test_no_sources(self):
        with temporary_directory() as tmp:
            with self.assertRaisesRegex(ValueError, "No HTML"):
                Corpus(Path(tmp))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary_directory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "EU_2099_1.html").write_text('''<html><body>
<p>REGULATION (EU) 2099/1</p>
<p id="art1">Article 1</p><div class="norm">1. Operators shall record the storage temperature before accepting a consignment.</div>
<p id="art2">Article 2</p><div class="norm">2. Operators shall submit a port declaration to the local authority.</div>
</body></html>''', encoding="utf-8")
        self.corpus = Corpus(self.root)

    def run_agent(self, behavior="valid", qid="arbitrary"):
        provider = ScriptedProvider(behavior)
        result = Investigator(self.corpus, Config(), provider).run("What storage and reporting rules apply?", qid, context={"product": "sample"})
        return result, provider

    def test_dynamic_followup_and_multi_provision_review(self):
        result, provider = self.run_agent()
        self.assertEqual(result["status"], "assessed")
        self.assertEqual(len(result["assessment"]["claims"]), 2)
        self.assertIn("review", provider.stages)
        self.assertTrue(any(e.get("phase") == "follow_up" for e in result["events"]))
        self.assertLessEqual(result["metrics"]["workflow_model_calls"], 12)

    def test_question_id_does_not_route(self):
        a, _ = self.run_agent(qid="totally-different-a")
        b, _ = self.run_agent(qid="totally-different-b")
        self.assertEqual(a["assessment"], b["assessment"])
        self.assertEqual(a["evidence"], b["evidence"])

    def test_fabricated_citation_rejected(self):
        result, _ = self.run_agent("fabricated")
        self.assertTrue(result["rejected_claims"])
        self.assertNotIn("NONEXISTENT", result["final_answer"])

    def test_semantic_reviewer_rejection(self):
        result, _ = self.run_agent("reject")
        self.assertEqual(result["assessment"]["claims"], [])
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_missing_evidence_explicit_uncertainty(self):
        result, _ = self.run_agent("missing")
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("External rule absent", result["final_answer"])

    def test_interrupted_review_never_publishes_draft(self):
        result, _ = self.run_agent("review_failure")
        self.assertEqual(result["assessment"]["claims"], [])
        self.assertTrue(result["errors"])

    def test_too_small_call_allowance_fails_closed(self):
        result = Investigator(self.corpus, replace(Config(), max_llm_calls=1), ScriptedProvider()).run("storage temperature")
        self.assertEqual(result["assessment"]["claims"], [])
        self.assertTrue(result["errors"])

    def test_quote_must_match(self):
        record = self.corpus.records[0]
        claim = {"id": "C1", "statement": "made up", "supports": [{"evidence_id": record.id, "quote": "A fictional legal provision never present in the source."}]}
        accepted, rejected = validate_claims([claim], self.corpus.by_id)
        self.assertFalse(accepted)
        self.assertEqual(len(rejected), 1)

    def test_output_roundtrip_and_jsonl(self):
        result, _ = self.run_agent()
        path = save_result(self.root / "out", result)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved, result)
        events = path.with_suffix(".events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertTrue(events)
        for event in events:
            self.assertIn("event", json.loads(event))

    def test_session_and_batch_gate(self):
        with patch.dict(os.environ, {"RUN_PAID_TESTS": "false"}), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            base = ["--source-dir", str(self.root), "--output-dir", str(self.root / "out")]
            session = self.root / "session.json"
            self.assertEqual(main(base + ["ask", "storage", "--session", str(session)]), 0)
            self.assertEqual(main(base + ["ask", "and reporting?", "--session", str(session)]), 0)
            self.assertEqual(len(json.loads(session.read_text())["history"]), 2)
            self.assertEqual(main(base + ["batch"]), 2)

    def test_two_question_synthetic_batch(self):
        path = self.root / "synthetic.json"
        write_json(path, {"questions": {"first": "storage", "second": "and reporting?"}})
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = main(["--source-dir", str(self.root), "--output-dir", str(self.root / "batch"),
                         "batch", "--file", str(path), "--authorize-batch"])
        self.assertEqual(code, 0)
        outputs = list((self.root / "batch").glob("*/question-second-*.json"))
        second = json.loads(outputs[0].read_text(encoding="utf-8"))
        self.assertEqual(second["history"][0]["question_id"], "first")

    def test_safe_output_names(self):
        for value in ("../../outside", "CON", "NUL", "a/b", "a\\b"):
            name = safe_filename(value)
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertTrue(name.startswith("question-"))


class BudgetAndAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary_directory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = replace(Config(), run_paid_tests=True, state_dir=self.root, pricing_file=price_file(self.root))

    def provider(self, transport):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "TEST-ONLY-NOT-A-REAL-KEY"}):
            provider = OpenAIProvider(self.config, transport=transport)
        provider.start_question("unit-test")
        return provider

    def response(self, usage=True):
        return {"id": "fake-response", "model": "gpt-6-luna", "status": "completed", "service_tier": "default",
                "usage": {"input_tokens": 100, "output_tokens": 20, "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 5}} if usage else None,
                "output": [{"type": "reasoning", "content": "NEVER_SAVE_HIDDEN_TEXT"},
                           {"type": "message", "content": [{"type": "output_text", "text": '{"ok":true}'}]}]}

    def call(self, provider):
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
        return provider.complete("test", "Test instructions", {"question": "test"}, schema, 30)

    def test_budget_persists_and_stops_before_overspend(self):
        ledger = BudgetLedger(self.root / "budget.sqlite3", "2")
        call = ledger.reserve(Decimal("1.50"), "development", "a")
        ledger.settle(call, Decimal("1.20"))
        ledger = BudgetLedger(self.root / "budget.sqlite3", "2")
        with self.assertRaisesRegex(BudgetError, "Spending limit"):
            ledger.reserve(Decimal("0.81"), "development", "b")
        self.assertAlmostEqual(ledger.summary()["development"]["charged_or_reserved_usd"], 1.2)

    def test_pending_or_uncertain_reservations_block(self):
        ledger = BudgetLedger(self.root / "budget.sqlite3", "2")
        call = ledger.reserve("0.1", "development", "a")
        with self.assertRaisesRegex(BudgetError, "Unsettled"):
            BudgetLedger(self.root / "budget.sqlite3", "2").reserve("0.1", "development", "b")
        ledger.uncertain(call)
        with self.assertRaises(BudgetError):
            ledger.reserve("0.1", "development", "c")

    def test_disabled_and_missing_key_no_network(self):
        with self.assertRaises(BudgetError):
            OpenAIProvider(Config())
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(BudgetError, "OPENAI_API_KEY"):
            OpenAIProvider(self.config)

    def test_uncertain_upper_bound_is_never_refunded(self):
        ledger = BudgetLedger(self.root / "budget.sqlite3", "2")
        call = ledger.reserve("1.5", "development", "failed")
        with self.assertRaises(BudgetError):
            ledger.account_uncertain_upper_bound(call)
        ledger.uncertain(call)
        ledger.account_uncertain_upper_bound(call)
        with self.assertRaisesRegex(BudgetError, "Spending limit"):
            ledger.reserve("0.51", "development", "next")
        self.assertEqual(ledger.summary()["development"]["charged_or_reserved_usd"], 1.5)
        ledger.reserve("0.5", "development", "next")

    def test_unverified_pricing_fails_closed(self):
        with self.assertRaises(BudgetError):
            Pricing(ROOT / "config/pricing.example.json", "gpt-6-luna")

    def test_verified_usage_cost_and_no_reasoning_logs(self):
        requests = []
        def transport(endpoint, payload, timeout):
            requests.append((endpoint, payload))
            return {"input_tokens": 100} if endpoint.endswith("input_tokens") else self.response()
        provider = self.provider(transport)
        self.assertEqual(self.call(provider), {"ok": True})
        self.assertEqual(provider.attempts, 1)
        self.assertEqual([r[0] for r in requests], ["responses"])
        self.assertEqual(requests[0][1]["reasoning"], {"effort": "medium"})
        self.assertFalse(requests[0][1]["store"])
        self.assertEqual(provider.events[-1]["reserved_usd"], 0.5295)
        self.assertNotIn("NEVER_SAVE_HIDDEN_TEXT", json.dumps(provider.events))
        self.assertAlmostEqual(provider.events[-1]["api_cost_usd"], 0.00002)
        self.assertEqual(provider.events[-1]["reasoning_tokens"], 5)

    def test_missing_usage_stops_later_calls(self):
        provider = self.provider(lambda endpoint, payload, timeout: {"input_tokens": 100} if endpoint.endswith("input_tokens") else self.response(False))
        with self.assertRaises(BudgetError):
            self.call(provider)
        with self.assertRaisesRegex(BudgetError, "Unsettled"):
            self.call(provider)
        self.assertEqual(provider.attempts, 1)

    def test_full_context_reservation_blocks_before_network(self):
        provider = self.provider(lambda *args: self.fail("No request allowed"))
        call = provider.ledger.reserve("1.5", "development", "earlier")
        provider.ledger.settle(call, Decimal("1.5"))
        with self.assertRaisesRegex(BudgetError, "Spending limit"):
            self.call(provider)
        self.assertEqual(provider.attempts, 0)

    def test_long_context_pricing_boundary(self):
        pricing = Pricing(self.config.pricing_file, self.config.model)
        usage = {"input_tokens": 272000, "output_tokens": 1000,
                 "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0}}
        self.assertEqual(pricing.actual_cost(usage), Decimal("0.0277"))
        usage["input_tokens"] += 1
        self.assertEqual(pricing.actual_cost(usage), Decimal("0.0551502"))

    def test_unexpected_service_tier_blocks(self):
        response = self.response()
        response["service_tier"] = "priority"
        provider = self.provider(lambda *args: response)
        with self.assertRaisesRegex(BudgetError, "service tier"):
            self.call(provider)
        self.assertEqual(provider.ledger.summary()["development"]["unsettled_calls"], 1)

    def test_transport_error_not_retried(self):
        count = []
        def transport(endpoint, payload, timeout):
            count.append(endpoint)
            if endpoint.endswith("input_tokens"):
                return {"input_tokens": 100}
            raise InferenceError("simulated timeout")
        provider = self.provider(transport)
        with self.assertRaises(InferenceError):
            self.call(provider)
        self.assertEqual(count.count("responses"), 1)
        self.assertEqual(provider.ledger.summary()["development"]["unsettled_calls"], 1)

    def test_call_limit(self):
        provider = self.provider(lambda endpoint, payload, timeout: {"input_tokens": 100} if endpoint.endswith("input_tokens") else self.response())
        provider.config = replace(provider.config, max_llm_calls=1)
        self.call(provider)
        with self.assertRaisesRegex(BudgetError, "call limit"):
            self.call(provider)

    def test_aggregate_writes_use_documented_default_ttl(self):
        response = self.response()
        response["usage"]["input_tokens_details"]["cache_write_tokens"] = 50
        provider = self.provider(lambda endpoint, payload, timeout: {"input_tokens": 100} if endpoint.endswith("input_tokens") else response)
        self.assertEqual(self.call(provider), {"ok": True})
        self.assertAlmostEqual(provider.events[-1]["api_cost_usd"], 0.00002125)
        self.assertIsNone(provider.pricing.actual_cost(response["usage"]))

    def test_documented_cache_write_usage_is_accounted(self):
        response = self.response()
        response["usage"]["input_tokens_details"] = {
            "cached_tokens": 10, "cache_write_tokens": 50,
            "cache_write_tokens_details": {"ttl_30m_tokens": 30, "ttl_12h_tokens": 20},
        }
        provider = self.provider(lambda endpoint, payload, timeout: {"input_tokens": 100} if endpoint.endswith("input_tokens") else response)
        self.assertEqual(self.call(provider), {"ok": True})
        self.assertAlmostEqual(provider.events[-1]["api_cost_usd"], 0.00002285)
        self.assertEqual(provider.ledger.summary()["development"]["unsettled_calls"], 0)

    def test_inconsistent_cache_write_breakdown_stops(self):
        response = self.response()
        response["usage"]["input_tokens_details"] = {
            "cached_tokens": 10, "cache_write_tokens": 50,
            "cache_write_tokens_details": {"ttl_30m_tokens": 30, "ttl_12h_tokens": 21},
        }
        provider = self.provider(lambda endpoint, payload, timeout: {"input_tokens": 100} if endpoint.endswith("input_tokens") else response)
        with self.assertRaises(BudgetError):
            self.call(provider)
        self.assertEqual(provider.ledger.summary()["development"]["unsettled_calls"], 1)

    def test_nan_and_negative_money_disallowed(self):
        for value in ("NaN", "Infinity", "-1"):
            with self.assertRaises(BudgetError):
                BudgetLedger(self.root / "invalid.sqlite3", value)


if __name__ == "__main__":
    unittest.main()
