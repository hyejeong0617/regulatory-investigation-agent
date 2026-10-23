# Frozen v1 evaluation artifacts

Start with [the report](EVALUATION_REPORT.md) and [summary](evaluation_summary.json).
`raw/Q1` through `raw/Q10` contain complete JSON, Markdown and event logs. Q5 is
the preserved development smoke. The other nine questions were attempted once
after freezing; Q9 remains incomplete and was not retried.

`frozen_manifest.json`, `final_integrity_audit.json`, budget snapshots and the
checkpoint receipt are historical evidence. They retain original machine paths
and must not be treated as portable configuration or a live budget database.
`published_raw_hashes.json` verifies the exported raw files. The original frozen
archive is kept locally as a release asset, not silently rebuilt.

`archive/evaluate_original.py` is the unchanged original orchestration source,
archived for inspection only; its paths assume the original workspace layout.
`archive/pricing.verified.json` is the historical rate card, not current pricing.
Do not rerun a benchmark simply to view these saved results.
