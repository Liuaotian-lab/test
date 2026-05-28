# Context Pack: Agent Runtime

## Purpose
`8.0.0-agent-runtime-stable` introduces a deterministic Agent Runtime control layer. It does not call external LLMs; it records, checks and constrains agent-like work.

## Inputs
- `.agent/allowed_files/agent_write_policy.json`
- `context_packs/*.md`
- candidate artifact paths
- workflow state files

## Outputs
- `.agent/run_reports/run_*.json`
- `.agent/audit/tool_calls.jsonl`
- `state/case_state.json`

## Public APIs
- `mmos.agents.policy.evaluate_path_permission`
- `mmos.agents.runtime.create_agent_run_report`
- `mmos.agents.budget.evaluate_budget`
- `mmos.adapters.mcp.permissions.evaluate_mcp_call`
- `mmos.workflows.state_machine.transition_case_state`

## CLI
- `workflow-state`
- `workflow-transition`
- `agent-policy-init`
- `agent-runtime-report`
- `agent-budget-check`
- `mcp-permission-check`

## Rules
- Agent outputs remain candidates unless promoted by deterministic governance.
- Official artifacts, package outputs, contracts, schemas and secrets are denied by default.
- MCP write and dangerous tools are denied unless explicitly approved by future human-approval logic.
