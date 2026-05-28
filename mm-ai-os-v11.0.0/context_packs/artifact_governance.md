# Context Pack: Artifact Governance

## Purpose

7.4.0 separates Agent-generated candidate artifacts from deterministic official artifacts.

## Governed Areas

- `workspace/problem_understanding/{candidate,official,reports}`
- `workspace/academic_search/{candidate,official,reports}`
- `workspace/method_plan/{candidate,official,reports}`
- `paper/{candidate,official,reports}`

## Core API

- `mmos.core.artifacts.ensure_candidate_official_layout(case_dir)`
- `mmos.core.artifacts.write_candidate_json(...)`
- `mmos.core.artifacts.write_official_json(...)`
- `mmos.core.artifacts.write_report_json(...)`
- `mmos.core.artifacts.read_official_json(...)`
- `mmos.core.artifacts.promote_artifact(...)`
- `mmos.core.artifacts.migrate_legacy_artifacts(...)`

## CLI

- `artifact-init-layout`
- `artifact-promote`
- `artifact-migrate-layout`
- `agent-write-check`

## Rule

Agent output is not authoritative. Agent output must be treated as candidate content until schema validation and promotion succeed.

## Forbidden

Do not allow Agent code to write directly to:

- `workspace/**/official/**`
- `final_outputs/**`
- `package/**`
- `paper/official/**`
- `contracts/**`
- `schemas/**`
