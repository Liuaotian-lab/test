from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.gates.final_gate import final_gate_check
from mmos.problem_intelligence.analyzer import problem_intelligence
from mmos.modeling_innovation.tournament import modeling_readiness_check
from mmos.solver_factory.factory import solver_benchmark
from mmos.agent_protocols.verifiers import compare_verifiers
from mmos.agent_protocols.paper import paper_quality_check
from mmos.judge_simulation.simulator import judge_simulate
# v7.0: capability_routing_check replaced by method plan check
from mmos.academic_research_engine.coverage_checker import check_coverage
from mmos.semantic_checks.temporal import temporal_semantics_check
from mmos.semantic_checks.attachment_semantics import attachment_semantic_audit
from mmos.semantic_checks.model_fidelity import model_fidelity_check
from mmos.semantic_checks.solver_variant import solver_variant_verify
from mmos.quality_oracle.common import registry_questions


def _ok(status: str | None, allow_warning: bool = False) -> bool:
    return status in {'passed','ok'} or (allow_warning and status == 'warning')


def _score_to_grade(score: float, caps: list[str]) -> str:
    if score >= 88:
        grade = 'S'
    elif score >= 80:
        grade = 'A'
    elif score >= 68:
        grade = 'B'
    elif score >= 55:
        grade = 'C'
    else:
        grade = 'D'
    if 'MAX_B_NO_VERIFIER' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'MAX_B_NO_ADVANCED_MODEL' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'MAX_C_PAPER_NOT_STRICT' in caps and grade in {'S','A','B'}:
        grade = 'C'
    if 'MAX_B_METHOD_PLAN_INCOMPLETE' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'MAX_D_TEMPORAL_SEMANTICS_FAILED' in caps:
        grade = 'D'
    if 'MAX_B_ATTACHMENT_SEMANTICS_WEAK' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'MAX_B_MODEL_FIDELITY_WEAK' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'MAX_B_NON_RUNNABLE_VARIANTS' in caps and grade in {'S','A'}:
        grade = 'B'
    if 'FAILED_FINAL_GATE' in caps:
        grade = 'D'
    return grade


