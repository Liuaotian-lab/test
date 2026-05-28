# 01 Problem Parse Repair Protocol

Goal: ensure the regex parser did not miss questions, implicit outputs, dependency order, or attachment-driven requirements.

Required artifacts:

- `workspace/problem_graph.raw.json`
- `workspace/problem_graph.agent_review.json`
- `workspace/problem_graph.final.json`

Rules:

- Do not accept fallback Q1 if the statement contains multiple tasks.
- Detect implicit output files and required result tables.
- Mark each question `required: true/false` explicitly.
- Record dependencies such as Q3 depending on Q2 parameters.
