# Test Report

## 10.0.0-constraint-certified-modeling-stable

Executed checks:

```bash
python -m compileall -q mmos scripts
python scripts/check_version_consistency.py
python scripts/run_tests.py --tier smoke
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/constraints tests/dependencies tests/certificates tests/validator_adequacy tests/semantic_redteam tests/final_gate_v2 tests/regression tests/agent_protocol
python scripts/mmtool.py self-test --case selftest_agent_boot --budget fast
```

Observed results:

```text
version consistency: passed
schema-list: passed, 79 schemas
full pytest: passed
new v10 module tests: 12 passed
self-test: passed
smoke: passed
```

Key negative tests:

- Missing inherited collision-free validator is blocked.
- Minimal-pitch claim without certificate is blocked.
- Dependency edge without validator/hook is blocked.
- Weak validator report without negative detection is blocked.
- Final Gate v2 blocks missing constraint coverage.
