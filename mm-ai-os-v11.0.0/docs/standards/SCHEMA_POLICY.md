# Schema Policy — 7.4.0-candidate-official-split

## Purpose

`7.4.0-candidate-official-split` introduces a first-class schema gate for MM-AI OS. Critical JSON artifacts must have an explicit JSON Schema before they are treated as stable workflow contracts.

## Rule

Any artifact that is consumed by a downstream workflow, gate, Agent task, package step or paper-generation step must satisfy the following lifecycle:

```text
artifact definition
  ↓
JSON Schema
  ↓
valid and invalid fixtures
  ↓
schema validation test
  ↓
workflow or gate consumption
```

## Current scope

This release adds schema coverage for the following core families:

- `problem_understanding/*`
- `academic_research/*`
- `method_plan/*`
- `contracts/*`
- `agents/*`
- `gates/*`
- `workflow/*`
- `artifacts/*`

## CLI

Use:

```bash
python -m mmos.cli schema-list
python -m mmos.cli schema-validate --schema problem_understanding/final_problem_signature --file path/to/file.json
```

Schema names are normalized. These forms are equivalent:

```text
problem_understanding/final_problem_signature
schemas/problem_understanding/final_problem_signature.schema.json
problem_understanding/final_problem_signature.schema.json
```

## Boundary

This release validates structure. It does not yet implement the `7.4.0` candidate/official artifact promotion flow. AI-generated outputs are still governed by existing task cards and gates until `7.4.0-candidate-official-split`.
