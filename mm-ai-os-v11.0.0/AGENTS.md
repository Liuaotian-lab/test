# AGENTS.md

## Project identity

This repository is **MM-AI OS `8.0.0-agent-runtime-stable`**, an Agentic Modeling OS for mathematical modeling competitions.

It is not a one-click solver. It is a workflow framework for evidence-backed problem understanding, academic search planning, method planning, contract activation, solver execution, quality gates, paper generation and submission packaging.

## Core operating rule

LLM-generated outputs are candidates unless a deterministic validator or gate promotes them into the official workflow.

## Required context strategy

1. Read `context_packs/global.md` first.
2. Read the relevant module context pack next.
3. Do not read the whole repository unless the task is explicitly an architecture audit.
4. Prefer inventories in `docs/refactor/` over ad-hoc full-tree exploration.

## Development rules

- Preserve v7.1-compatible case semantics unless the task explicitly says otherwise.
- Do not remove quality gates.
- Do not bypass evidence requirements.
- Do not introduce new dependencies without updating `pyproject.toml`, `requirements.txt` if needed and tests.
- Do not write generated content directly into `workspace/**/official/**`, `paper/official/**`, `final_outputs/**` or `package/**`. Use `candidate/` plus promotion.
- Treat `schemas/` as formal data contracts. Schema changes require matching fixtures and tests.
- Keep command behavior backward compatible with `scripts/mmtool.py`.

## Testing commands

```bash
python scripts/run_tests.py --tier smoke
python scripts/run_tests.py --tier schema
python -m pytest -q
python -m mmos.cli --help
python scripts/mmtool.py --help
```

## High-risk areas

- `workspace/problem_understanding/final_problem_signature.json`
- `workspace/academic_search/search_results.json`
- `workspace/method_plan/case.method_plan_summary.json`
- `contracts/questions/<QID>/`
- `final_outputs/`
- `package/`

## Version plan

- `7.2.0-control-plane-refactor`: control plane, context packs, CLI split.
- `7.3.0-schema-gated`: strong JSON schema coverage.
- `8.0.0-agent-runtime-stable`: AI candidate artifact isolation.
- `8.0.0-agent-runtime-stable`: synthetic end-to-end and golden tests.
- `8.0.0-agent-runtime-stable`: Agent runtime, MCP adapter, permissions and audit.
