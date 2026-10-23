# Architecture

The implementation is a bounded Python workflow with no third-party runtime dependencies.

| Component | Responsibility |
|---|---|
| `corpus.py` | Parse local HTML, preserve provision/table context, fingerprint evidence |
| `retrieval.py` | BM25 lexical ranking over corpus records |
| `schemas.py` | Strict investigation, assessment, review, and action JSON contracts |
| `agent.py` | Initial discovery, adaptive investigation, drafting, review, rendering |
| `llm.py` | Standard-tier OpenAI Responses requests and usage reporting |
| `budget.py` | Persistent cross-process reservations and usage settlement |
| `cli.py` | Offline and paid commands, session support, output persistence |

The four local tools are `search`, `lookup`, `neighbors`, and `linked`. No benchmark
IDs determine retrieval routes inside the agent. Model instructions are `COMMON`,
`PLAN_PROMPT`, `DRAFT_PROMPT`, and `REVIEW_PROMPT` in `agent.py`.

The default discovery searches the question, case terms, and each available regulation.
The model can propose up to four actions per investigation round. Draft claims require
exact quotations; code validates identifiers and quotes before a separate model call
checks support and coverage. Review can trigger additional retrieval and a second draft.
An interrupted review discards unreviewed claims. Observable decisions are logged;
hidden chain-of-thought is not recorded.

Frozen evaluation limits: 12 model calls, 32 tools, 4 investigation rounds, 6,000
maximum output tokens, 110,000 evidence characters, 600 seconds per question, and
120 seconds per request. The library defaults are 240/60 seconds; evaluation used
the same 600/120 overrides as the successful Q5 smoke.

This design favors auditable evidence and bounded execution over complex infrastructure.
Its limitations include lexical recall, imperfect table interpretation, missing external
acts, and correlated errors between drafting and review calls to the same model.
