# Cleanup Report

## 7.4.0

Removed clearly disposable or tool-local content:

```text
.claude/
assets/
__pycache__/
*.pyc
```

No uncertain project files were deleted.

## 7.5.0

Before packaging, generated runtime cases and Python cache files are removed. Synthetic fixtures under `tests/fixtures/synthetic_cases/` are retained because they are part of the deterministic regression harness.
