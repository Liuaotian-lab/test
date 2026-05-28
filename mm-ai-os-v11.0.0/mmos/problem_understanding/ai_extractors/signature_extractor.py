from __future__ import annotations
from typing import Any
from pathlib import Path
import re
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_candidate_json, write_candidate_json
from mmos.kernel.events import now_iso

SCHEMA_VERSION = "7.4.0"

DOMAIN_RULES = [
    ("physical_process.thermal_process", ["炉温", "温度", "热", "传热", "焊接", "回流焊", "thermal", "temperature", "heat"]),
    ("physical_process.hydraulic_pressure_control", ["油管", "压力", "柱塞", "喷油", "液压", "pressure", "hydraulic", "valve"]),
    ("solar_optical.heliostat_field", ["定日镜", "太阳能", "光学效率", "heliostat", "solar", "tower", "ray tracing"]),
    ("graph_network.graph_theory", ["网络", "路径", "节点", "边", "最短路", "最大流", "图", "network", "graph", "path", "flow"]),
    ("traffic_flow", ["交通", "车流", "拥堵", "路网", "traffic", "vehicle", "congestion"]),
    ("statistical_decision", ["评价", "指标", "排序", "决策", "权重", "TOPSIS", "AHP", "entropy", "ranking", "evaluation"]),
    ("stochastic_simulation", ["随机", "仿真", "蒙特卡洛", "概率", "stochastic", "simulation", "Monte Carlo"]),
    ("operations_research.constrained_optimization", ["优化", "最优", "约束", "调度", "规划", "optimization", "constraint", "scheduling"]),
]

TASK_RULES = [
    ("mechanistic_modeling", ["建立模型", "机理", "微分方程", "方程", "守恒", "model", "equation", "mechanism"]),
    ("prediction", ["预测", "预报", "未来", "forecast", "predict", "prediction"]),
    ("parameter_estimation", ["拟合", "参数估计", "反演", "标定", "fit", "calibration", "inverse", "estimate"]),
    ("constrained_optimization", ["优化", "最优", "最大", "最小", "约束", "optimization", "optimal", "minimize", "maximize"]),
    ("simulation", ["仿真", "模拟", "simulation", "simulate", "Monte Carlo"]),
    ("evaluation", ["评价", "评估", "排序", "ranking", "evaluation", "score"]),
]

QUANTITY_RULES = [
    ("temperature", "T", "state_variable", ["温度", "炉温", "temperature"]),
    ("time", "t", "independent_variable", ["时间", "时刻", "秒", "分钟", "time"]),
    ("velocity", "v", "decision_or_state_variable", ["速度", "传送带", "velocity", "speed"]),
    ("position", "x", "state_or_index_variable", ["位置", "距离", "坐标", "position", "distance"]),
    ("pressure", "p", "state_variable", ["压力", "pressure"]),
    ("flow_rate", "q", "state_or_decision_variable", ["流量", "flow"]),
    ("power", "P", "state_or_output_variable", ["功率", "power"]),
    ("cost", "C", "objective_component", ["成本", "费用", "cost"]),
    ("demand", "d", "target_or_input_variable", ["需求", "销量", "客流", "demand"]),
    ("indicator", "I", "evaluation_indicator", ["指标", "评价指标", "indicator"]),
]

CONSTRAINT_RE = re.compile(r"[^。；;\n]*(?:不超过|不得超过|不少于|至少|至多|约束|限制|必须|不能|上限|下限|低于|高于|小于|大于)[^。；;\n]*")
DATA_RE = re.compile(r"(?:附件|数据|表\s*\d*|图\s*\d*|Excel|CSV|xlsx|xls|csv|曲线|图像|表格)", re.IGNORECASE)
OUTPUT_RE = re.compile(r"(?:求出|给出|确定|预测|评价|排序|最优|方案|模型|结果|参数)")


