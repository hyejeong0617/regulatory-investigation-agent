# Regulatory Investigation AI Agent

A Python investigator over the five supplied frozen EU food-law HTML documents.
It discovers provisions through local retrieval, lets the configured model request
targeted follow-up searches, and publishes only claims that pass citation checks
and a separate model review. No previous agent repository or implementation was used.

**Validation status (2026-10-22):** 39 offline tests pass. The authorized live Q5
smoke completed with `gpt-6-luna`, medium reasoning, six calls and no execution
errors. It returned a partial assessment with nine cited claims; it is not a
complete legal-answer validation. Known-usage development cost is $0.015314225;
including the first failed connection's retained upper bound, the ledger accounts
for $0.544814225 of the $2 cap. The full benchmark has not been run.
See `validation/report.json`, `validation/live_smoke_report.json`, and
`DEVELOPMENT_LOG.md` for evidence. `CHECKPOINT.md` describes the older offline ZIP.

## Quick start (no downloads)

Requires Python 3.11 or newer. All runtime and test code uses the standard library.
Run commands from this project folder. On Windows PowerShell:

```powershell
python -m venv --without-pip .venv
.\.venv\Scripts\python.exe -m regulatory_agent doctor
.\.venv\Scripts\python.exe -m regulatory_agent index
.\.venv\Scripts\python.exe -m regulatory_agent search "dried figs aflatoxin maximum level"
.\.venv\Scripts\python.exe -m regulatory_agent ask "Which provisions address import documentation and withdrawal duties for this shipment?"
```

On macOS/Linux use `.venv/bin/python` instead. A virtual environment is optional;
`python -m regulatory_agent ...` works directly. No package installation is needed.
`requirements.txt` documents the empty runtime dependency set. `pyproject.toml`
also supports ordinary package installation using setuptools when available;
the documented no-install module commands are the validated path.

The default `ask` command produces an **offline evidence pack**, explicitly marked
`evidence_only`. It makes no LLM calls and does not pretend to provide a legal
assessment. Source excerpts are in its JSON evidence records. Add `--paid` only
after live testing has been resumed and the checks below have been completed.

Global options precede the command:

```powershell
python -m regulatory_agent --source-dir data --output-dir outputs ask "Your question"
```

## Case facts and follow-up questions

Default case: dried figs, Türkiye, aflatoxin B1 detected, EU jurisdiction. The
concentration, units, total aflatoxins, classification, intended use, shipment
stage, and compliance status remain unknown. Detection does not mean exceedance.

`--context facts.json` merges explicit facts into this default case; use `null`
for unknown values. Change product/origin/hazard for another case. Example:

```json
{"product":"Dried figs","country_of_origin":"Türkiye","intended_use":null,"concentration":null}
```

```powershell
python -m regulatory_agent ask "Which import documents matter?" --context facts.json --session outputs/case.json
python -m regulatory_agent ask "Which operator is responsible for those steps?" --session outputs/case.json
```

The session preserves facts, questions, coverage issues, accepted statements and
evidence IDs. Previous statements are navigation context, not legal authority;
the agent must cite source records again. Sessions reject a changed corpus
fingerprint. A maximum of ten previous turns is passed to the model.

## Inference configuration and spending controls

The agreed model is **`gpt-6-luna`**, with **medium** reasoning. There is no model
fallback. The authorized cumulative development API budget is **USD 2**. The user
subsequently requested a pause before any paid calls; leave `RUN_PAID_TESTS=false`
until that work resumes. `.env.example` documents all settings; the application
reads real environment variables and does **not** automatically load `.env`.

After resumption, set `OPENAI_API_KEY` securely in the execution environment.
`doctor` reports only whether it exists, never its value. Do not put it in source,
configuration files, command examples, logs, or chat.

Paid operation requires all of:

1. `--paid` on the command and `RUN_PAID_TESTS=true` in the environment.
2. The exact `INFERENCE_MODEL`, valid credentials, and a positive spending limit.
3. `PRICING_FILE` pointing to a recently verified pricing JSON file.
   `config/pricing.verified.json` was verified against official documentation on
   2026-10-22. Verification expires after seven days. The example stays disabled.

