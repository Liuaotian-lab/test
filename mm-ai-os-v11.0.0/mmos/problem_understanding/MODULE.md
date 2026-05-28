# Module: Problem Understanding

## Purpose

Build evidence-backed problem understanding artifacts and enforce the understanding gate.

## Inputs

- `workspace/problem_corpus.md`
- `workspace/problem_graph.json`
- Optional Agent candidate signature file.

## Outputs

- `workspace/problem_understanding/evidence_index.json`
- `workspace/problem_understanding/final_problem_signature.json`
- `quality/understanding_gate_report.json`
- Compatibility artifact: `workspace/problem_signatures/case.signatures.json`

## Public CLI

- `problem-understand`
- `understanding-gate`
- `problem-signature-extract`

## Do Not

- Do not invent claims without evidence.
- Do not perform academic search here.
- Do not generate final method plans here.
