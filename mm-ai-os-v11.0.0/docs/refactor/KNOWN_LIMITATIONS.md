# Known Limitations

## 8.0.0 Agent Runtime Stable

- The Agent Runtime is deterministic and does not invoke real external LLMs.
- MCP support is a permission/audit boundary, not a full remote MCP client.
- Human approval is represented through approval-required flags; interactive approval UX is deferred.
- Budget accounting is explicit usage-based and not yet connected to live token metering.