```powershell
# Run only when paid development testing is authorized:
$env:INFERENCE_MODEL = "gpt-6-luna"
$env:REASONING_EFFORT = "medium"
$env:MAX_DEVELOPMENT_TEST_API_SPEND_USD = "2"
$env:PRICING_FILE = "config/pricing.verified.json"
$env:RUN_PAID_TESTS = "true"
python -m regulatory_agent ask "For this shipment, which provisions establish contaminant limits and operator responsibilities?" --paid --id live-smoke
```

The adapter uses OpenAI Responses with strict JSON output, `store=false`, standard
service tier, and no built-in paid tools. Before each request it reserves the
entire model context window at the highest cache-write rate, including long-context
multipliers, plus maximum output cost in a persistent SQLite ledger. There is no
token-count endpoint call or assumption that token counting is free. With 6,000
maximum output tokens the reservation is $0.5295 per call. Actual usage settles
at the appropriate short/long-context rates. Cached-input and output usage are
accounted separately. Reasoning tokens
are already part of output tokens and are not billed twice.

The ledger is `.state/budget.sqlite3`, shared across runs and processes. Pending
reservations block concurrent generation. Missing usage, ambiguous transport
failures, unexpected model identifiers, and unknown cache-write charges block
subsequent paid requests. Network requests are never automatically retried.
Keep this ledger across restarts; changing/deleting it loses the cumulative cap.
An explicit reconciliation can permanently account for an uncertain call at its
entire reserved upper bound. Actual usage remains unknown; the amount is never
refunded. This allows a deliberate retry only when the remaining budget still
covers another full reservation. It is not an automatic retry mechanism.
The cap covers requests made by this project, not unrelated account usage.
Costs are USD estimates from verified rates and reported usage, not invoice totals.
There is no live internet legal lookup in this implementation.

Cache-write usage is priced from the reported retention breakdown when present.
For aggregate-only writes, this adapter uses the documented 30-minute default:
it sends plain text with no request-level or per-part TTL override. Inconsistent
reported breakdowns still stop inference. If cache settings are changed, the
pricing contract and tests must be updated together.

For the authorized Q5-only smoke test, from the project directory:

```powershell
# Only needed when the shell did not inherit the existing Windows user variable:
$env:OPENAI_API_KEY = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'User')
.\.venv\Scripts\python.exe scripts/smoke_q5.py
```

This script fixes the model to `gpt-6-luna`, medium reasoning, and a cumulative
$2 cap using the existing ledger. Q4 text is context only; only Q5 is executed.
Results are under `outputs/live-smoke/<timestamp>/question-Q5-a08c925f.json`,
with Markdown, events JSONL and `run_summary.json` alongside. Inspect status,
errors, accepted claims/citations and token/cost metrics; exit code alone does not
establish answer completeness. A partial assessment explicitly lists evidence gaps.

## Architecture and investigation process

1. **Parse and fingerprint.** A small `html.parser` DOM ignores scripts/styles,
   retains paragraph numbering and inline subscripts, and identifies Articles,
   Annexes and legal tables. Each source and record has a SHA-256-based identity.
   Records include filename, regulation number as printed, snapshot date, source
   lines, HTML anchor, canonical URL, and normalized text.
2. **Preserve tables.** Rowspan/colspan expansion retains original cell positions.
   Header rows travel with data rows, including units and contaminant names.
   Referenced footnotes are attached where recognized. Some import tables use
   blanks and place hazards/frequencies midway through a visual product block:
   these are retained as labelled sibling-row context, never forward-filled into
   a guessed requirement. Raw cells and origin coordinates remain in JSON.
3. **Discover.** BM25 ranks the question and case facts across the entire corpus,
   with a small per-document discovery pass. There are no benchmark-ID routes,
   stored benchmark answers, or product-specific legal conclusions in the agent.
4. **Investigate.** The model receives the document/provision catalog and retrieved
   evidence. It identifies coverage issues, decides whether evidence is sufficient,
   and can request lexical search, exact provision lookup, neighboring rows, or
   internally linked records. Actions and missing evidence are logged, not private
   reasoning. Duplicate actions and no-progress loops stop early.
