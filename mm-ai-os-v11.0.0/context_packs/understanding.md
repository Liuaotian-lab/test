# Context Pack: Problem Understanding

## Purpose

Build evidence-backed problem understanding artifacts and enforce the understanding gate.

## Inputs

- `workspace/problem_corpus.md`
- `workspace/problem_graph.json`
- Optional Agent candidate file in `workspace/problem_understanding/agent_candidate_signature.json`

## Outputs

- `workspace/problem_understanding/evidence_index.json`
- `workspace/problem_understanding/candidate_signatures.json`
- `workspace/problem_understanding/official/final_problem_signature.json`
- `workspace/problem_understanding/reports/understanding_gate_report.json`
- Compatibility: `workspace/problem_signatures/case.signatures.json`

## Public CLI

- `problem-understand`
- `understanding-gate`
- `problem-signature-extract`

## Rules

- Formal claims require evidence ids.
- Heuristic fallback is only bootstrap; Agent review is still required for serious cases.
- Do not generate academic methods here.

## Tests

```bash
python -m pytest -q tests/test_problem_understanding_engine.py
```
