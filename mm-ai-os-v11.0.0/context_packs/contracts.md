# Context Pack: Contracts

## Purpose

Scaffold and validate case-level and question-level contracts that constrain execution.

## Inputs

- `registry/questions_registry.json`
- `templates/contracts_question/`
- `templates/case/contracts/`

## Outputs

- `contracts/global/*.json`
- `contracts/questions/<QID>/*.json`
- `engineering/questions/<QID>/`

## Public CLI

- `question-activate`
- `contract-build`
- `contract-check`

## Rules

- Do not modify contract semantics casually.
- Question activation should be explicit or all-question scoped.
- Solver outputs must satisfy output and validation contracts.
