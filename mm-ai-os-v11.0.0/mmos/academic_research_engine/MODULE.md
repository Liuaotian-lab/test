# Module: Academic Research Engine

## Purpose

Generate evidence-backed search plans, validate search plans, match externally populated methods, and check research coverage.

## Inputs

- `workspace/problem_understanding/final_problem_signature.json`
- `workspace/problem_signatures/case.signatures.json`
- `workspace/academic_search/search_results.json`

## Outputs

- `workspace/academic_search/search_results.json`
- `workspace/academic_search/method_matches.json`
- `quality/search_plan_gate_report.json`
- `quality/coverage_gap_analysis.json`
- `quality/citation_validation.json`

## Public CLI

- `academic-search`
- `search-plan-gate`
- `method-recommend`
- `coverage-gap-analysis`
- `citation-validate`

## Do Not

- Do not fabricate literature results.
- Do not fall back to model self-knowledge as if it were academic evidence.
