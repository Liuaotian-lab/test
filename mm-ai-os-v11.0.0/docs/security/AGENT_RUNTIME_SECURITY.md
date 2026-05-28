# Agent Runtime Security: 8.0.0

This release adds deterministic safety controls around agent-like work:

- path permission checks;
- candidate-only default write policy;
- budget checks;
- MCP permission checks;
- JSONL audit events;
- run reports.

The runtime intentionally avoids connecting to real external LLM or remote MCP servers. It provides the control plane required before those integrations are introduced.
