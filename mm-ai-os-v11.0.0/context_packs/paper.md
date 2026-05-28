# Context Pack: Paper

## Purpose

Generate, check and compile contest-paper artifacts.

## Inputs

- Problem understanding artifacts.
- Method plan artifacts.
- Question results and output registry.
- Evidence and citation artifacts.

## Outputs

- `paper/`
- `reports/`
- `final_outputs/`
- optional PDF build artifacts.

## Public CLI

- `paper-build`
- `paper-quality-check`
- `latex-paper-build`
- `latex-paper-compile`
- `paper-env-doctor`

## Rules

- Paper generation does not prove mathematical correctness.
- Final submission still requires quality gates.
- Do not treat generated LaTeX as final without review.
