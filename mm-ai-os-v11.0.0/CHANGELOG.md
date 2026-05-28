# 11.0.0-dynamic-protocol-certified-modeling-stable

- Added dynamic protocol generation, linting, redteam, compilation, and dynamic protocol gate.
- Added capability atom templates and compiled protocol contracts.
- Added dynamic validator, negative test, mutation test, and validator adequacy v2 support.
- Added model fidelity, claim limit, dynamic certificate, output schema, heterogeneous verification, and OS diagnostic subsystems.
- Added final-gate-v3 integrating final-gate-v2 with dynamic protocol, fidelity, claim, certificate, output-schema, and diagnostic checks.
- Updated version metadata and command inventory.


## 10.0.0-constraint-certified-modeling-stable

- Added constraint ledger, coverage gate, dependency graph, certificate engine, validator adequacy checks, semantic red-team, model-risk register, independent verification protocol, Final Gate v2 and strict prompt profiles.
- Added regression coverage for missing inherited constraints and missing optimality certificates.

# 9.0.0-modeling-os-stable

- Added experiment/evidence ledger modules and schemas.
- Added Skills Runtime with manifest, loader, context budget, run report, and gate checks.
- Added evidence-driven routing candidate gate and deterministic promotion.
- Added validator builder/test runner/negative-test runner.
- Added 10 compact capability protocols.
- Added context budget and memory compaction commands.
- Added machine-readable quality protocol and red-team gate.
- Added MCP safe tool integration and provenance checks.
- Preserved v8.0.1 kernel gate compatibility and full test suite compatibility.

# Changelog

## 8.0.1-kernel-gate-hotfix

- Added `schemas/solver/solution_real.schema.json` for strict real-solver outputs.
- Added strict `solver-verify --all --strict` behavior with artifact, scope, data-source, violation and validator checks.
- Added `placeholder-scan`, `constraint-test`, `stale-output-check` and `final-gate --strict`.
- Added kernel-gate regression tests for intentionally invalid solver outputs and validators.

## 8.0.0 - agent-runtime-stable

- Added deterministic `thermal_optimization_minimal` synthetic case fixtures.
- Added `mmos.synthetic` support layer for no-network E2E regression.
- Added synthetic CLI commands: `synthetic-install`, `synthetic-search-inject`, `synthetic-solution-inject`, `agent-runtime-stable-run`, `synthetic-write-golden`.
- Added `method-match` CLI so injected search results can be consumed without re-running academic search planning.
- Added E2E and golden tests for the synthetic pipeline.
- Added `scripts/ci_local.sh` and expanded `scripts/run_tests.py` tiers for unit, integration, e2e, golden and all.
- Documented E2E and golden testing policy.


## 8.0.0-agent-runtime-stable

- Added candidate/official/reports artifact governance layout for problem understanding, academic search, method plan and paper artifacts.
- Added `mmos.core.artifacts` helpers for official reads/writes, candidate writes, report writes, artifact promotion, migration and Agent write permission evaluation.
- Added CLI commands: `artifact-init-layout`, `artifact-promote`, `artifact-migrate-layout`, `agent-write-check`.
- Updated case scaffold and templates to create governed artifact directories and `.agent/allowed_files/agent_write_policy.json`.
- Updated key workflows to prefer official artifacts while retaining legacy compatibility mirrors.
- Added artifact governance policy, context pack and tests.
- Removed `.claude/`, embedded OCR assets, `__pycache__/` and `*.pyc` from the distributable package.

## 7.3.0-schema-gated

- Added `schemas/` families for problem understanding, academic research, method plan, contracts, agents, gates, workflow and artifacts.
- Added `mmos/core/schema.py` and schema validation CLI commands.
- Added lightweight domain dataclasses for future state-machine work.
- Added schema fixtures and schema tests.

## 7.2.0-control-plane-refactor

- Added `AGENTS.md`, `context_packs/`, refactor inventories and version reports.
- Split monolithic CLI into the `mmos/cli/` package while preserving command compatibility.
- Standardized version metadata.

## 7.1.0-understanding-gated

- Introduced understanding-gated workflow, academic search plan gate and v7 compatibility artifacts.
- Removed legacy capability pack reliance from the formal workflow.
- Added version consistency, CLI contract, path safety and academic research bootstrap tests.
