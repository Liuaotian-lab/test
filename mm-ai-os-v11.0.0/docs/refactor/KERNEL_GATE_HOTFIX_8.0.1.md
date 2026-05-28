# 8.0.1 Kernel Gate Hotfix

## New CLI

```bash
python scripts/mmtool.py solver-verify <case_id> --all --strict
python scripts/mmtool.py solver-verify <case_id> --result results/Q1/outputs/solution_real.json --strict
python scripts/mmtool.py placeholder-scan <case_id> --all
python scripts/mmtool.py constraint-test <case_id> --all
python scripts/mmtool.py stale-output-check <case_id> --all
python scripts/mmtool.py final-gate <case_id> --strict
```

## Strict `solution_real.json` Minimum

Strict final delivery requires:

- `scope=real`
- `data_source != demo_data`
- `solver_status` not in `failed`, `timeout`, `iter_limit`
- `violation_count=0`
- `diagnostics.constraints_checked=true`
- non-empty `diagnostics.domain_validators_run`
- no `fallback_used=true` with `optimal=true`
- no heuristic/simulation/approximate/exploratory result claiming `optimal=true`
- all listed artifacts exist
- non-empty limitations

## Compatibility

Legacy `solver-verify` remains permissive unless `--strict` or `--strict-schema` is provided.  This preserves existing v8 workflows while adding the stronger final-delivery path.
