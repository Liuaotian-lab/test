# Risk Register

## 8.0.1-kernel-gate-hotfix

| Risk | Status | Mitigation |
|---|---|---|
| Strict schema may reject legacy `solution_real.json` files. | Accepted | Strict behavior is opt-in via `--strict` / `final-gate --strict`; legacy `solver-verify` remains compatible. |
| Generic validator execution cannot infer every project-specific validator signature. | Open | The first version supports `validate`, `validate_solution`, `validate_output`, and `run_validation`; future validator-builder work should standardize this interface. |
| Placeholder scan can produce false positives in operating-system source files. | Mitigated | Case engineering placeholders are blocking; OS-level scan is warning-scoped when `--all` is used. |
| Freshness checks depend on file modification time when no explicit hash registry exists. | Accepted | Hash verification is performed when `output_hashes` are present; future experiment-ledger work should make hashes mandatory. |