5. **Assess and check.** The model writes atomic claims with conditions and exact
   quoted support. A deterministic validator rejects unknown IDs and fabricated
   quotes. A separate model call checks entailment, exceptions, scope, numbers,
   actors, and missing issues; it can request another targeted retrieval pass.
   Rejected claims are withheld. An interrupted reviewer cannot publish a draft.
6. **Render and persist.** The answer is rendered from accepted claims, unknown
   facts and unresolved issues. Every planned issue without an accepted claim is
   explicitly marked unresolved. JSON, Markdown, JSONL diagnostics, and a run
   summary are saved. No hidden reasoning or raw API response objects are saved.

Execution limits default to 12 generation calls per question, 32 retrieval calls,
four planning rounds, at most two synthesis/review cycles, a 240-second question
deadline and 60-second HTTP timeouts. Completed malformed JSON may receive one
format-repair call within the same allowance. At most six hits per search and
twelve parts per exact lookup are returned. Evidence text is capped at 110,000
characters; truncation is reported. The HTTP timeout bounds an individual blocking
operation; total wall time may slightly exceed the question deadline during cleanup.

Lexical retrieval was chosen for inspectability, exact legal terminology and zero
embedding cost. Its weaknesses are paraphrase recall and ranking duplicate table
rows. Adaptive query reformulation and neighboring-row lookup help, but cannot
guarantee complete legal coverage. Embeddings/hybrid search are a possible later
improvement; a multi-agent framework was unnecessary for this bounded workflow.

## Outputs and metrics

Each `ask` or `batch` run gets a unique timestamped output directory. For each question:

- `question-<safe-id>-<hash>.json`: input context/history, answer, claims, evidence,
  source manifests, retrieved provisions, tool queries/actions, review outcomes,
  errors, limitations and metrics.
- Matching `.md` and `.events.jsonl`: readable answer and observable execution events.
- `run_summary.json`: result paths, status, metrics and cumulative budget summary.

Metrics include actual generation attempts, workflow calls, retrieval calls,
input/output/reasoning tokens when reported, wall time and calculable API cost.
Unavailable metrics are `null`. Offline generation calls and cost are zero;
test-double workflow calls must not be mistaken for real inference. Development
and evaluation costs have separate ledger labels but share the cumulative limit.
Startup failures return exit code 2 and write `startup_error.json`; successful
offline or partially answered results return 0 unless execution errors occurred.

Status values: `evidence_only`, `assessed`, `partial`, `insufficient_evidence`,
`incomplete`, and `blocked`. `assessed` means the implemented checks passed,
not independently established legal correctness.

## Batch evaluation (not authorized during development)

The provided JSON format is supported without hard-coded question IDs. The runner
processes questions in file order and carries case context and history forward.
It stops the batch on an execution/budget error. It requires an explicit gate,
including offline mode, to prevent accidentally running the held-out benchmark.

```powershell
# For a separately authorized evaluation after freezing the implementation:
python -m regulatory_agent batch --file data/benchmark_questions_v1.json --authorize-batch --paid
```

Do not execute that command during the current development checkpoint. Only a
synthetic two-question file is used to test batch mechanics.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/validate_offline.py
```

The validation script removes credentials from child environments, forces offline
mode, runs unit/integration tests, checks CLI startup, indexes the real corpus,
and executes one original multi-provision smoke question. It does not run the
supplied Q1–Q10 benchmark. Logs and a machine-readable report are written under
`validation/`. Tests cover real source structure plus synthetic model/HTTP
contracts; mocked semantic review cannot establish model answer quality.

## Scope and limitations

The five documents have different snapshot dates and include one original act.
They do not establish verified current law or contain every externally referenced
sampling/analytical act. The system must identify such gaps. Complex table layout
can remain ambiguous; sibling context is evidence for review, not automatic
applicability. Exact matching quotes verify provenance, not entailment. The
semantic reviewer shares the same model and may share its mistakes. There are no
claims of benchmark performance, live API compatibility or legal completeness
until those are actually evaluated.

The API integration follows the official [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs)
and [prompt-caching documentation](https://developers.openai.com/api/docs/guides/prompt-caching).
Model and rate references are the official [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [pricing page](https://developers.openai.com/api/docs/pricing), consulted on
2026-10-22. These development references are not legal evidence.
