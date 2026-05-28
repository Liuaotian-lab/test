# Context Pack: Synthetic E2E

## Purpose
Provide a deterministic, no-network, no-LLM regression case that exercises the main OS pipeline from raw problem materials to final submission package.

## Scope
This context pack covers the v7.5 synthetic thermal optimization case and its supporting CLI commands, fixtures, e2e tests and golden snapshots.

## Inputs
- `tests/fixtures/synthetic_cases/thermal_optimization_minimal/raw/problem_statement.md`
- `tests/fixtures/synthetic_cases/thermal_optimization_minimal/raw/observations.csv`

## Outputs
- `cases/<case>/workspace/problem_graph.json`
- `cases/<case>/workspace/problem_understanding/official/final_problem_signature.json`
- `cases/<case>/workspace/academic_search/official/search_results.json`
- `cases/<case>/workspace/method_plan/official/case.method_plan_summary.json`
- `cases/<case>/results/Q1/outputs/solution_real.json`
- `cases/<case>/final_outputs/final_gate_check.json`
- `cases/<case>/package/package_manifest.json`
- `cases/<case>/package/final_submission.zip`

## Public APIs
- `mmos.synthetic.thermal_case.install_synthetic_raw(case_dir)`
- `mmos.synthetic.thermal_case.inject_synthetic_search_results(case_dir)`
- `mmos.synthetic.thermal_case.inject_synthetic_solution(case_dir)`
- `mmos.synthetic.thermal_case.run_synthetic_e2e(case_dir, force=False)`
- `mmos.synthetic.thermal_case.write_golden_snapshot(case_dir, destination)`

## CLI Commands
- `synthetic-install <case>`
- `synthetic-search-inject <case>`
- `synthetic-solution-inject <case>`
- `synthetic-e2e-run <case> --force`
- `synthetic-write-golden <case> --destination <dir>`
- `method-match <case>`

## Data Contracts
The synthetic flow uses existing v7.3/v7.4 schemas and artifact governance. It does not introduce a new production case format.

## Allowed Changes
- Synthetic fixture text and CSV, if golden files are intentionally regenerated.
- `mmos/synthetic/thermal_case.py` for deterministic regression support.
- E2E and golden tests.

## Forbidden Changes
- Do not make this flow depend on real network access.
- Do not call an LLM.
- Do not require external MCP servers.
- Do not write synthetic fixture outputs into production case examples.

## Tests
- `python scripts/run_tests.py --tier e2e`
- `python scripts/run_tests.py --tier golden`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/e2e tests/golden`

## Common Failure Modes
- Golden mismatch after intentional pipeline changes: regenerate snapshots and review diff.
- Package file count drift: confirm whether artifact registry behavior changed intentionally.
- Search plan overwritten after fixture injection: use `method-match` instead of `method-recommend` when testing injected search results.
