# Usage

Run commands from the repository root with Python 3.11+. An optional virtual
environment can be created with `python -m venv --without-pip .venv`.

## Offline commands

```bash
python -m regulatory_agent doctor
python -m regulatory_agent index
python -m regulatory_agent search "dried figs aflatoxin"
python -m regulatory_agent ask "Which requirements address this shipment?" --id example
python scripts/validate_offline.py
```

The application reads real environment variables; `.env.example` is documentation
and is not loaded automatically. `doctor` reports credential presence only.

## Paid operation

Live execution requires an existing `OPENAI_API_KEY` environment variable, an exact
model, an explicitly authorized cumulative budget, and a recently verified pricing
file. `config/pricing.example.json` deliberately has `verified=false`. Archived
evaluation rates are historical records, not fresh authorization or current pricing.
Verify rates against official model/pricing/cache documentation before enabling a
new live configuration. Pricing verification expires after seven days.

Example PowerShell configuration, after those prerequisites are satisfied:

```powershell
$env:INFERENCE_MODEL = 'gpt-6-luna'
$env:REASONING_EFFORT = 'medium'
$env:RUN_PAID_TESTS = 'true'
$env:MAX_DEVELOPMENT_TEST_API_SPEND_USD = '2'
$env:STATE_DIR = '.state'
$env:PRICING_FILE = 'config/pricing.verified.json'
$env:MAX_SECONDS_PER_QUESTION = '600'
$env:API_TIMEOUT_SECONDS = '120'
python -m regulatory_agent ask 'Which provisions are relevant to this shipment?' --id example --paid
```

The provider reserves a full-context worst-case request cost before sending it.
It settles reported usage, accounts for cached reads/writes and long-context rates,
and blocks when the remaining budget cannot cover a reservation. Unknown usage can
block subsequent requests. Never delete `.state/budget.sqlite3` to continue an
existing budget. No failed network request is automatically retried.

JSON, Markdown, event JSONL and run summaries appear under `outputs/<timestamp>/`.
Inspect `status`, `errors`, claims, unresolved issues, and metrics rather than only
the process exit code. `partial` is an assessment with gaps; `incomplete` indicates
interrupted execution. `scripts/smoke_q5.py` explicitly makes paid Q5 calls and must
not be run to reproduce the preserved v1 evaluation: Q5 was not rerun in that study.

## Independent evaluation

The CLI batch command shares answer history, so it was not used for the independent
v1 protocol. Each evaluated question used a fresh process and empty history. The
original orchestration script is preserved as an archival record, not a portable
rerun command. See the evaluation protocol before conducting a separately authorized
future evaluation. CI performs offline tests only and has no API credential.
