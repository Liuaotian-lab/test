from __future__ import annotations

def normalize_validation_result(result):
    if result is True:
        return {'status':'passed','failures':[],'violation_count':0}
    if result is False:
        return {'status':'failed','failures':[{'code':'VALIDATOR_RETURNED_FALSE'}],'violation_count':1}
    if isinstance(result, list):
        return {'status':'failed' if result else 'passed','failures':result,'violation_count':len(result)}
    if isinstance(result, dict):
        failures=result.get('failures') or result.get('violations') or []
        return {'status':result.get('status') or ('failed' if failures else 'passed'), 'failures':failures, 'violation_count':int(result.get('violation_count', len(failures)))}
    return {'status':'failed','failures':[{'code':'VALIDATOR_BAD_RETURN_TYPE','type':type(result).__name__}], 'violation_count':1}
