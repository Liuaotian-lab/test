from __future__ import annotations

from dataclasses import dataclass, asdict
from fnmatch import fnmatch
from pathlib import Path
from shutil import copy2
from typing import Any
import json

from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.schema import validate_json_file

SCHEMA_VERSION = "7.5.0"
LAYOUT_DIRS = {
    "problem_understanding": ("workspace/problem_understanding/candidate", "workspace/problem_understanding/official", "workspace/problem_understanding/reports"),
    "academic_search": ("workspace/academic_search/candidate", "workspace/academic_search/official", "workspace/academic_search/reports"),
    "method_plan": ("workspace/method_plan/candidate", "workspace/method_plan/official", "workspace/method_plan/reports"),
    "paper": ("paper/candidate", "paper/official", "paper/reports"),
}

LEGACY_OFFICIAL_MAP: dict[str, str] = {
    "workspace/problem_understanding/evidence_index.json": "workspace/problem_understanding/official/evidence_index.json",
    "workspace/problem_understanding/final_problem_signature.json": "workspace/problem_understanding/official/final_problem_signature.json",
    "workspace/problem_signatures/case.signatures.json": "workspace/problem_signatures/official/case.signatures.json",
    "workspace/academic_search/search_results.json": "workspace/academic_search/official/search_results.json",
    "workspace/academic_search/method_matches.json": "workspace/academic_search/official/method_matches.json",
    "workspace/academic_search/citation_list.json": "workspace/academic_search/official/citation_list.json",
    "workspace/method_plan/case.method_plan_summary.json": "workspace/method_plan/official/case.method_plan_summary.json",
    "workspace/method_plan/case.approval_summary.json": "workspace/method_plan/official/case.approval_summary.json",
}

LEGACY_REPORT_MAP: dict[str, str] = {
    "workspace/problem_understanding/signature_review.json": "workspace/problem_understanding/reports/signature_review.json",
    "quality/understanding_gate_report.json": "workspace/problem_understanding/reports/understanding_gate_report.json",
    "quality/search_plan_gate_report.json": "workspace/academic_search/reports/search_plan_gate_report.json",
    "quality/coverage_gap_analysis.json": "workspace/method_plan/reports/coverage_gap_analysis.json",
    "quality/citation_validation.json": "workspace/academic_search/reports/citation_validation.json",
}

LEGACY_CANDIDATE_MAP: dict[str, str] = {
    "workspace/problem_understanding/agent_candidate_signature.json": "workspace/problem_understanding/candidate/agent_candidate_signature.json",
    "workspace/problem_understanding/candidate_signatures.json": "workspace/problem_understanding/candidate/candidate_signatures.json",
}


