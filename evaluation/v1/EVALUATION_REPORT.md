# Regulatory Agent v1 evaluation report

This GitHub-facing report uses relative links. Original answers are preserved byte-for-byte.
Model: `gpt-6-luna`; reasoning: `medium`. Q5 is the existing development smoke; all other questions are independent post-freeze evaluations.

| Question | Origin | Status | LLM calls | Tools | Input tokens | Output tokens | Reasoning tokens | Seconds | Estimated USD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Q1 | post-freeze evaluation | partial | 4 | 13 | 41932 | 6067 | 4587 | 54.1206 | 0.008274700 |
| Q2 | post-freeze evaluation | partial | 3 | 7 | 28195 | 2959 | 2050 | 28.505 | 0.005003650 |
| Q3 | post-freeze evaluation | partial | 4 | 9 | 44566 | 4050 | 2744 | 36.6992 | 0.007595450 |
| Q4 | post-freeze evaluation | partial | 8 | 25 | 203441 | 12271 | 8050 | 107.463 | 0.031565025 |
| Q5 | previous development smoke | partial | 6 | 23 | 82923 | 8638 | 4628 | 75.2485 | 0.013620175 |
| Q6 | post-freeze evaluation | partial | 7 | 13 | 79330 | 13542 | 8645 | 107.8974 | 0.016686725 |
| Q7 | post-freeze evaluation | partial | 6 | 13 | 83199 | 10454 | 6375 | 94.7365 | 0.015626425 |
| Q8 | post-freeze evaluation | partial | 6 | 15 | 100802 | 10310 | 7083 | 89.0164 | 0.017754800 |
| Q9 | post-freeze evaluation | incomplete | 5 | 21 | 109937 | 10887 | 6271 | 97.1893 | 0.019185250 |
| Q10 | post-freeze evaluation | partial | 6 | 25 | 118778 | 9833 | 5534 | 86.7524 | 0.019763300 |

## Budget

Nine new evaluation runs: $0.141455325. Selected Q1–Q10 inference: $0.155075500. Cumulative known usage: $0.156769550. Retained uncertain transport reservation: $0.529500000. Total accounted: $0.686269550 / $2. Remaining lower bound at finalization: $1.313730450.

## Execution and limitations

Q9 remains incomplete because its model response did not complete. It was not retried. Q10 was independently executed once after the initial runner stopped. All other selected results are partial assessments with no execution errors. No Gold Standard grading was performed.
The 39-test offline suite passed before freezing. Runtime/source hashes and Q5 hashes were verified after evaluation. Exact source quotations do not establish correctness; same-model review, lexical retrieval, complex tables and frozen legal snapshots remain limitations.

Observed tools across all selected questions: search 88, lookup 61, neighbors 15, linked 0. Total: 55 LLM calls, 164 tools, 893,103 input tokens, 89,011 output tokens, and 55,967 reasoning tokens already included in output. Sum of question wall times: 777.6283 seconds.

## Raw results

### Q1

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q1/question-Q1-32d833f3.json) · [markdown](raw/Q1/question-Q1-32d833f3.md) · [events](raw/Q1/question-Q1-32d833f3.events.jsonl)
Investigation rounds: 2; review rounds: 1; accepted claims: 4; rejected records: 0.
Errors: []

Unresolved issues:

- Whether this particular shipment is subject to an aflatoxin-specific Türkiye import-control measure cannot be established from the supplied evidence.
- The reported detection alone does not establish that the 6.0 μg/kg aflatoxin B1 maximum is exceeded; the concentration and unit are unknown.
- The supplied table excerpts do not resolve whether the Türkiye-specific aflatoxin checks apply to this shipment, including the effect of its precise product classification.
- The supplied records do not include the applicable sampling and analytical rules, and the frozen snapshots do not verify current law.
- No accepted claim addresses issue: Türkiye-specific entry controls

### Q2

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q2/question-Q2-8845886b.json) · [markdown](raw/Q2/question-Q2-8845886b.md) · [events](raw/Q2/question-Q2-8845886b.events.jsonl)
Investigation rounds: 1; review rounds: 1; accepted claims: 1; rejected records: 2.
Errors: []

Unresolved issues:

- Whether this shipment exceeds either maximum level or is compliant cannot be determined without its measured concentrations and confirmed classification.
- The assessment omits the numerical limits requested: the supplied dried-fig entry gives 6 μg/kg for aflatoxin B1 and 10 μg/kg for the sum of B1, B2, G1 and G2.
- The cited 2023/915 text is a frozen snapshot and does not establish that these levels are current law.
- Citation validation failed: Quote is not an exact meaningful passage from the cited record
- No accepted claim addresses issue: Dried-fig aflatoxin maximum levels

### Q3

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q3/question-Q3-9fc58f1a.json) · [markdown](raw/Q3/question-Q3-9fc58f1a.md) · [events](raw/Q3/question-Q3-9fc58f1a.events.jsonl)
Investigation rounds: 2; review rounds: 1; accepted claims: 4; rejected records: 0.
Errors: []

Unresolved issues:

