# Context Pack: Academic Research

## Purpose

Generate evidence-backed academic search plans, validate the search plan, match externally populated methods and check coverage/citations.

## Inputs

- `workspace/problem_understanding/official/final_problem_signature.json`
- Compatibility: `workspace/problem_signatures/case.signatures.json`
- External/Agent-populated `workspace/academic_search/official/search_results.json`

## Outputs

- `workspace/academic_search/official/search_results.json`
- `workspace/academic_search/official/method_matches.json`
- `workspace/method_plan/official/case.method_plan_summary.json`
- `workspace/academic_search/reports/search_plan_gate_report.json`
- `workspace/method_plan/reports/coverage_gap_analysis.json`
- `workspace/academic_search/reports/citation_validation.json`

## Public CLI

- `academic-search`
- `search-plan-gate`
- `method-recommend`
- `method-plan-synthesize`
- `coverage-gap-analysis`
- `citation-validate`

## Rules

- Do not fabricate search results.
- Search planning is allowed without network access.
- Real literature results must be externally supplied or Agent-populated and later validated.
