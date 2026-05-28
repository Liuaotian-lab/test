# Baseline 10.0.0 Constraint-certified Modeling Stable

Base: 9.0.0-modeling-os-stable.

Primary objective: close the core trust gap exposed by the bench-dragon A regression: a case can pass artifact/schema/evidence gates while still omitting inherited mathematical constraints.

Added trust chain:

```text
problem evidence -> constraint ledger -> dependency graph -> solver hook -> validator -> negative test -> certificate -> semantic redteam -> final-gate-v2
```

Baseline checks run:

```bash
python -m compileall -q mmos scripts
python scripts/check_version_consistency.py
python scripts/run_tests.py --tier smoke
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/mmtool.py self-test --case selftest_agent_boot --budget fast
```