def build_candidate_signature(case_dir: Path, evidence_index: dict[str, Any], question_id: str | None = None, prefer_agent_file: bool = True) -> dict[str, Any]:
    """Build a candidate understanding signature.

    If an external Agent has provided workspace/problem_understanding/candidate/agent_candidate_signature.json,
    the file is included as the primary candidate. Otherwise a conservative heuristic candidate is used.
    """
    case_dir = Path(case_dir).resolve()
    candidates = []
    if prefer_agent_file:
        agent_candidate = read_candidate_json(case_dir, "workspace/problem_understanding/agent_candidate_signature.json", None)
        if agent_candidate:
            candidates.append({
                "candidate_id": "agent_supplied",
                "producer": "external_agent",
                "status": "provided",
                "signature": agent_candidate.get("signature", agent_candidate),
            })

    heuristic = _heuristic_candidate(evidence_index, question_id)
    candidates.append({
        "candidate_id": "heuristic_bootstrap",
        "producer": "deterministic_fallback",
        "status": "provided",
        "signature": heuristic,
    })

    out = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "status": "passed",
        "mode": "agent_constrained_with_deterministic_fallback",
        "candidates": candidates,
        "agent_contract": _agent_contract(),
    }
    write_candidate_json(case_dir, "workspace/problem_understanding/candidate_signatures.json", out)
    return out


def _heuristic_candidate(evidence_index: dict[str, Any], question_id: str | None) -> dict[str, Any]:
    blocks = evidence_index.get("evidence_blocks", [])
    if question_id:
        qids = [question_id]
    else:
        qids = sorted({b.get("question_id") for b in blocks if b.get("question_id") and b.get("question_id") != "GLOBAL"}) or ["Q0"]
    questions = {}
    for qid in qids:
        q_blocks = [b for b in blocks if b.get("question_id") in {qid, "GLOBAL"}]
        text = "\n".join(b.get("text", "") for b in q_blocks)
        questions[qid] = _extract_question(qid, text, q_blocks)
    return {
        "schema_version": SCHEMA_VERSION,
        "understanding_mode": "heuristic_bootstrap_agent_review_required",
        "questions": questions,
    }


