from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import read_jsonl, append_jsonl, write_json, status_from, resolve_case_file


def _confidence(rec: dict) -> str:
    if rec.get('solver_status') in {'failed','timeout','iter_limit'} or rec.get('quality_level') in {'failed','exploratory'}:
        return 'low'
    if rec.get('violation_count') == 0 and len(rec.get('validators') or []) >= 2:
        return 'high'
    return 'medium'


def build_evidence_claims(case_dir: Path) -> list[dict]:
    case_dir=Path(case_dir).resolve()
    records=read_jsonl(case_dir/'reports'/'experiments_summary.jsonl')
    claims=[]
    for idx, rec in enumerate(records, start=1):
        confidence=_confidence(rec)
        claims.append({
            'claim_id': f'claim_{idx:03d}',
            'question_id': rec.get('question_id'),
            'claim': rec.get('conclusion') or f"{rec.get('question_id')} generated a solver result.",
            'experiment_id': rec.get('experiment_id'),
            'source_artifact': rec.get('source_solution') or (rec.get('artifacts') or [''])[0],
            'confidence': confidence,
            'validators': rec.get('validators') or [],
            'limitations': rec.get('limitations') or '',
            'allowed_in_paper': confidence in {'high','medium'} and rec.get('quality_level') not in {'failed','exploratory'},
            'allowed_in_abstract': confidence == 'high' and rec.get('quality_level') not in {'failed','exploratory'},
        })
    return claims


def write_evidence_map(case_dir: Path, claims: list[dict]) -> None:
    lines=['# Evidence Map','']
    for c in claims:
        lines += [f"## {c.get('claim_id')}", '', f"- 结论：{c.get('claim')}", f"- 来源：`{c.get('source_artifact')}`", f"- 实验：`{c.get('experiment_id')}`", f"- 置信度：{c.get('confidence')}", '- 验证器：']
        vals=c.get('validators') or []
        if vals:
            lines += [f"  - `{v}`" for v in vals]
        else:
            lines.append('  - 无')
        lines += [f"- 限制：{c.get('limitations')}", '']
    out=case_dir/'reports'/'evidence_map.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines).rstrip()+"\n", encoding='utf-8')


def evidence_pack_case(case_dir: Path) -> dict:
    case_dir=Path(case_dir).resolve()
    claims=build_evidence_claims(case_dir)
    final_claims=[{k:v for k,v in c.items() if k in {'claim_id','question_id','claim','experiment_id','source_artifact','confidence','allowed_in_paper','allowed_in_abstract'}} for c in claims if c.get('allowed_in_paper')]
    append_jsonl(case_dir/'reports'/'evidence_claims.jsonl', claims)
    append_jsonl(case_dir/'reports'/'final_claims.jsonl', final_claims)
    write_evidence_map(case_dir, claims)
    failures=[]; warnings=[]
    if not claims:
        failures.append({'code':'NO_EVIDENCE_CLAIMS','message':'Run experiment-pack before evidence-pack.'})
    report={'status':status_from(failures,warnings),'claims':claims,'final_claims':final_claims,'failures':failures,'warnings':warnings,'outputs':['reports/evidence_claims.jsonl','reports/final_claims.jsonl','reports/evidence_map.md']}
    write_json(case_dir/'reports'/'evidence_pack_report.json', report)
    return report
