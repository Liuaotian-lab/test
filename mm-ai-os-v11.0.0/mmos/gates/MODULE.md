# Module: Gates

## Purpose

Quality and submission gates that decide whether artifacts can move forward.

## Inputs

- Case workspace artifacts.
- Output registry.
- Solver results.
- Paper and report artifacts.

## Outputs

- `quality/*.json`
- `.agent/gate_reports/*.json`
- `final_outputs/final_gate_check.json`

## Public CLI

- `solver-verify`
- `final-gate`
- `final-gate-check`
- `package-submit`

## Do Not

- Do not downgrade blocking failures without an explicit versioned policy change.
- Do not trust stale gate reports when recomputation is feasible.
