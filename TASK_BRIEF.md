# Build an EU Food Regulatory Investigation AI Agent — Independent AI Engineering Experiment

## Role and objective

Act as the lead AI engineer responsible for designing, implementing, testing, and documenting a complete, runnable **EU Food Regulatory Investigation AI Agent**.

Your task is to deliver working software, not merely an architecture proposal, tutorial, code snippets, or an untested notebook.

You are participating in an independent AI development experiment. Your implementation will be compared with an existing human-guided Agent development project and a separately developed AI-built implementation.

**Your primary objective:** Build the most reliable, evidence-grounded, and operationally useful regulatory investigation agent you can within the available development time and resources.

You are responsible for architecture decisions, implementation, debugging, testing, and documentation. Make reasonable engineering decisions autonomously. Ask for human assistance only when essential access, permissions, credentials, or genuinely blocking information is missing.

## 1. Regulatory use case

Develop an AI Agent capable of investigating questions concerning EU food safety and regulatory requirements.

The initial reference case is:

- Product: Dried figs
- Country of origin: Türkiye
- Hazard: Aflatoxin B1 detected
- Jurisdiction: European Union
- Investigation context: The exact concentration, product classification, shipment stage and compliance status may be unknown.

The user may ask about maximum contaminant levels, applicable import conditions, sampling and laboratory requirements, official controls, documentary obligations, business-operator responsibilities, regulatory enforcement or withdrawal/recall.

The system must also accept arbitrary regulatory questions within its provided document scope. **Do not hard-code responses, Article numbers, search routes or conditional logic for individual benchmark question IDs.**

## 2. Provided source materials

The clean workspace will contain the following frozen EU-law HTML documents in `data/`:

1. `EU_2023_915_consolidated_2026-08-19.html`
2. `EU_2019_1793_consolidated_2026-06-30.html`
3. `EU_2017_625_consolidated_2025-01-05.html`
4. `EU_2002_178_consolidated_2026-01-01.html`
5. `EU_2019__1013_original.html`

A separate file, `data/benchmark_questions_v1.json`, contains ten questions used for the eventual comparison.

Use the regulatory case context consistently across these questions, including questions that refer to previous topics or ask for a synthesis of legal conclusions.

You must design the document-processing and retrieval architecture yourself.

You will not receive existing retrieval indexes, previous Agent code, model outputs, benchmark solutions or Gold Standard answers.

The supplied documents are historical snapshots. Do not present them as verified current law. Internet access for installing dependencies and development documentation is allowed. Legal conclusions in the core benchmark must be based on the supplied corpus. Any optional live EUR-Lex or Cellar verification must be separately controlled, clearly labelled and logged.

## 3. Required Agent capabilities

### A. Autonomous regulatory investigation

The Agent must determine, based on the user's question:

- Which regulatory issues need to be investigated
- Which available regulations are potentially relevant
- Which specific Articles, Annexes, tables or provisions address those issues
- Whether the retrieved evidence supports the proposed legal conclusions
- Whether additional targeted investigation is needed before answering

It must not require the developer to provide the correct regulation or Article number in advance.

### B. Document discovery and retrieval

Implement reliable retrieval over the five supplied legal documents.

Preserve traceability to the original source document and relevant legal location.

Handle, where applicable, Articles, subsections, Annexes, tables, numbered rows and product-specific entries. Avoid losing legally meaningful relationships when parsing complex HTML tables.

You may choose lexical retrieval, semantic retrieval, hybrid search, exact provision lookup or another approach. Explain your choice and its trade-offs.

### C. Evidence-grounded reasoning

Every material legal conclusion must be supported by identifiable source evidence.

The final answer should identify the regulation and the specific Article, Annex or table entry wherever possible.

Do not invent legal requirements, numeric limits, document obligations, applicability decisions or citations.

Distinguish:

- Legal rules established by the source documents
- Application conditions and exceptions
- Shipment-specific facts that are unknown
- Matters requiring additional verification
- Current-law status that cannot be established from the frozen corpus

A contaminant being detected must not automatically be treated as proof that a maximum level has been exceeded.

### D. Evidence sufficiency and follow-up investigation

The Agent should evaluate whether it has enough relevant legal evidence to answer the user's actual question.

Having several retrieved documents or valid-looking citation IDs does not necessarily mean the investigation is complete.

When material evidence is missing, the Agent should be capable of targeted follow-up investigation, within explicit execution limits.

If a necessary conclusion cannot be supported, identify the missing information rather than fabricate an answer.

### E. Regulatory assessment output

Generate an understandable, professionally structured regulatory assessment that contains, as appropriate:

- Direct answer to the question
- Applicable legal requirements and supporting provisions
- Conditions, exceptions and unresolved facts
- Responsibilities of relevant operators or authorities
- Practical next steps for the food business operator
- Limitations concerning document coverage and legal currentness

Keep the response focused on the question. Do not substitute lengthy legal background for operationally important requirements.

## 4. Architecture autonomy

You are free to select the most appropriate technical architecture and framework.

Do not assume that LangGraph, smolagents, a multi-agent system, or any particular RAG architecture is required.