def _extract_question(qid: str, text: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_ids = [b.get("evidence_id") for b in blocks if b.get("evidence_id")]
    # Domain
    domain_hits = []
    for domain, words in DOMAIN_RULES:
        hits = _hits(text, words)
        if hits:
            domain_hits.append((domain, hits))
    if domain_hits:
        primary, hits = max(domain_hits, key=lambda item: len(item[1]))
        confidence = min(0.88, 0.38 + 0.10 * len(hits))
    else:
        primary, hits, confidence = "unknown", [], 0.12

    # Tasks
    tasks = []
    for task, words in TASK_RULES:
        hits_task = _hits(text, words)
        if hits_task:
            tasks.append({
                "task": task,
                "claim_type": "inference",
                "reason": f"Matched task indicators: {', '.join(hits_task[:5])}",
                "confidence": min(0.86, 0.34 + 0.12 * len(hits_task)),
                "evidence_ids": evidence_ids[:3],
                "evidence_terms": hits_task[:8],
            })
    if not tasks:
        tasks.append({"task": "modeling", "claim_type": "inference", "reason": "No specific task markers found; fallback to general modeling.", "confidence": 0.20, "evidence_ids": evidence_ids[:2], "evidence_terms": []})

    # Variables
    variables = []
    quantities = []
    for name, symbol, role, words in QUANTITY_RULES:
        h = _hits(text, words)
        if h:
            quantities.append(name)
            variables.append({
                "name": name,
                "symbol": symbol,
                "role": _refine_role(name, role, tasks),
                "unit": "unknown",
                "claim_type": "inference",
                "evidence_ids": evidence_ids[:3],
                "evidence_terms": h[:6],
                "confidence": min(0.82, 0.38 + 0.10 * len(h)),
            })

    # Constraints
    constraints = []
    seen = set()
    for m in CONSTRAINT_RE.finditer(text):
        raw = m.group(0).strip()
        if raw and raw not in seen:
            seen.add(raw)
            constraints.append({
                "text": raw[:220],
                "direction": _constraint_direction(raw),
                "threshold": _first_number(raw),
                "claim_type": "fact_or_direct_requirement",
                "evidence_ids": evidence_ids[:3],
                "confidence": 0.72,
            })
        if len(constraints) >= 12:
            break

    # Data requirements
    data_requirements = []
    if DATA_RE.search(text):
        data_requirements.append({
            "requirement": "Use provided data, tables, figures, curves or attachments when available.",
            "claim_type": "inference",
            "evidence_ids": evidence_ids[:3],
            "confidence": 0.65,
        })

    required_outputs = _infer_outputs(tasks, text, evidence_ids)
    dependencies = []
    if qid != "Q1" and re.search(r"问题\s*[一1]|第\s*[一1]\s*问|Q\s*1|上一问|前一问|上述模型", text, re.IGNORECASE):
        dependencies.append({"depends_on": "Q1", "type": "model_or_result_dependency", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.58})

    return {
        "question_id": qid,
        "goal": {
            "claim": _infer_goal(text),
            "claim_type": "inference",
            "evidence_ids": evidence_ids[:3],
            "confidence": 0.62 if text else 0.1,
        },
        "domain_family": {"primary": primary, "confidence": confidence, "evidence_terms": hits[:8], "evidence_ids": evidence_ids[:3]},
        "task_archetypes": tasks,
        "variables": variables,
        "physical_quantities": quantities,
        "constraints": constraints,
        "data_requirements": data_requirements,
        "required_outputs": required_outputs,
        "dependencies": dependencies,
        "open_questions": _open_questions(primary, tasks, variables, constraints, data_requirements),
        "source_evidence_ids": evidence_ids[:8],
    }


def _hits(text: str, words: list[str]) -> list[str]:
    low = text.lower()
    return [w for w in words if w.lower() in low]


def _refine_role(name: str, role: str, tasks: list[dict[str, Any]]) -> str:
    task_names = {t.get("task") for t in tasks}
    if "constrained_optimization" in task_names and name in {"velocity", "cost", "flow_rate", "power"}:
        return "decision_or_objective_variable"
    if "prediction" in task_names and name in {"demand", "temperature", "traffic_flow"}:
        return "target_or_state_variable"
    return role


def _constraint_direction(text: str) -> str:
    if re.search(r"不超过|不得超过|至多|上限|低于|小于", text):
        return "upper_bound"
    if re.search(r"不少于|至少|下限|高于|大于", text):
        return "lower_bound"
    if re.search(r"必须|不能|约束|限制", text):
        return "requirement_or_prohibition"
    return "unknown"


def _first_number(text: str) -> str | None:
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return m.group(0) if m else None


def _infer_goal(text: str) -> str:
    sentences = re.split(r"[。；;\n]", text)
    for s in sentences:
        if OUTPUT_RE.search(s) and len(s.strip()) >= 6:
            return s.strip()[:240]
    return (sentences[0].strip() if sentences else "")[:240] or "Understand and model the problem requirements."


def _infer_outputs(tasks: list[dict[str, Any]], text: str, evidence_ids: list[str]) -> list[dict[str, Any]]:
    names = {t.get("task") for t in tasks}
    outputs = []
    if "prediction" in names:
        outputs.append({"type": "prediction_result", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.62})
    if "constrained_optimization" in names:
        outputs.append({"type": "optimal_solution_or_parameters", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.66})
    if "evaluation" in names:
        outputs.append({"type": "evaluation_ranking_or_scores", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.60})
    if "simulation" in names:
        outputs.append({"type": "simulation_results", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.60})
    outputs.append({"type": "model_and_solution_report", "claim_type": "inference", "evidence_ids": evidence_ids[:2], "confidence": 0.80})
    return outputs


def _open_questions(domain: str, tasks: list[dict[str, Any]], variables: list[dict[str, Any]], constraints: list[dict[str, Any]], data_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    if domain == "unknown":
        issues.append({"type": "domain_uncertain", "message": "Primary domain is unknown; Agent review required."})
    if not variables:
        issues.append({"type": "variables_uncertain", "message": "No variables were confidently extracted."})
    if any(t.get("task") == "constrained_optimization" for t in tasks) and not constraints:
        issues.append({"type": "optimization_constraints_uncertain", "message": "Optimization was detected but explicit constraints were not extracted."})
    if not data_requirements:
        issues.append({"type": "data_requirements_uncertain", "message": "No data or attachment requirement was extracted; verify whether attachments are needed."})
    return issues


def _agent_contract() -> dict[str, Any]:
    return {
        "required_behavior": [
            "Return strict JSON only.",
            "Cite evidence_ids for every goal, task, variable, constraint, data requirement and output claim.",
            "Separate fact, inference and recommendation using claim_type.",
            "Do not prescribe a final method unless it is clearly marked as recommendation and later backed by academic evidence.",
            "List open_questions when evidence is insufficient.",
        ],
        "expected_agent_file": "workspace/problem_understanding/candidate/agent_candidate_signature.json",
        "formal_gate": "understanding-gate",
    }
