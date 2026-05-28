# Module: Contracts

## Purpose

Create and validate case/question contracts used to constrain Agent and solver execution.

## Inputs

- Case scaffold templates.
- `registry/questions_registry.json`.

## Outputs

- `contracts/global/*.json`
- `contracts/questions/<QID>/*.json`
- `engineering/questions/<QID>/`

## Public CLI

- `question-activate`
- `contract-build`
- `contract-check`

## Do Not

- Do not silently change contract semantics.
- Do not activate questions without a registry or explicit question id.
