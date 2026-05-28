# Golden Test Policy

## Purpose

Golden tests protect stable structural outputs from accidental drift. They are used for deterministic synthetic artifacts only.

## Golden Files

```text
tests/fixtures/synthetic_cases/thermal_optimization_minimal/expected/
  problem_graph.golden.json
  search_plan.golden.json
  method_plan.golden.json
  package_manifest.golden.json
```

## Regeneration

Use:

```bash
python -m mmos.cli synthetic-e2e-run synthetic_thermal_minimal --force
python -m mmos.cli synthetic-write-golden synthetic_thermal_minimal --destination tests/fixtures/synthetic_cases/thermal_optimization_minimal/expected
```

Regeneration is allowed only when the intended behavior changes. Review the diff before committing.

## Stability Rules

Golden snapshots strip timestamps and other unstable fields. They should preserve structural content, key IDs, package paths and method-plan semantics.

## Test Command

```bash
python scripts/run_tests.py --tier golden
```

or directly:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/golden
```
