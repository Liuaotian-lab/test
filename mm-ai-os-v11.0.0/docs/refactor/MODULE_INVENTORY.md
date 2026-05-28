# Module Inventory — 7.4.0 Candidate-Official Split

Module status values: `stable`, `experimental`, `scaffold`, `deprecated`, `agent-generated-unreviewed`.

| module | status | python files | purpose |
|---|---|---:|---|
| `mmos/academic_research_engine/` | `stable` | 6 | Search planning, method matching, coverage and citation checks. |
| `mmos/agent_protocols/` | `experimental` | 6 | Auxiliary or competition-readiness subsystem. |
| `mmos/artifacts/` | `stable` | 6 | Output discovery, registration, build and package helpers. |
| `mmos/award_readiness/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/chart_digitizer/` | `experimental` | 9 | Auxiliary or competition-readiness subsystem. |
| `mmos/claim_evidence/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/cli/` | `stable` | 16 | Command-line entry point and command parser package. |
| `mmos/contest_commander/` | `experimental` | 3 | Auxiliary or competition-readiness subsystem. |
| `mmos/contracts/` | `stable` | 2 | Case and question contract scaffolding and validation. |
| `mmos/feedback/` | `experimental` | 4 | Auxiliary or competition-readiness subsystem. |
| `mmos/gates/` | `stable` | 6 | Quality and final gate checks. |
| `mmos/ingestion/` | `stable` | 2 | Document and data ingestion into case workspace artifacts. |
| `mmos/judge_simulation/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/kernel/` | `stable` | 6 | Core path, JSON, event and hashing utilities. |
| `mmos/method_plan/` | `stable` | 2 | Method plan synthesis and approval. |
| `mmos/modeling_innovation/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/optimism_control/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/paper_excellence/` | `experimental` | 4 | Auxiliary or competition-readiness subsystem. |
| `mmos/paper_latex/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/problem_graph/` | `stable` | 2 | Problem statement parsing into question graph artifacts. |
| `mmos/problem_intelligence/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/problem_signature/` | `stable` | 2 | Compatibility wrapper over problem understanding signatures. |
| `mmos/problem_understanding/` | `stable` | 13 | Evidence-backed problem understanding engine and gate. |
| `mmos/quality_oracle/` | `experimental` | 8 | Auxiliary or competition-readiness subsystem. |
| `mmos/red_team/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/repair_loop/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/semantic_audit/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/semantic_checks/` | `experimental` | 6 | Auxiliary or competition-readiness subsystem. |
| `mmos/solver_execution/` | `experimental` | 1 | Auxiliary or competition-readiness subsystem. |
| `mmos/solver_factory/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/submission/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/tournament/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |
| `mmos/verification/` | `experimental` | 1 | Auxiliary or competition-readiness subsystem. |
| `mmos/workflow_runtime/` | `experimental` | 2 | Auxiliary or competition-readiness subsystem. |


## v7.3 Added Modules

| module | status | purpose |
|---|---|---|
| `mmos/core/schema.py` | stable | Schema discovery, loading and JSON artifact validation. |
| `mmos/domain/` | stable | Lightweight dataclasses for schema-aligned domain objects. |
| `schemas/problem_understanding/` | stable | Contracts for evidence, question nodes and final signatures. |
| `schemas/academic_research/` | stable | Contracts for search plans, results, identified methods and citations. |
| `schemas/method_plan/` | stable | Contracts for method candidates, plans, reviews and approvals. |
| `schemas/agents/` | experimental | Contracts for Agent task cards, run reports and allowed-file manifests. |
| `schemas/gates/` | stable | Contracts for gate result payloads. |
| `schemas/workflow/` | experimental | Contracts for step result and case state records. |


## 7.4 Added Core Module

| Module | Status | Responsibility |
|---|---|---|
| `mmos/core/artifacts.py` | stable | Candidate/official artifact paths, promotion, migration and Agent write-policy evaluation. |

## v7.5 Additions

| Module | Status | Purpose |
|---|---|---|
| `mmos/synthetic/` | stable-regression-fixture | Deterministic synthetic E2E support for no-network pipeline regression. |
| `tests/e2e/` | stable-regression-fixture | End-to-end synthetic pipeline test. |
| `tests/golden/` | stable-regression-fixture | Golden snapshot stability tests for synthetic artifacts. |
