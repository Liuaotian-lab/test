# Modeling OS 9.0.0 Stable

This release keeps the 8.x control plane and adds a small-core, dynamic-skill architecture:

1. Experiment ledger: `experiment-record`, `experiment-pack`.
2. Evidence ledger: `evidence-pack`, `claim-check`.
3. Skills Runtime: `skill-list`, `skill-show`, `skill-run`, `skill-check`.
4. Routing: `routing-check`, `routing-promote`.
5. Validators: `validator-build`, `validator-test`, `negative-test`.
6. Capability protocols: `capability-list`, `capability-show`.
7. Context budget: `context-build`, `context-check`, `context-compact`.
8. Quality protocol: `quality-review`, `red-team-gate`, `model-readiness-gate`.
9. MCP safety: `mcp-safe-check`.

All generated AI outputs remain constrained to candidate/tool-report paths until deterministic checks promote them.
