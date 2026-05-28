# Contributing

This project treats modeling outputs as governed artifacts. Contributions should preserve the distinction between candidate artifacts, official artifacts, validators, evidence, certificates, and final gate reports.

## Development checks

Run these before opening a pull request:

```bash
python -m compileall -q mmos scripts
python scripts/check_version_consistency.py
python -m pytest -q
```

## Pull request expectations

- Do not weaken path-safety or artifact-promotion rules.
- Do not let format validators substitute for mathematical or domain validators.
- Do not add commands that can write directly into `official/`, `final_outputs/`, or `package/` without gate-controlled promotion.
- Add regression tests for new CLI commands or compatibility aliases.
- Document any capability gap that affects final claims.
