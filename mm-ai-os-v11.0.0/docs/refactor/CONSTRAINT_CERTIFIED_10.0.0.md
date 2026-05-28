# MM-AI OS 10.0.0 Constraint-certified Release

This release upgrades MM-AI OS from artifact-complete modeling to constraint-certified modeling.

## New modules

- `mmos.constraints`: constraint ledger, ledger check, coverage gate.
- `mmos.dependencies`: cross-question dependency graph and dependency gate.
- `mmos.certificates`: optimization/boundary certificate checker.
- `mmos.validator_adequacy`: validator adequacy and adversarial mutation protocol.
- `mmos.semantic_redteam`: semantic red-team gate and model-risk register.
- `mmos.independent_verification`: high-risk claim verification protocol.
- `mmos.final_gate_v2`: artifact/validity/trust final gate.
- `mmos.agent_protocol`: strict prompt profiles, task cards, failure ledger and repair limiter.

## Regression fixed

The bench-dragon A Q3 failure mode is now represented as a regression test: a minimal-pitch claim without the inherited collision-free validator and bracketing certificate is blocked.

## Trust policy

- Missing constraint coverage blocks strict delivery.
- Missing dependency graph blocks inherited constraints.
- Minimum/maximum/optimal/boundary claims require certificates.
- Weak validators must detect negative and mutation cases.
- Semantic red-team blocking issues prevent Final Gate v2.
