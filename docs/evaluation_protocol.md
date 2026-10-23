# Frozen v1 evaluation protocol

The user authorized evaluation, not optimization. Before execution, the existing
Q5 smoke was checked, 39 offline tests passed, and source hashes, configuration,
model settings and corpus fingerprint were frozen. Agent logic was not changed.

Q1, Q2, Q3, Q4, Q6, Q7, Q8, Q9 and Q10 were each attempted once using gpt-6-luna,
medium reasoning, the original question file and the same five legal snapshots.
Each question ran in a fresh process with empty answer history. The prescribed
case was dried figs from Türkiye with aflatoxin B1 detected; unspecified shipment
facts remained unknown. Q3 received the original Q2 text; Q9/Q10 received preceding
question texts only. No earlier answers or retrieved evidence were shared.

Q5 is a pre-freeze development smoke with original Q4 text as context. It was not
rerun and must be distinguished from post-freeze evaluation results. No Gold
Standard or previous Build 1–4 answers were consulted for this evaluation.

Q9 returned an incomplete model response and was preserved without repair or retry.
The initial orchestration stopped; Q10 was subsequently run once as an independent
question under unchanged configuration. The next session recovered its completed
output and finalized the report without making additional API calls.

The same persistent ledger retained all prior usage and the $0.5295 transport
reservation. No budget resets or reconciliation occurred during evaluation. A
fresh clone does not carry that ledger and cannot claim to inherit its budget cap.

Results preserve final answers, original questions/context, evidence, citations,
accepted/rejected claims, observable investigation decisions, tool history,
unresolved issues, errors, and resource metrics. No correctness grading has been
performed. Source/quote integrity checks are not legal-quality judgments.
