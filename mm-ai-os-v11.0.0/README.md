# MM-AI OS 11.0.0-dynamic-protocol-certified-modeling-stable

Codename: `dynamic-protocol-certified-modeling-stable`

MM-AI OS is an agentic mathematical-modeling operating system for competition-grade modeling workflows. The v11 line focuses on **dynamic capability protocols**, **constraint coverage**, **model fidelity control**, **validator adequacy**, **certificates**, and **final gate governance**.

This repository is intended to be auditable and reproducible rather than a chat-style answer generator. A modeling case should leave durable artifacts under `cases/<case_id>/`, including problem ingestion, data audit, constraint ledger, dependency graph, compiled protocol, solver outputs, validators, certificates, evidence ledgers, risk reports, and final gate reports.

## Core workflow

```text
case-init
→ ingest-documents / data-audit
→ problem-parse-v3 / problem-graph-build / problem-understand
→ constraint-ledger-build / dependency-graph-build
→ problem-type-infer / capability-atom-match
→ protocol-synthesize / protocol-lint / protocol-redteam / protocol-compile
→ question-activate / contract-build / contract-check
→ validator-build / negative-test-build / mutation-test-build
→ model-fidelity-plan-build / solver-build / case-run-flow
→ solver-verify / model-fidelity-check / claim-limit-check
→ certificate-plan-synthesize / certificate-build / certificate-check-v2
→ heterogeneous-verify / sensitivity-analysis
→ evidence-pack-v2 / claim-check / output-schema-check
→ semantic-redteam / model-risk-check / capability-gap-matrix
→ dynamic-protocol-gate / final-gate-v3 / package-case
```

## Quick start

```bash
python -m compileall -q mmos scripts
python scripts/mmtool.py self-test --case selftest_agent_boot --budget fast
python scripts/mmtool.py case-init demo_case --force
python scripts/mmtool.py ingest-documents demo_case --unpack-archives
python scripts/mmtool.py data-audit demo_case --recursive --manifest
python scripts/mmtool.py problem-parse-v3 demo_case
python scripts/mmtool.py problem-type-infer demo_case
python scripts/mmtool.py capability-atom-match demo_case
python scripts/mmtool.py protocol-synthesize demo_case
python scripts/mmtool.py protocol-lint demo_case
python scripts/mmtool.py protocol-redteam demo_case
python scripts/mmtool.py protocol-compile demo_case
python scripts/mmtool.py dynamic-protocol-gate demo_case --strict
python scripts/mmtool.py final-gate-v3 demo_case --strict
```

## v11 compatibility notes

The CLI keeps compatibility aliases for the v11 prompt chain:

- `problem-parse-v3` delegates to the current v2 parser.
- `ingest-documents --unpack-archives` performs safe archive extraction before corpus construction.
- `--from compiled-protocol` and `--from-compiled-protocol` are both accepted where relevant.
- `contract-build --all --from compiled-protocol`, `experiment-record --all`, `output-build --accept-draft`, and `output-validate --all-required` are accepted for prompt-chain compatibility.
- `solver-build` delegates to the existing `solver-factory` scaffold generator.

Compatibility aliases do not make a weak solver mathematically certified. Final claim strength is still governed by validators, certificates, model fidelity, claim limits, and `final-gate-v3`.

## Repository layout

```text
mmos/                 Core OS modules
scripts/mmtool.py     CLI entrypoint
capabilities/         Capability atom templates
contracts/            OS-level contract metadata
schemas/              JSON schemas
templates/            Case templates and scaffold files
docs/                 Architecture, standards, and testing documentation
tests/                Regression and gate tests
cases/                Local case workspaces; generated outputs are ignored by git
```

## Testing

```bash
python scripts/check_version_consistency.py
python -m pytest tests/test_dynamic_protocol_os.py tests/test_prompt_chain_cli_compat.py -q
python -m pytest -q
```

## Open-source hygiene

Generated case artifacts, caches, local environments, and packaged outputs are ignored by default. Before publishing, run:

```bash
python -m compileall -q mmos scripts
python -m pytest -q
```

## License

Released under the MIT License. See [`LICENSE`](LICENSE).
