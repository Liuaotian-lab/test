# Context Pack: Gates

## Purpose

Quality gates prevent weak or unverified artifacts from entering final outputs or submission packages.

## Key gates

- `understanding-gate`
- `search-plan-gate`
- `method-plan-check`
- `report-consistency-check`
- `solver-verify`
- `final-gate`
- `package-submit`

## Outputs

- `quality/*.json`
- `.agent/gate_reports/*.json`
- `final_outputs/final_gate_check.json`

## Rules

- Gates are not documentation; they are execution boundaries.
- Do not downgrade blocking errors to warnings without explicit approval.
- Final gate should recompute relevant checks rather than trusting stale reports.
