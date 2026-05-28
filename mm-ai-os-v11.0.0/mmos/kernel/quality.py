QUALITY_LEVELS = [
    'global_optimal',
    'certified_optimal',
    'exhaustive_best',
    'local_optimal',
    'heuristic_feasible',
    'evaluated_best',
    'simulation_estimate',
    'approximate',
    'exploratory',
    'failed',
]

OPTIMALITY_SUPPORT_REQUIRED = {
    'global_optimal': ['global_optimality_certificate'],
    'certified_optimal': ['certificate_or_bound'],
    'exhaustive_best': ['enumerated_all_candidates'],
}


def validate_quality_claim(result: dict) -> list[dict]:
    failures = []
    q = result.get('quality_level') or result.get('optimality_label')
    diag = result.get('diagnostics', {}) or {}
    if q not in QUALITY_LEVELS:
        failures.append({'code': 'INVALID_QUALITY_LEVEL', 'message': f'unknown quality_level={q!r}'})
        return failures
    if q == 'global_optimal' and not diag.get('global_optimality_certificate'):
        failures.append({'code': 'GLOBAL_OPTIMAL_UNSUPPORTED', 'message': 'global_optimal requires diagnostics.global_optimality_certificate'})
    if q == 'certified_optimal' and not (diag.get('certificate_or_bound') or diag.get('duality_gap') is not None):
        failures.append({'code': 'CERTIFIED_OPTIMAL_UNSUPPORTED', 'message': 'certified_optimal requires certificate/bound/gap evidence'})
    if q == 'exhaustive_best' and not diag.get('enumerated_all_candidates'):
        failures.append({'code': 'EXHAUSTIVE_BEST_UNSUPPORTED', 'message': 'exhaustive_best requires enumerated_all_candidates=true'})
    return failures