def _rel(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("/")


def official_rel(legacy_rel: str | Path) -> str:
    rel = _rel(legacy_rel)
    if rel in LEGACY_OFFICIAL_MAP:
        return LEGACY_OFFICIAL_MAP[rel]
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "workspace" and parts[1] in {"problem_understanding", "academic_search", "method_plan"}:
        return str(Path("workspace") / parts[1] / "official" / Path(*parts[2:])).replace("\\", "/")
    if len(parts) >= 2 and parts[0] == "paper":
        return str(Path("paper") / "official" / Path(*parts[1:])).replace("\\", "/")
    return rel


def candidate_rel(legacy_rel: str | Path) -> str:
    rel = _rel(legacy_rel)
    if rel in LEGACY_CANDIDATE_MAP:
        return LEGACY_CANDIDATE_MAP[rel]
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "workspace" and parts[1] in {"problem_understanding", "academic_search", "method_plan"}:
        return str(Path("workspace") / parts[1] / "candidate" / Path(*parts[2:])).replace("\\", "/")
    if len(parts) >= 2 and parts[0] == "paper":
        return str(Path("paper") / "candidate" / Path(*parts[1:])).replace("\\", "/")
    return rel


def report_rel(legacy_rel: str | Path) -> str:
    rel = _rel(legacy_rel)
    if rel in LEGACY_REPORT_MAP:
        return LEGACY_REPORT_MAP[rel]
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "workspace" and parts[1] in {"problem_understanding", "academic_search", "method_plan"}:
        return str(Path("workspace") / parts[1] / "reports" / Path(*parts[2:])).replace("\\", "/")
    return rel


def official_path(case_dir: Path, legacy_rel: str | Path) -> Path:
    return Path(case_dir).resolve() / official_rel(legacy_rel)


def candidate_path(case_dir: Path, legacy_rel: str | Path) -> Path:
    return Path(case_dir).resolve() / candidate_rel(legacy_rel)


def report_path(case_dir: Path, legacy_rel: str | Path) -> Path:
    return Path(case_dir).resolve() / report_rel(legacy_rel)


def first_existing(case_dir: Path, *relative_paths: str | Path) -> Path | None:
    base = Path(case_dir).resolve()
    for rel in relative_paths:
        p = base / _rel(rel)
        if p.exists():
            return p
    return None


def read_official_json(case_dir: Path, legacy_rel: str | Path, default: Any = None) -> Any:
    rel = _rel(legacy_rel)
    official = official_rel(rel)
    p = first_existing(case_dir, official, rel)
    if p is None:
        return default
    return read_json(p, default)


def read_candidate_json(case_dir: Path, legacy_rel: str | Path, default: Any = None) -> Any:
    rel = _rel(legacy_rel)
    candidate = candidate_rel(rel)
    p = first_existing(case_dir, candidate, rel)
    if p is None:
        return default
    return read_json(p, default)


def write_official_json(case_dir: Path, legacy_rel: str | Path, data: Any, *, mirror_legacy: bool = True) -> Path:
    base = Path(case_dir).resolve()
    rel = _rel(legacy_rel)
    out = base / official_rel(rel)
    write_json(out, data)
    if mirror_legacy and official_rel(rel) != rel:
        write_json(base / rel, data)
    return out


def write_candidate_json(case_dir: Path, legacy_rel: str | Path, data: Any, *, mirror_legacy: bool = True) -> Path:
    base = Path(case_dir).resolve()
    rel = _rel(legacy_rel)
    out = base / candidate_rel(rel)
    write_json(out, data)
    if mirror_legacy and candidate_rel(rel) != rel:
        write_json(base / rel, data)
    return out


def write_report_json(case_dir: Path, legacy_rel: str | Path, data: Any, *, mirror_legacy: bool = True) -> Path:
    base = Path(case_dir).resolve()
    rel = _rel(legacy_rel)
    out = base / report_rel(rel)
    write_json(out, data)
    if mirror_legacy and report_rel(rel) != rel:
        write_json(base / rel, data)
    return out


def ensure_candidate_official_layout(case_dir: Path) -> dict[str, Any]:
    base = Path(case_dir).resolve()
    created: list[str] = []
    for dirs in LAYOUT_DIRS.values():
        for rel in dirs:
            p = base / rel
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                created.append(rel)
            keep = p / ".gitkeep"
            if not keep.exists():
                keep.write_text("", encoding="utf-8")
    manifest_path = base / ".agent" / "allowed_files" / "agent_write_policy.json"
    if not manifest_path.exists():
        write_json(manifest_path, default_allowed_files_manifest(base.name))
        created.append(".agent/allowed_files/agent_write_policy.json")
    return {"schema_version": SCHEMA_VERSION, "status": "passed", "case_id": base.name, "created": created}


def default_allowed_files_manifest(case_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "default_policy": "deny",
        "allow_read": [
            "data/**",
            "workspace/**/official/**",
            "workspace/**/reports/**",
            "registry/**",
            "contracts/**",
            "engineering/**",
            "results/**",
            "reports/**",
            "paper/official/**",
            "paper/reports/**",
            "context_packs/**",
        ],
        "allow_write": [
            "workspace/**/candidate/**",
            "paper/candidate/**",
            ".agent/run_reports/**",
            ".agent/task_cards/**",
        ],
        "deny_read": [".env", "*.key", "secrets/**"],
        "deny_write": [
            "workspace/**/official/**",
            "final_outputs/**",
            "package/**",
            "paper/official/**",
            "contracts/**",
            "schemas/**",
            "os_manifest.json",
            "VERSION.txt",
            ".env",
            "*.key",
            "secrets/**",
        ],
    }


def is_path_allowed(path: str | Path, patterns: list[str]) -> bool:
    rel = _rel(path)
    return any(fnmatch(rel, pattern) for pattern in patterns)


def evaluate_write_permission(relative_path: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rel = _rel(relative_path)
    denied = is_path_allowed(rel, manifest.get("deny_write", []))
    allowed = is_path_allowed(rel, manifest.get("allow_write", []))
    decision = "denied" if denied else ("allowed" if allowed else manifest.get("default_policy", "deny"))
    if decision == "deny":
        decision = "denied"
    return {
        "schema_version": SCHEMA_VERSION,
        "path": rel,
        "decision": decision,
        "matched_allow": allowed,
        "matched_deny": denied,
    }


@dataclass(frozen=True)
class PromotionResult:
    status: str
    case_id: str
    source: str
    destination: str
    schema: str | None
    promoted_at: str
    validation: dict[str, Any] | None
    report: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def promote_artifact(
    case_dir: Path,
    source_rel: str | Path,
    destination_rel: str | Path,
    *,
    schema: str | None = None,
    mirror_legacy: str | Path | None = None,
) -> PromotionResult:
    base = Path(case_dir).resolve()
    src = (base / _rel(source_rel)).resolve()
    dst = (base / _rel(destination_rel)).resolve()
    try:
        src.relative_to(base)
        dst.relative_to(base)
    except ValueError as exc:
        raise ValueError("promotion paths must stay inside the case directory") from exc
    if not src.exists():
        raise FileNotFoundError(f"candidate artifact not found: {_rel(source_rel)}")
    validation_payload = None
    if schema:
        result = validate_json_file(src, schema, root=_repo_root_from_case(base))
        validation_payload = result.to_dict()
        if result.status != "passed":
            report_rel_path = f"workspace/artifact_promotions/reports/{src.stem}_promotion_failed.json"
            report = {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "case_id": base.name,
                "source": _rel(source_rel),
                "destination": _rel(destination_rel),
                "schema": schema,
                "validation": validation_payload,
                "promoted_at": now_iso(),
            }
            write_json(base / report_rel_path, report)
            return PromotionResult("failed", base.name, _rel(source_rel), _rel(destination_rel), schema, report["promoted_at"], validation_payload, report_rel_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    copy2(src, dst)
    if mirror_legacy:
        legacy = base / _rel(mirror_legacy)
        legacy.parent.mkdir(parents=True, exist_ok=True)
        copy2(src, legacy)
    report_rel_path = f"workspace/artifact_promotions/reports/{src.stem}_promotion.json"
    promoted_at = now_iso()
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "case_id": base.name,
        "source": _rel(source_rel),
        "destination": _rel(destination_rel),
        "schema": schema,
        "validation": validation_payload,
        "promoted_at": promoted_at,
    }
    write_json(base / report_rel_path, report)
    return PromotionResult("passed", base.name, _rel(source_rel), _rel(destination_rel), schema, promoted_at, validation_payload, report_rel_path)


def migrate_legacy_artifacts(case_dir: Path, *, overwrite: bool = False) -> dict[str, Any]:
    base = Path(case_dir).resolve()
    ensure_candidate_official_layout(base)
    migrated: list[dict[str, str]] = []
    for legacy, official in {**LEGACY_OFFICIAL_MAP, **LEGACY_REPORT_MAP, **LEGACY_CANDIDATE_MAP}.items():
        src = base / legacy
        dst = base / official
        if src.exists() and (overwrite or not dst.exists()):
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy2(src, dst)
            migrated.append({"from": legacy, "to": official})
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "case_id": base.name,
        "layout": "candidate-official-v1",
        "migrated_count": len(migrated),
        "migrated": migrated,
        "timestamp": now_iso(),
    }
    write_json(base / "workspace" / "artifact_promotions" / "reports" / "legacy_migration_report.json", report)
    return report


def _repo_root_from_case(case_dir: Path) -> Path:
    p = Path(case_dir).resolve()
    for parent in [p, *p.parents]:
        if (parent / "schemas").exists() and (parent / "mmos").exists():
            return parent
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "schemas").exists() and (parent / "mmos").exists():
            return parent
    return p
