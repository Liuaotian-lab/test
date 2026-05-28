# E2E Testing

## Purpose

v7.5 introduces a deterministic synthetic end-to-end case to protect the main workflow from regression. It does not require network access, external LLM calls, MCP servers or production data.

## Synthetic Case

Fixture root:

```text
tests/fixtures/synthetic_cases/thermal_optimization_minimal/
```

The fixture models a small thermal optimization problem with one primary question. It provides raw problem materials and deterministic injected artifacts for academic search results and solver output.

## Primary Command

```bash
python -m mmos.cli synthetic-e2e-run synthetic_thermal_minimal --force
```

This runs the pipeline through:

```text
synthetic install -> ingest -> parse -> understand -> academic search plan -> search gate -> inject search results -> method match -> method plan -> coverage/citation checks -> method plan synthesis -> inject solution -> output build -> final gate -> package submit
```

## Test Command

```bash
python scripts/run_tests.py --tier e2e
```

or directly:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/e2e
```

## Non-Goals

The synthetic E2E case is not a contest benchmark and does not measure mathematical modeling quality. It only proves that the OS control flow, artifact governance and final packaging path remain executable.
