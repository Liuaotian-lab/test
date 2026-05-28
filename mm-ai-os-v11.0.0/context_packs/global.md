# Context Pack: Global

## Purpose

Low-token control-plane summary for MM-AI OS `7.4.0-candidate-official-split`.

## System identity

Agentic workflow framework for mathematical modeling competitions. The system coordinates problem ingestion, problem understanding, academic search planning, method planning, contracts, execution, paper generation and submission gates.

## Preserved workflow

`case-init -> ingest-documents -> problem-parse-v2 -> problem-understand -> understanding-gate -> academic-search -> search-plan-gate -> method-plan-synthesize -> question-activate -> final-gate -> package-submit`

## Core rule

AI output is not official unless validated by deterministic code or a gate.

## Read before modifying

- `AGENTS.md`
- `docs/refactor/CURRENT_ARCHITECTURE.md`
- `docs/refactor/MODULE_INVENTORY.md`
- The module-specific context pack.

## Standard tests

```bash
python scripts/run_tests.py --tier smoke
python -m pytest -q
```

## Forbidden in ordinary tasks

- Reading the full repository without need.
- Changing case layout.
- Removing gates.
- Introducing dependencies without updating project metadata.

## 7.4 artifact governance

Read `context_packs/artifact_governance.md` before changing candidate/official behavior.
