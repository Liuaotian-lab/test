from __future__ import annotations

def _exit_code_from_payload(payload, strict_warnings=False):
    if isinstance(payload, dict):
        status = payload.get('status')
        if status == 'failed' or payload.get('final_allowed') is False:
            return 1
        if strict_warnings and status == 'warning':
            return 1
    return 0
