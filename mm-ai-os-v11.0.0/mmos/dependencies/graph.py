from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import status_from
from mmos.constraints.ledger import load_constraint_ledger


def dependency_graph_path(case_dir: Path) -> Path:
    return Path(case_dir) / "workspace" / "dependencies" / "official" / "question_dependency_graph.json"


def build_dependency_graph(case_dir: Path, *, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    out = dependency_graph_path(case_dir)
    if out.exists() and not force:
        return {"status": "passed", "action": "kept_existing", "path": str(out)}
    ledger = load_constraint_ledger(case_dir) or {"constraints": []}
    edges: list[dict[str, Any]] = []
    for c in ledger.get("constraints", []):
        if not isinstance(c, dict):
            continue
        qto = c.get("question_id")
        for dep in c.get("depends_on", []) or []:
            # Best-effort inference: Q2_C001 -> Q2
            qfrom = str(dep).split("_")[0] if str(dep).startswith("Q") else str(dep)
            edges.append({
                "from_question": qfrom,
                "to_question": qto,
                "dependency_type": "constraint_inheritance",
                "constraint_id": c.get("constraint_id"),
                "required_artifacts": c.get("required_artifacts", []),
                "required_hooks": c.get("required_solver_hooks", []),
                "required_validators": c.get("required_validators", []),
                "required_claim_limits": c.get("claim_limits", []),
                "blocking": True,
            })
    graph = {"case_id": case_dir.name, "schema_version": "10.0", "edges": edges}
    write_json(out, graph)
    return {"status": "passed", "path": str(out), "edge_count": len(edges)}


def load_dependency_graph(case_dir: Path) -> dict[str, Any] | None:
    p = dependency_graph_path(case_dir)
    if p.exists():
        return read_json(p, {"edges": []})
    return None


def dependency_check(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    graph = load_dependency_graph(case_dir)
    warnings: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    if graph is None:
        # If there are inherited constraints, graph is required; otherwise warn only.
        ledger = load_constraint_ledger(case_dir)
        inherited = [c for c in (ledger or {}).get("constraints", []) if isinstance(c, dict) and "inherited" in str(c.get("constraint_type"))]
        if inherited:
            failures.append({"code": "MISSING_DEPENDENCY_GRAPH", "message": "inherited constraints require question_dependency_graph.json"})
        else:
            warnings.append({"code": "NO_DEPENDENCY_GRAPH", "message": "no dependency graph present"})
        report = {"status": status_from(failures, warnings), "edges_checked": 0, "failures": failures, "warnings": warnings}
        write_json(case_dir / "workspace" / "dependencies" / "reports" / "dependency_check_report.json", report)
        return report
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            failures.append({"code": "INVALID_DEPENDENCY_EDGE", "index": idx}); continue
        if not edge.get("from_question") or not edge.get("to_question"):
            failures.append({"code": "MISSING_DEPENDENCY_ENDPOINT", "index": idx})
        if edge.get("blocking", True) and edge.get("dependency_type") in {"validator_reuse", "constraint_inheritance"}:
            if not edge.get("required_validators") and not edge.get("required_hooks"):
                failures.append({"code": "DEPENDENCY_WITHOUT_VALIDATOR_OR_HOOK", "edge": edge})
        for artifact in edge.get("required_artifacts", []) or []:
            p = Path(artifact)
            if not p.is_absolute():
                p = case_dir / p
            if not p.exists():
                failures.append({"code": "MISSING_DEPENDENCY_ARTIFACT", "artifact": artifact, "edge": edge})
    report = {"status": status_from(failures, warnings), "edges_checked": len(edges), "failures": failures, "warnings": warnings}
    write_json(case_dir / "workspace" / "dependencies" / "reports" / "dependency_check_report.json", report)
    return report
