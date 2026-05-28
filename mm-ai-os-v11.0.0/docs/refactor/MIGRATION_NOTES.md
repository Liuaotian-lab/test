# Migration Notes

## 8.0.0 Agent Runtime Stable

Existing 7.5 cases remain compatible. New runtime metadata is added lazily:

- `.agent/allowed_files/agent_write_policy.json`
- `.agent/run_reports/`
- `.agent/audit/tool_calls.jsonl`
- `state/case_state.json`

No case data migration is required for ordinary usage.
