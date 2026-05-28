# Current Architecture — 7.4.0-candidate-official-split

## Project identity

MM-AI OS is an Agentic Modeling OS for mathematical modeling competitions. Version `7.4.0` preserves the v7.1 understanding-gated workflow while adding a control plane for maintainability, lower context cost and safer Agent collaboration.

## Preserved formal workflow

```text
case-init
  -> ingest-documents
  -> problem-parse-v2
  -> problem-understand
  -> understanding-gate
  -> academic-search
  -> search-plan-gate
  -> external search result population
  -> method-recommend / method-plan-synthesize
  -> coverage-gap-analysis / citation-validate
  -> question-activate
  -> question-run-flow / case-run-flow
  -> paper-build / latex-paper-build
  -> final-gate
  -> package-submit
```

## 7.2 control-plane changes

- CLI moved from a single `mmos/cli.py` module to a package under `mmos/cli/`.
- `scripts/mmtool.py` remains backward compatible and still imports `mmos.cli.main`.
- `AGENTS.md` is now the default AI-agent entrypoint.
- `context_packs/` provides low-token module summaries for Agent tasks.
- `docs/refactor/*_INVENTORY.md` records modules, commands, artifacts and known risks.
- Version metadata is split into `VERSION.txt` and `VERSION_CODENAME`.

## Non-goals in 7.2

- No case layout migration.
- No schema overhaul.
- No candidate/official artifact split.
- No MCP runtime.
- No new modeling algorithm layer.

## Next version boundary

Version `7.4.0-candidate-official-split` should add strong schema coverage for problem understanding, academic research, method plan, contracts, gates and agent run reports.

## v7.5 Synthetic Regression Layer

v7.5 adds a deterministic synthetic regression layer under `mmos/synthetic/`. This layer is intentionally not a production modeling subsystem. It exists to exercise the full OS control flow without external network access, LLM calls, MCP servers, or real contest data.

The synthetic case uses the same case scaffold, artifact governance, method planning, final gate and package submission mechanisms as normal cases.
