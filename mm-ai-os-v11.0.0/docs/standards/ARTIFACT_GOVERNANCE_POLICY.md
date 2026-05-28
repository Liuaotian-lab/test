# Artifact Governance Policy — 7.4.0-candidate-official-split

## Purpose

Version 7.4.0 introduces a governed artifact layout for AI-assisted workflows. The policy separates Agent-produced drafts from system-confirmed artifacts.

## Layout

Governed workflow areas use three directories:

```text
candidate/   # Agent, external tool, or human draft outputs
official/    # System-approved artifacts consumed by downstream workflow steps
reports/     # Gate reports, validation reports, promotion reports, and audits
```

Initial governed areas:

```text
workspace/problem_understanding/{candidate,official,reports}
workspace/academic_search/{candidate,official,reports}
workspace/method_plan/{candidate,official,reports}
paper/{candidate,official,reports}
```

## Rule

Agent-generated content must enter `candidate/` first. Downstream formal workflow steps should prefer `official/` artifacts. Legacy flat paths are retained as compatibility mirrors only.

## Promotion

Promotion from `candidate/` to `official/` must pass through deterministic code:

```bash
python -m mmos.cli artifact-promote <case> \
  --source workspace/problem_understanding/candidate/final_problem_signature.json \
  --destination workspace/problem_understanding/official/final_problem_signature.json \
  --schema problem_understanding/final_problem_signature \
  --mirror-legacy workspace/problem_understanding/final_problem_signature.json
```

The promotion command writes an audit report under:

```text
workspace/artifact_promotions/reports/
```

## Agent write boundary

The default Agent write policy is:

- allow writes to `workspace/**/candidate/**`, `paper/candidate/**`, `.agent/run_reports/**`, `.agent/task_cards/**`;
- deny writes to `workspace/**/official/**`, `final_outputs/**`, `package/**`, `paper/official/**`, `contracts/**`, `schemas/**`, version files, and secrets.

Use:

```bash
python -m mmos.cli agent-write-check <case> --path workspace/problem_understanding/official/x.json
```

## Compatibility

Legacy paths are still written for 7.x compatibility. New code should prefer `mmos.core.artifacts.read_official_json()` and `write_official_json()` rather than direct flat-path reads and writes.
