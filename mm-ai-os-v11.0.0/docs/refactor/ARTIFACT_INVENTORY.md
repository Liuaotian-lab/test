# Artifact Inventory — 7.4.0 Candidate-Official Split

This document records the main case artifacts consumed by the v7.1-compatible workflow preserved in v7.2.

| stage | artifact | role |
|---|---|---|
| ingestion | `workspace/problem_corpus.md` | Unified problem text corpus. |
| ingestion | `data/manifest/data_manifest.json` | Raw data and attachment manifest. |
| parsing | `workspace/problem_graph.json` | Parsed question graph. |
| parsing | `registry/questions_registry.json` | Question registry consumed by contract activation. |
| understanding | `workspace/problem_understanding/evidence_index.json` | Evidence slices from the problem corpus. |
| understanding | `workspace/problem_understanding/final_problem_signature.json` | Canonical v7 problem understanding output. |
| understanding | `quality/understanding_gate_report.json` | Understanding gate report. |
| compatibility | `workspace/problem_signatures/case.signatures.json` | Compatibility artifact for older research modules. |
| research | `workspace/academic_search/search_results.json` | Search plan plus externally populated search results. |
| research | `workspace/academic_search/method_matches.json` | Extracted or matched method candidates. |
| method plan | `workspace/method_plan/case.method_plan_summary.json` | Case-level method plan summary. |
| contracts | `contracts/questions/<QID>/*.json` | Per-question execution contracts. |
| execution | `results/<QID>/outputs/solution_real.json` | Question solution result. |
| quality | `final_outputs/final_gate_check.json` | Final gate report. |
| package | `package/package_manifest.json` | Submission package manifest. |


## v7.3 Schema Artifacts

| artifact | purpose |
|---|---|
| `schemas/problem_understanding/final_problem_signature.schema.json` | Contract for final problem understanding signatures. |
| `schemas/academic_research/search_results.schema.json` | Contract for planned and externally populated academic search results. |
| `schemas/method_plan/method_plan.schema.json` | Contract for per-question and case-level method plans. |
| `schemas/gates/gate_result.schema.json` | Generic quality gate result contract. |
| `tests/fixtures/schemas/**` | Valid and invalid fixtures for schema regression tests. |


## 7.4 Governed Artifact Layout

| Area | Candidate | Official | Reports |
|---|---|---|---|
| Problem understanding | `workspace/problem_understanding/candidate/` | `workspace/problem_understanding/official/` | `workspace/problem_understanding/reports/` |
| Academic search | `workspace/academic_search/candidate/` | `workspace/academic_search/official/` | `workspace/academic_search/reports/` |
| Method plan | `workspace/method_plan/candidate/` | `workspace/method_plan/official/` | `workspace/method_plan/reports/` |
| Paper | `paper/candidate/` | `paper/official/` | `paper/reports/` |

Legacy flat paths are compatibility mirrors. New workflow code should prefer official artifacts.

## v7.5 Synthetic E2E Artifacts

| Artifact | Producer | Consumer |
|---|---|---|
| `tests/fixtures/synthetic_cases/thermal_optimization_minimal/raw/problem_statement.md` | fixture | synthetic E2E pipeline |
| `tests/fixtures/synthetic_cases/thermal_optimization_minimal/raw/observations.csv` | fixture | synthetic E2E pipeline |
| `tests/fixtures/synthetic_cases/thermal_optimization_minimal/expected/*.golden.json` | `synthetic-write-golden` | golden tests |
| `cases/<case>/quality/synthetic_e2e_report.json` | `synthetic-e2e-run` | E2E diagnostics |