def first_prize_gate_check(case_dir: Path, target_score: float = 82.0, strict_final: bool = False, write: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    failures=[]; warnings=[]; caps=[]; gate_results=[]
    qs = registry_questions(case_dir)
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    final_report = final_gate_check(case_dir, strict_warnings=strict_final, write=True)
    gate_results.append({'gate': 'final-gate-check', 'status': final_report.get('status'), 'report': final_report})
    if not _ok(final_report.get('status'), allow_warning=not strict_final):
        caps.append('FAILED_FINAL_GATE')
        failures.append({'code': 'FINAL_GATE_NOT_PASSED', 'status': final_report.get('status')})

    cr = check_coverage(case_dir, strict=True)
    gate_results.append({'gate': 'method-plan-check', 'status': cr.get('status'), 'report': cr})
    if not _ok(cr.get('status')):
        caps.append('MAX_B_METHOD_PLAN_INCOMPLETE')
        failures.append({'code': 'METHOD_PLAN_COVERAGE_INCOMPLETE', 'status': cr.get('status'), 'failures': cr.get('gaps') or cr.get('failures')})

    ts = temporal_semantics_check(case_dir, strict=True)
    gate_results.append({'gate': 'temporal-semantics-check', 'status': ts.get('status'), 'report': ts})
    if not _ok(ts.get('status')):
        caps.append('MAX_D_TEMPORAL_SEMANTICS_FAILED')
        failures.append({'code': 'TEMPORAL_SEMANTICS_NOT_PASSED', 'status': ts.get('status'), 'failures': ts.get('failures')})

    aa = attachment_semantic_audit(case_dir, strict=True)
    gate_results.append({'gate': 'attachment-semantic-audit', 'status': aa.get('status'), 'report': aa})
    if not _ok(aa.get('status'), allow_warning=True):
        caps.append('MAX_B_ATTACHMENT_SEMANTICS_WEAK')
        warnings.append({'code': 'ATTACHMENT_SEMANTICS_WEAK', 'status': aa.get('status'), 'failures': aa.get('failures')})

    mf = model_fidelity_check(case_dir, strict=True)
    gate_results.append({'gate': 'model-fidelity-check', 'status': mf.get('status'), 'report': mf})
    if not _ok(mf.get('status'), allow_warning=True):
        caps.append('MAX_B_MODEL_FIDELITY_WEAK')
        warnings.append({'code': 'MODEL_FIDELITY_WEAK', 'status': mf.get('status'), 'failures': mf.get('failures')})

    sv = solver_variant_verify(case_dir, strict=False)
    gate_results.append({'gate': 'solver-variant-verify', 'status': sv.get('status'), 'report': sv})
    if not _ok(sv.get('status'), allow_warning=True):
        caps.append('MAX_B_NON_RUNNABLE_VARIANTS')
        warnings.append({'code': 'SOLVER_VARIANTS_NOT_FULLY_RUNNABLE', 'status': sv.get('status')})

    pi = read_json(case_dir / 'quality' / 'problem_intelligence_report.json', {}) or problem_intelligence(case_dir)
    gate_results.append({'gate': 'problem-intelligence', 'status': pi.get('status'), 'report': pi})
    if not _ok(pi.get('status'), allow_warning=True):
        warnings.append({'code': 'PROBLEM_INTELLIGENCE_NOT_STRONG', 'status': pi.get('status')})

    mr = modeling_readiness_check(case_dir, strict=False)
    gate_results.append({'gate': 'modeling-readiness-check', 'status': mr.get('status'), 'report': mr})
    if not _ok(mr.get('status'), allow_warning=True):
        failures.append({'code': 'MODELING_READINESS_NOT_PASSED', 'status': mr.get('status')})
    if any(f.get('code') == 'MISSING_ADVANCED_MODEL' for f in mr.get('failures', [])):
        caps.append('MAX_B_NO_ADVANCED_MODEL')

    sb = solver_benchmark(case_dir, strict=False, min_variants=2)
    gate_results.append({'gate': 'solver-benchmark', 'status': sb.get('status'), 'report': sb})
    if not _ok(sb.get('status'), allow_warning=True):
        warnings.append({'code': 'SOLVER_BENCHMARK_WEAK', 'status': sb.get('status')})
    if any(w.get('code') == 'INSUFFICIENT_SOLVER_VARIANTS' for w in sb.get('warnings', [])):
        warnings.append({'code': 'FIRST_PRIZE_PREFERS_MULTIPLE_SOLVER_VARIANTS'})

    vc = compare_verifiers(case_dir, strict=False)
    gate_results.append({'gate': 'verifier-compare', 'status': vc.get('status'), 'report': vc})
    if not _ok(vc.get('status'), allow_warning=True):
        caps.append('MAX_B_NO_VERIFIER')
        warnings.append({'code': 'VERIFIER_COMPARE_NOT_STRONG', 'status': vc.get('status')})

    pq = paper_quality_check(case_dir, strict=True)
    gate_results.append({'gate': 'paper-quality-check', 'status': pq.get('status'), 'report': pq})
    if not _ok(pq.get('status')):
        caps.append('MAX_C_PAPER_NOT_STRICT')
        warnings.append({'code': 'PAPER_QUALITY_NOT_STRICT_PASSED', 'status': pq.get('status')})

    js = judge_simulate(case_dir, rounds=3)
    gate_results.append({'gate': 'judge-simulate', 'status': js.get('status'), 'report': js})
    score = float(js.get('score') or 0.0)
    grade = _score_to_grade(score, caps)
    if score < target_score:
        warnings.append({'code': 'JUDGE_SIMULATION_SCORE_BELOW_TARGET', 'score': score, 'target_score': target_score})
    if grade in {'D'}:
        failures.append({'code': 'FIRST_PRIZE_READINESS_TOO_LOW', 'grade': grade, 'score': score})
    status = 'failed' if failures else ('passed' if grade in {'S','A'} and score >= target_score else 'warning')
    report = {
        'gate': 'first-prize-gate-check',
        'status': status,
        'target_score': target_score,
        'first_prize_readiness': {
            'grade': grade,
            'score': score,
            'confidence': 'medium_high' if grade in {'S','A'} and not caps else 'medium',
            'caps_applied': caps,
            'weak_dimensions': js.get('weak_dimensions', []),
            'recommended_next_actions': js.get('recommended_improvements', []),
        },
        'failures': failures,
        'warnings': warnings,
        'gate_results': gate_results,
        'generated_at': now_iso(),
    }
    if write:
        write_json(case_dir / 'quality' / 'first_prize_gate_report.json', report)
        write_json(case_dir / 'final_outputs' / 'first_prize_gate_report.json', report)
    return report
