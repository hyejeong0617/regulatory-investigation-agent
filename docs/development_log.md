# Development log

> **Historical development log (not current operating status).** This document retains the original development sequence, including temporary blockers, old local paths, early test counts and interrupted stages. The final frozen Codex-built v1 was subsequently tested and evaluated in October 2026. For the current implementation and instructions, see [README](../README.md); for actual Q1–Q10 results, see [v1 evaluation report](../evaluation/v1/EVALUATION_REPORT.md). A separate AI-assisted quality assessment has been discussed but is not yet human-verified. Historical notes below are not claims about the current state.

## Final timeline and interpretation

- **Offline implementation:** source parsing, BM25, local retrieval tools, citation checks, structured agent and budget gate were built; 33 tests passed at an intermediate checkpoint.
- **Live Q5 smoke test:** later authorized; 39 offline tests and a partial Q5 model-generated assessment were recorded.
- **Freeze:** v1 code, corpus and evaluation configuration were frozen before the nine additional evaluation questions.
- **Post-freeze evaluation:** Q1–Q4 and Q6–Q10 were attempted; Q9 remained incomplete and was not retried. Q5 remained the existing pre-freeze smoke, not an independent post-freeze test.
- **Publication:** final code, law snapshots and raw outputs were published as a separate GitHub repository. See [publication provenance](publication.md). No original results were regenerated for this documentation cleanup.


## Scope and authorization

- Built independently from `TASK_BRIEF.md`, the five supplied HTML files and the
  provided question-file format. The previous `Regulatory_agent` repository,
  external benchmark answers and historical model outputs were not accessed.
- First recorded development timestamp: **2026-10-22 09:37:54 UTC**
  (**11:37:54 Europe/Berlin**). Initial brief reading preceded this captured timestamp;
  total elapsed time is therefore measured from this recorded point.
- Offline checkpoint finish and measured elapsed seconds are recorded in
  `validation/development_metrics.json`. This is a checkpoint, not a claim that
  live-model acceptance is complete.
- User supplied the model (`gpt-6-luna`), medium reasoning, a USD 2 total development
  API ceiling, authorization for essential paid smoke testing, and prohibition on
  running the full Q1–Q10 benchmark during development.
- A credential-presence check returned false without exposing any key value.
- User then requested completion of offline work and a checkpoint before restart,
  with **no paid API calls yet**. That pause remains in force.

## Architecture and implementation

Python 3.11+ standard-library implementation; developed and tested on Python 3.13.5.
No runtime framework, embedding service, third-party runtime package, or subagent
was used. The only configured inference model is `gpt-6-luna`, medium reasoning.

Implemented:

- HTML DOM parsing, Article/Annex boundaries, preserved inline text/numbering,
  original-source hashes, HTML anchors/line ranges and canonical URLs.
- Span-aware table grids, header/units context, linked footnotes and explicit
  sibling context for visually grouped import entries with blank cells.
- BM25 retrieval, regulation filtering, exact provision lookup, neighboring
  records and internal-link lookup.
- Bounded model investigation, structured claims, exact quote/citation checks,
  independent semantic review, targeted follow-up and explicit coverage gaps.
- CLI, context/session persistence, sequential batch runner with explicit gate,
  atomic JSON outputs, Markdown answers and JSONL observable-event logs.
- OpenAI Responses adapter, strict schemas, token preflight, persisted SQLite
  reservations, usage/cost accounting and fail-closed uncertain billing.
- Offline tests, a reproducible validation runner, README and restart checkpoint.

Official OpenAI documentation was consulted for API engineering only. No live
legal search was used to derive benchmark conclusions. Pricing example values
were read from official documentation but are intentionally **not enabled**:
token-count billing and cache-write accounting still require confirmation.

## Errors discovered and fixes

1. Windows terminal encoding initially failed while inspecting Unicode text.
   Developer inspection and CLI output now use UTF-8; no source files were changed.
2. Initial paragraph-only parsing omitted operative text stored in `div.norm`.
   Added whole numbered div paragraphs and regression coverage for withdrawal duties.
3. Footnote ancestor selection initially captured a whole notes table. Restricted
   it to the individual note wrapper, improving accuracy and retrieval ranking.
4. Filenames normalize all acts as year/number, but older legal titles can use
   number/year. Regulation identifiers now use the printed legal title.
5. First unit-test runs stalled in `tempfile.mkstemp` outside the project. A
   traceback identified the path; test scratch directories now stay under
   `.test_tmp/` in the writable project. Interrupted runs are not counted as passes.
6. Reviewed SQLite connection lifetime and explicitly close connections after
   transactions, preventing leaked handles on Windows.
7. Added explicit coverage gaps for issues with no accepted claim; a rejected or
   interrupted review never permits an unsupported draft into the final answer.

## Tests actually executed

- Initial successful system-Python run: **33 tests passed**, unittest reported
  **4.497 seconds**.
- Final clean virtual-environment validation: **33 tests passed**; exact logs,
  commands, timestamps and process durations are in `validation/report.json` and
  `validation/unit_tests.log`.
- Clean environment created with `python -m venv --without-pip .venv`.
  The standard-library application runs without package downloads or installation.
- `doctor`, `index`, and one original offline multi-provision smoke question passed
  in that environment. End-to-end offline validation took **9.154 seconds**.
