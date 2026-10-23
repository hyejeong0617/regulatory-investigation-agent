"""CLI and sequential batch runner; batch evaluation requires an explicit gate."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import replace
from pathlib import Path

from .agent import DEFAULT_CONTEXT, Investigator
from .config import Config
from .corpus import Corpus
from .llm import OpenAIProvider
from .retrieval import SearchIndex
from .util import digest, now, write_json


def load_object(path: Path):
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return result


def load_questions(path: Path):
    questions = load_object(path).get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("Batch input must contain a nonempty 'questions' object")
    if any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in questions.items()):
        raise ValueError("Question IDs and questions must be strings")
    return list(questions.items())


def safe_filename(question_id):
    value = re.sub(r"[^A-Za-z0-9_-]", "_", question_id)[:60] or "question"
    # Prefix also avoids Windows device filenames and traversal.
    return "question-" + value + "-" + digest(question_id.encode())[:8]


def save_result(output_dir, result):
    stem = safe_filename(result["question_id"])
    write_json(output_dir / (stem + ".json"), result)
    (output_dir / (stem + ".md")).write_text(result["final_answer"] + "\n", encoding="utf-8")
    with (output_dir / (stem + ".events.jsonl")).open("w", encoding="utf-8") as stream:
        for event in result["events"]:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    return output_dir / (stem + ".json")


def parser():
    p = argparse.ArgumentParser(description="Investigate supplied EU-law snapshots. Default: offline evidence only.")
    p.add_argument("--source-dir", type=Path)
    p.add_argument("--output-dir", type=Path)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Show configuration and credential presence, never secrets")
    sub.add_parser("index", help="Parse local corpus and write manifest/evidence records")
    search = sub.add_parser("search", help="Local BM25 search")
    search.add_argument("query")
    search.add_argument("--regulation", default="")
    search.add_argument("--limit", type=int, default=6)
    ask = sub.add_parser("ask", help="One question, optionally sharing a conversation session")
    ask.add_argument("question")
    ask.add_argument("--id", default="single")
    ask.add_argument("--context", type=Path, help="JSON object merged with the default case; null keeps a fact unknown")
    ask.add_argument("--session", type=Path)
    ask.add_argument("--paid", action="store_true", help="Also requires RUN_PAID_TESTS=true and verified pricing")
    batch = sub.add_parser("batch", help="Sequential question file; no development benchmark authorization implied")
    batch.add_argument("--file", type=Path)
    batch.add_argument("--context", type=Path)
    batch.add_argument("--paid", action="store_true")
    batch.add_argument("--authorize-batch", action="store_true", help="Explicit evaluation authorization required even offline")
    return p


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    config = None
    run_dir = None
    try:
        config = Config.from_env()
        if args.source_dir:
            config = replace(config, source_dir=args.source_dir)
        if args.output_dir:
            config = replace(config, output_dir=args.output_dir)
        if args.command == "doctor":
            print(json.dumps({"python": sys.version.split()[0], "model": config.model,
                              "reasoning_effort": config.reasoning_effort,
                              "OPENAI_API_KEY_exists": bool(os.getenv("OPENAI_API_KEY", "").strip()),
                              "paid_enabled_in_environment": config.run_paid_tests,
                              "budget_usd": config.budget_usd, "pricing_file": str(config.pricing_file) if config.pricing_file else None,
                              "source_dir": str(config.source_dir.resolve()),
                              "source_files": [p.name for p in sorted(config.source_dir.glob("*.html"))]}, indent=2))
            return 0
        if args.command == "batch" and not args.authorize_batch:
            raise ValueError("Batch evaluation is disabled without --authorize-batch. Full benchmark is not authorized during development.")
        corpus = Corpus(config.source_dir)
        if args.command == "index":
            write_json(config.output_dir / "corpus_manifest.json", {"fingerprint": corpus.fingerprint, "documents": corpus.manifest})
            write_json(config.output_dir / "corpus_records.json", [r.to_dict() for r in corpus.records])
            print(f"Indexed {len(corpus.manifest)} documents and {len(corpus.records)} evidence records in {config.output_dir.resolve()}")
            return 0
        if args.command == "search":
            hits = SearchIndex(corpus).search(args.query, args.limit, args.regulation)
            print(json.dumps([{**record.to_dict(), "score": score} for record, score in hits], ensure_ascii=False, indent=2))
            return 0
        # Unique run directory preserves earlier runs, errors, and usage logs.
        run_name = now().replace(":", "-").replace("+", "_")
        run_dir = config.output_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=False)
        questions = [(args.id, args.question)] if args.command == "ask" else load_questions(args.file or config.benchmark_file)
        provider = OpenAIProvider(config, purpose="development" if args.command == "ask" else "evaluation") if args.paid else None
        context = deepcopy_context()
        history = []
        session = getattr(args, "session", None)
        if session and session.exists():
            state = load_object(session)
            if state.get("corpus_fingerprint") != corpus.fingerprint:
                raise ValueError("Session corpus changed; start a new session to avoid stale citations")
            context, history = state["context"], state["history"]
        if args.context:
            context.update(load_object(args.context))
        agent = Investigator(corpus, config, provider)
        summary = {"started_at": now(), "mode": "openai" if provider else "offline", "results": []}
        exit_code = 0
        for question_id, question in questions:
            result = agent.run(question, question_id, context, history)
            path = save_result(run_dir, result)
            summary["results"].append({"question_id": question_id, "status": result["status"], "path": str(path), "metrics": result["metrics"]})
            # History is navigation context, never a second source of legal authority.
            history.append({"question_id": question_id, "question": question, "status": result["status"],
                            "issues": result["issues"], "evidence_ids": [r["id"] for r in result["evidence"]],
                            "accepted_statements": [c["statement"] for c in result["assessment"]["claims"]]})
            history = history[-10:]
            if session:
                write_json(session, {"corpus_fingerprint": corpus.fingerprint, "context": context, "history": history})
            print(result["final_answer"])
            print(f"\nSaved: {path.resolve()}")
            write_json(run_dir / "run_summary.json", summary)
            if result["errors"]:
                exit_code = 2
                # Billing uncertainty or budget exhaustion must stop the whole batch.
                break
        summary["finished_at"] = now()
        if provider:
            summary["cumulative_budget"] = provider.ledger.summary()
        write_json(run_dir / "run_summary.json", summary)
        return exit_code
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        diagnostic = {"timestamp": now(), "status": "blocked", "error_type": type(error).__name__,
                      "message": str(error), "api_cost_usd": None}
        if config:
            write_json((run_dir or config.output_dir) / "startup_error.json", diagnostic)
        print(json.dumps(diagnostic, ensure_ascii=False), file=sys.stderr)
        return 2


def deepcopy_context():
    return dict(DEFAULT_CONTEXT)