- The supplied legal texts are frozen snapshots and do not establish which requirements apply on the shipment’s relevant date; current, date-specific law has not been verified.
- No accepted claim addresses issue: Direct-consumption dried-fig limit
- No accepted claim addresses issue: Sorting and physical-treatment category
- No accepted claim addresses issue: Processed products and Article 3 factors

### Q4

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q4/question-Q4-6866b007.json) · [markdown](raw/Q4/question-Q4-6866b007.md) · [events](raw/Q4/question-Q4-6866b007.events.jsonl)
Investigation rounds: 4; review rounds: 2; accepted claims: 6; rejected records: 0.
Errors: []

Unresolved issues:

- Whether Annex I temporary-increase listing applies to the shipment.
- The specific identity and physical check frequency applicable to this dried-figs tariff line.
- The supplied evidence identifies dried figs from Türkiye (CN 0804 20 90) in Annex II, but does not establish the applicable hazard-specific identity/physical-check frequency for that tariff line; blank table cells cannot resolve it.
- Whether dried figs from Türkiye are also listed in Annex I for temporarily increased controls is not established by the supplied Annex I excerpts.
- The supplied records are frozen snapshots, not verification of requirements applicable at the time of a particular shipment.
- For mycotoxin sampling, Regulation 2019/1793 Article 3 refers to Regulation 2023/2782, whose detailed sampling requirements are not included.
- No accepted claim addresses issue: 2019/1793 increased-control listing
- No accepted claim addresses issue: 2019/1793 special-entry-condition listing
- No accepted claim addresses issue: Conditions and documentary requirements
- No accepted claim addresses issue: Aflatoxin maximum level
- No accepted claim addresses issue: 2019/1793 Annex II special conditions for Turkish dried figs
- No accepted claim addresses issue: 2019/1793 Annex I increased-control listing
- No accepted claim addresses issue: 2023/915 aflatoxin B1 maximum level
- No accepted claim addresses issue: Whether Annex I temporary-increase listing applies

### Q5

Origin: previous development smoke; status: `partial`.
[json](raw/Q5/question-Q5-a08c925f.json) · [markdown](raw/Q5/question-Q5-a08c925f.md) · [events](raw/Q5/question-Q5-a08c925f.events.jsonl)
Investigation rounds: 4; review rounds: 1; accepted claims: 9; rejected records: 0.
Errors: []

Unresolved issues:

- The applicable Annex II hazard designation and check frequency for dried figs under CN 0804 20 90 cannot be established from the supplied row: its hazard and frequency cells are blank, and the 30% value shown for other CN codes cannot safely be attributed to it.
- The specific official-certificate requirement, if any, and prior-notification applicability for this shipment cannot be determined from the supplied evidence.
- The shipment’s compliance with aflatoxin limits cannot be assessed from detection alone without the concentration and relevant test details.
- The snapshots are not verified current law, so the currently applicable listing and requirements remain unconfirmed.
- The supplied dried-fig Annex II row has blank hazard and check-frequency cells. The applicable hazard designation and frequency cannot be established from these records, and the 30% frequency for other CN codes cannot be attributed to this row.
- The detailed sampling and analytical requirements in Regulation (EU) 2023/2782 were not supplied; whether its conditional rule applies to this Annex II entry also remains unresolved.
- The evidence does not establish whether an official certificate or prior notification is required for this particular consignment. Shipment classification, stage, and applicable category are not provided.
- Detection alone does not establish an exceedance. The shipment’s measured concentration and relevant analytical details are missing.
- No accepted claim addresses issue: Annex II listing and applicability to dried figs (Türkiye)
- No accepted claim addresses issue: Special import conditions: certificate, laboratory results, and entry notification
- No accepted claim addresses issue: Official-control sampling and analytical requirements
- No accepted claim addresses issue: Applicable aflatoxin limits and shipment-specific exceedance
- No accepted claim addresses issue: Whether dried figs (CN 0804 20 90) fall within Türkiye’s Annex II aflatoxin listing and control frequency
- No accepted claim addresses issue: Official sampling and analysis method for aflatoxins
- No accepted claim addresses issue: Applicable aflatoxin limits and whether the detected result exceeds them
- No accepted claim addresses issue: Whether special import conditions and supporting documents apply
- No accepted claim addresses issue: Prior notification and CHED requirements
- No accepted claim addresses issue: Aflatoxin maximum level and shipment-specific compliance
- No accepted claim addresses issue: Annex II applicability and check frequency for dried figs from Türkiye
- No accepted claim addresses issue: Special-import certificate and analytical-result requirements
- No accepted claim addresses issue: Mycotoxin sampling and analysis method

### Q6

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q6/question-Q6-f8bdff3f.json) · [markdown](raw/Q6/question-Q6-f8bdff3f.md) · [events](raw/Q6/question-Q6-f8bdff3f.events.jsonl)
Investigation rounds: 3; review rounds: 2; accepted claims: 9; rejected records: 1.
Errors: []

Unresolved issues:

- The specific competent authority cannot be identified without the Member State and border-control post; the records state that Member States designate authorities but do not name the authority for this consignment.
- The records do not establish that the detected Aflatoxin B1 level exceeds an applicable maximum or that non-compliance has been formally established. Shipment stage, product classification, intended use, and concentration are also unknown.
- The cited mycotoxin sampling rule points to Regulation (EU) 2023/2782, but its provisions are not supplied; the evidence therefore does not establish the sampling and analysis basis for the reported detection.
- No accepted claim addresses issue: General competent-authority duties after established non-compliance
- No accepted claim addresses issue: Member State designation of the competent authority
- No accepted claim addresses issue: Border competent-authority duties for entering consignments
- No accepted claim addresses issue: Actions after non-compliance is established

### Q7

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q7/question-Q7-0f27e1c3.json) · [markdown](raw/Q7/question-Q7-0f27e1c3.md) · [events](raw/Q7/question-Q7-0f27e1c3.events.jsonl)
Investigation rounds: 2; review rounds: 2; accepted claims: 8; rejected records: 3.
Errors: []

Unresolved issues:

- The supplied facts do not establish that aflatoxin B1 exceeds the applicable limit or that any authority has established non-compliance; therefore no action can be said to have been triggered for this shipment.
- For a non-compliant consignment entering the Union, Article 66 also provides for an order to destroy, re-dispatch, or subject the consignment to special treatment or another compliance measure; these specific follow-on options are not stated in the claims.
- The evidence identifies dried figs from Türkiye in the import-control listing, but does not establish from the supplied table context whether the aflatoxin hazard and control frequency apply to this specific product entry. CN/TARIC classification and shipment stage are also unknown.
- The supplied records refer to Regulation (EU) 2023/2782 for mycotoxin sampling and analysis, but its sampling and analysis rules are not supplied. The snapshots also do not verify current law.
- Citation validation failed: Quote is not an exact meaningful passage from the cited record
- No accepted claim addresses issue: Applicable aflatoxin maximum level
- No accepted claim addresses issue: Türkiye dried-fig import-control applicability

### Q8

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q8/question-Q8-6fbba5df.json) · [markdown](raw/Q8/question-Q8-6fbba5df.md) · [events](raw/Q8/question-Q8-6fbba5df.events.jsonl)
Investigation rounds: 2; review rounds: 2; accepted claims: 5; rejected records: 0.
Errors: []

Unresolved issues:

- The supplied records do not establish the current applicable sampling and analytical-method rules for an aflatoxin result. If the assessment relies on the detected result, those rules may also need checking; detection alone does not establish an exceedance.
- No accepted claim addresses issue: Türkiye-specific entry controls at Union entry
- No accepted claim addresses issue: General food-safety obligations
- No accepted claim addresses issue: Snapshot date and amendment verification

### Q9

Origin: post-freeze evaluation; status: `incomplete`.
[json](raw/Q9/question-Q9-c7c58bd6.json) · [markdown](raw/Q9/question-Q9-c7c58bd6.md) · [events](raw/Q9/question-Q9-c7c58bd6.events.jsonl)
Investigation rounds: 4; review rounds: 0; accepted claims: 0; rejected records: 0.
Errors: [{"type": "InferenceError", "message": "Model response incomplete; increase output allowance only within budget"}]

Unresolved issues:

- Investigation stopped before a verified assessment could be completed.

### Q10

Origin: post-freeze evaluation; status: `partial`.
[json](raw/Q10/question-Q10-80548726.json) · [markdown](raw/Q10/question-Q10-80548726.md) · [events](raw/Q10/question-Q10-80548726.events.jsonl)
Investigation rounds: 4; review rounds: 1; accepted claims: 8; rejected records: 0.
Errors: []

Unresolved issues:

- The records do not establish whether aflatoxin-specific increased identity or physical checks, or specific aflatoxin sampling and testing requirements, apply to this dried-fig consignment from Türkiye.
- The records do not provide enough shipment or analytical information to decide whether either dried-fig maximum level is exceeded.
- The supplied records do not include Regulation (EU) 2023/2782, so they cannot establish its applicable aflatoxin sampling and analytical requirements.
- The cited legislation is supplied only as frozen snapshots, not verified current law; the dried-fig classification, current Annex II conditions, and shipment-specific entry documentation still require confirmation.
- Without the measured concentration, total aflatoxins, and reliable analytical and product-classification details, the shipment's compliance status cannot be determined.
- No accepted claim addresses issue: Aflatoxin maximum levels and classification
- No accepted claim addresses issue: Operator duties and action on potential non-compliance
- No accepted claim addresses issue: Türkiye import controls and consignment documentation
- No accepted claim addresses issue: Current-law and shipment-specific verification
- No accepted claim addresses issue: Aflatoxin limits and product classification
- No accepted claim addresses issue: Türkiye import-control applicability and entry requirements
- No accepted claim addresses issue: Current-law and shipment-fact verification
- No accepted claim addresses issue: Türkiye import-control scope and consignment requirements
- No accepted claim addresses issue: Shipment facts and current-law verification
- No accepted claim addresses issue: Aflatoxin maximum levels and product classification
- No accepted claim addresses issue: Operator duties and action on confirmed non-compliance