- Parsed **5 documents / 2,264 evidence records**. The smoke question retrieved
  **11 records across 5 regulations**, with **7 local retrieval calls**. Its
  measured investigation loop was **0.0069 seconds**, excluding corpus loading;
  the whole smoke command took **2.661 seconds**.
- Inspected the smoke JSON and confirmed that every evidence ID, source hash and
  excerpt resolves to the actual in-memory source records. No legal conclusion was
  generated in offline mode.
- Synthetic model/HTTP doubles exercised adaptive retrieval, multi-provision
  synthesis/review, unsupported citation rejection, missing sources, review
  interruption, usage logging, persistent budget caps and ambiguous billing.
- A synthetic two-question file tested batch mechanics. The supplied full Q1–Q10
  benchmark was **not executed**, offline or paid.

No real-model answer, actual API transport, real API billing response, or legal
answer quality has been validated. Mocked responses are never reported as paid
calls or live model evidence.

## Human interventions and efficiency

Two follow-up user interventions affected development after the initial task:
the model/budget clarification and the request to checkpoint before restart.
There were **two clarification requests** from the agent:
missing model/budget authorization and missing environment credentials. Both are
recorded in this conversation. No step-by-step implementation approval was sought.

Development paid API requests: **0**. Input/output/reasoning API tokens: **0**.
Development API cost: **USD 0**. Agent live-inference cost: **USD 0**.
The editor assistant's own token usage/cost is **not measured** and is separate
from the application's authorized development API budget. No LLM tokens or cost
were invented for offline tests. The cumulative live budget ledger has not been
created; isolated test ledgers and an explicitly labelled diagnostic ledger were
used only locally, then cleaned up.

## Remaining acceptance work

- Refresh credentials by restarting Codex, then check presence without printing.
- Resume paid-testing authorization before any paid request.
- Verify exact API token-count billing, current model/pricing compatibility and
  cache-write cost semantics. Keep the disabled example disabled until resolved.
- Run one economical real `gpt-6-luna` end-to-end smoke question within the total
  USD 2 limit. Inspect its legal claims against source records, actual usage and
  any runtime incompatibility; debug within the same budget.
- Record final live-validation results and freeze the implementation before the
  separately authorized benchmark evaluation.

Known limitations: lexical recall; ambiguous visual table grouping; fixed evidence
and tool limits; incomplete external-act coverage; different source snapshot dates;
same-model review can share errors. See README for operational details.

## Manual Q5 launch preparation — 2026-10-22

Inspected the actual README, configuration, CLI, adapter, budget ledger and supplied
Q5 text. No enabled pricing file or live budget ledger was present. User will run
the live test manually; no live test or full benchmark was executed here.

One necessary implementation correction: cache-write retention fields were named
`ephemeral_30m_tokens` / `ephemeral_12h_tokens`; the official prompt-caching guide
documents `ttl_30m_tokens` / `ttl_12h_tokens`. Updated those two lookups and added
regressions for both correctly reported writes and an inconsistent breakdown.
Official reference: https://developers.openai.com/api/docs/guides/prompt-caching

Executed `.venv\\Scripts\\python.exe -m unittest discover -s tests -v`:
**35 tests passed in 3.289 seconds**. This is newer than the preserved 33-test
checkpoint report. No paid model requests were made; development API spend remains
zero. Token-count endpoint billing still lacks explicit verification, so no enabled
pricing file was created and no budget guard was bypassed. The manual launch must
stop at a local pricing preflight until this prerequisite is satisfied.


## Pricing repair and authorized Q5 live smoke — 2026-10-22

Created config/pricing.verified.json from official model, pricing and prompt-cache
references. Removed the token-count endpoint dependency. Each Responses request
reserves the entire 1,050,000-token model context at the highest cache-write rate
and long-context multipliers, plus maximum output cost ($0.5295 at 6,000 output).
Actual costs include long-context pricing, cache reads/writes and output tokens.
Aggregate cache writes use the documented 30m default because requests contain no
TTL overrides. Response model and standard service tier are checked before settlement.

Windows User environment credentials were passed only into the child process;
no credential was printed or saved. Initial sandbox connection failed; the entire
$0.5295 reservation was permanently retained with actual cost unknown. Explicit
upper-bound reconciliation never refunds this amount. An outside-sandbox API
request succeeded but exposed aggregate cache-write reporting. Official default
TTL documentation allowed its $0.00169405 usage estimate to be reconciled.
Both reconciliation records are saved in validation/ and original failures retained.

All 39 offline tests and the full offline validation script passed before the final
live retry. No packages were installed. Q5 alone then completed in 75.2485 seconds,
6 model calls, 82,923 input and 8,638 output tokens (4,628 reasoning tokens already
included). Its cost estimate is $0.013620175. Nine accepted claims were rechecked
against the original corpus with no citation/quotation failures. No execution errors.

The answer status is partial: unresolved frequency, certificate and notification
applicability, external-act coverage and snapshot currency prevent a completeness
claim. Accumulated issue labels also produce redundant unresolved-issue warnings.
This smoke validates live integration, not legal accuracy or benchmark performance.
The complete Q1-Q10 benchmark was NOT executed.

Known-usage cumulative estimate: $0.015314225. Including the unknown first connection
at its full retained upper bound: $0.544814225 accounted, leaving at least
$1.455185775 within the $2 cap. Preserve .state/budget.sqlite3 across all future runs.
See validation/live_smoke_report.json and outputs/live-smoke/
2026-10-22T18-26-39.920679_00-00/. README and the historical checkpoint notice updated.
