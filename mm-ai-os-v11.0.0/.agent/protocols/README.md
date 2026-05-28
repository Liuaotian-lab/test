# MM-AI OS Agent Protocols

These protocols define how a capable AI Agent should convert the OS scaffold into a real competition-grade solution. The Python runtime enforces file safety, contracts, gates, output integrity, and packaging. The Agent is responsible for semantic modeling, solver implementation, independent verification, and paper polish, but every such action must leave machine-checkable artifacts.

Recommended strict sequence:

```bash
python scripts/mmtool.py problem-parse-v2 <case>
python scripts/mmtool.py problem-parse-review <case>
python scripts/mmtool.py agent-task-generate <case> --all --phase all --force
# Agent edits contracts, solvers, verifiers, reports, figures and paper.
python scripts/mmtool.py verifier-run <case> --all
python scripts/mmtool.py verifier-compare <case> --all --strict
python scripts/mmtool.py paper-build <case> --force
python scripts/mmtool.py paper-quality-check <case> --strict
python scripts/mmtool.py agent-protocol-check <case> --strict
python scripts/mmtool.py final-gate-check <case>
```