Evaluate whether a simpler workflow or an adaptive investigation process is sufficient to satisfy the capabilities above.

Use complexity only where it provides a clear functional benefit.

The implementation must demonstrate meaningful runtime decisions about evidence gathering or additional investigation. A static list of preselected answers or QID-specific provision routes does not satisfy this requirement.

Document your chosen architecture, its advantages, limitations and alternatives considered.

## 5. Development environment and resource controls

Use Python and the provided workspace.

Agent inference must use the same preselected LLM and configuration as the other implementations in this comparison.

Configuration:

- `INFERENCE_MODEL`: [SAME MODEL FOR BOTH AGENTS]
- `REASONING_EFFORT`: medium, where supported
- `SOURCE_DIR`: `data/`
- `BENCHMARK_FILE`: `data/benchmark_questions_v1.json`
- `MAX_LLM_CALLS_PER_QUESTION`: 12
- `MAX_DEVELOPMENT_TEST_API_SPEND_USD`: [PREAUTHORIZED LIMIT]
- `RUN_PAID_TESTS`: controlled explicitly

Use environment variables for credentials. Never hard-code or commit API keys.

Implement bounded tool calls, retries, timeouts and error handling. Allow economical execution without forcing every question through a full investigation loop.

If a spending limit is reached or cannot be reliably enforced, stop initiating additional paid calls and report the limitation.

Prioritize a working, testable Agent over a polished user interface. A CLI and batch runner are sufficient; a Streamlit application is optional.

## 6. Implementation deliverables

Produce a complete project with:

1. Runnable Python Agent implementation
2. Document parsing and retrieval components
3. Agent configuration and dependency files
4. Single-question command-line execution
5. Batch execution support for the supplied benchmark file
6. Structured JSON outputs for each question
7. Source-grounded citations and evidence records
8. Execution metrics and diagnostic logs
9. Automated tests and at least one actual end-to-end smoke test where credentials and budget permit
10. A complete README explaining setup, architecture, execution, testing and limitations

The implementation must work from a clean environment using documented commands.

Do not claim that a component has been tested unless the test was actually executed.

## 7. Required observability and metrics

For every question, save:

- Question ID and input context
- Final answer
- Regulations and provisions retrieved
- Source evidence IDs and citation locations
- Tool calls and search queries
- Additional investigation or retry events
- Number of LLM calls
- Input tokens, output tokens and reasoning tokens where reported
- Wall-clock execution time
- API cost, if it can be calculated from verified usage and pricing
- Errors, incomplete steps and limitations

The outputs must permit an independent evaluator to review the answer and its supporting evidence.

Do not report internal reasoning text or hidden chain-of-thought. Record observable decisions, tool actions, evidence and outcomes.

Maintain a separate **development log** with:

- Development start and finish timestamps
- Framework and inference model choices
- Major implementation steps
- Tests executed and their results
- Errors encountered and fixes applied
- Human assistance or interventions requested
- Paid API usage during development
- Known unfinished requirements

Development cost and Agent inference cost must be distinguishable.

If a metric is unavailable, record `null` or `not measured`. Never invent usage, time or cost numbers.

## 8. Validation and acceptance criteria

Before declaring completion:

- Confirm that the application can install and start from the documented commands.
- Verify that it loads and searches the supplied legal corpus.
- Demonstrate dynamic identification of relevant regulations and provisions without QID-specific routing.
- Verify that citations point to actual retrieved source records.
- Check that unsupported or unavailable evidence produces an explicit uncertainty statement.
- Test at least one multi-provision regulatory question.
- Test an insufficient-evidence or missing-source situation.
- Execute and inspect at least one real question with the configured LLM, if permitted.
- Verify that JSON outputs and usage logs are written correctly.
- Confirm that the README matches the actual implemented system.

You may run additional development tests within the agreed resource budget.

Do not use external Gold Standard answers, historical model results or previous Agent implementations to optimize the benchmark.

## 9. Development autonomy and stopping conditions

Proceed through architecture selection, implementation, testing and correction without waiting for step-by-step approval.

Make reasonable choices when minor implementation details are unspecified.

Do not stop after generating a plan or an initial code draft.

Continue debugging until the acceptance criteria are met or a genuine technical, permission or budget blocker prevents further progress.

Do not exceed the authorized API budget or take actions outside the provided workspace without permission.

If complete implementation is not possible, deliver the functioning components, test evidence, unresolved issues and exact reproduction instructions rather than claiming full completion.

## 10. Final handoff

At completion, provide:

**A. Implementation status:** completed, partially completed or blocked, with evidence.

**B. Architecture explanation:** major components, research workflow, tool selection and stopping logic.

**C. Runnable artifacts:** source files, dependencies, configuration, tests, execution commands and documentation.

**D. Validation report:** tests run, results and remaining defects.

**E. Efficiency report:** development elapsed time, recorded human interventions, model/API usage and costs, and Agent runtime metrics.

**F. Limitations:** regulatory coverage, source currentness, incomplete requirements and risks.

The final result must be independently runnable and evaluable.

**Start implementation now using the supplied files. The goal is a complete, tested software artifact—not a conceptual demonstration.**