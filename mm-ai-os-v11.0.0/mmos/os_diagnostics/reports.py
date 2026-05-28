from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import status_from


def _load_atoms(root: Path | None, case_dir: Path) -> dict[str, Any]:
    # Root may be unavailable from direct function tests; infer from case ancestors where possible.
    roots=[]
    if root: roots.append(Path(root))
    for p in [Path(case_dir), *Path(case_dir).parents]:
        if (p/'mmos'/'protocol_templates'/'atoms').exists(): roots.append(p)
    atoms={}
    for r in roots:
        for p in (r/'mmos'/'protocol_templates'/'atoms').glob('*.yaml'):
            try:
                obj=json.loads(p.read_text(encoding='utf-8'))
                atoms[obj['atom_id']]=obj
            except Exception:
                pass
    return atoms


def gate_escape_risk_check(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    risks=[]
    fidelity=read_json(case_dir/'quality'/'model_fidelity_check.json', {}) or {}
    if fidelity.get('status') in {'failed','warning'}:
        risks.append({'risk':'fidelity_gate_not_clean','severity':'high' if fidelity.get('status')=='failed' else 'medium','reason':'model fidelity check reported failures or warnings','recommended_fix':'raise model fidelity or downgrade claims'})
    vad=read_json(case_dir/'quality'/'validator_adequacy_v2_report.json', {}) or read_json(case_dir/'quality'/'validator_adequacy_report.json', {}) or {}
    if vad.get('status') in {'failed','warning'}:
        risks.append({'risk':'validator_adequacy_not_clean','severity':'high','reason':'validator adequacy is incomplete','recommended_fix':'add domain/math validators and mutation-detecting negative tests'})
    comp=read_json(case_dir/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json', {}) or {}
    for qid,c in (comp.get('question_contracts') or {}).items():
        if c.get('validators') and all(('schema' in v or 'output' in v or 'freshness' in v) for v in c.get('validators')):
            risks.append({'risk':'format_only_validators_may_pass','severity':'high','question_id':qid,'reason':'compiled validators appear format-oriented only','recommended_fix':'add math/domain validators from capability atoms'})
    report={'status':'warning' if risks else 'passed','gate_escape_risks':risks,'risk_count':len(risks),'generated_at':now_iso()}
    write_json(case_dir/'quality'/'gate_escape_risk_report.json', report)
    return report


def capability_gap_matrix(case_dir: Path, root: Path | None = None) -> dict[str, Any]:
    case_dir=Path(case_dir)
    atoms=_load_atoms(root, case_dir)
    match=read_json(case_dir/'workspace'/'dynamic_protocols'/'candidate'/'capability_atom_match.json', {}) or {}
    rows=[]; gaps=[]
    for m in match.get('matched_atoms') or []:
        aid=m.get('atom_id')
        status='supported' if aid in atoms else 'missing'
        if status=='missing':
            gaps.append({'required_atom':aid,'support_status':'missing','impact':'dynamic protocol cannot compile full atom requirements','recommended_action':'add atom template'})
        else:
            atom=atoms[aid]
            partial=not atom.get('required_validators') or not atom.get('required_negative_tests')
            status='partial' if partial else 'supported'
            if partial:
                gaps.append({'required_atom':aid,'support_status':'partial','impact':'validator or negative test coverage may be weak','recommended_action':'complete atom template'})
        rows.append({'required_atom':aid,'support_status':status,'confidence':m.get('confidence'),'minimum_fidelity':m.get('minimum_fidelity'),'claim_limit':m.get('claim_limit')})
    report={'status':'warning' if gaps else 'passed','capability_gaps':gaps,'matrix':rows,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'capability_gap_matrix.json', report)
    return report


def protocol_reuse_suggest(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    match=read_json(case_dir/'workspace'/'dynamic_protocols'/'candidate'/'capability_atom_match.json', {}) or {}
    suggestions=[]
    for m in match.get('matched_atoms') or []:
        if (m.get('confidence') or 0) >= 0.75:
            suggestions.append({'atom_id':m.get('atom_id'),'suggestion':'keep as reusable capability atom; candidate for regression fixture coverage','confidence':m.get('confidence')})
    report={'status':'passed','suggestions':suggestions,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'protocol_reuse_suggestions.json', report)
    return report


def os_improvement_report(case_dir: Path, root: Path | None = None) -> dict[str, Any]:
    case_dir=Path(case_dir)
    escape=read_json(case_dir/'quality'/'gate_escape_risk_report.json', {}) or gate_escape_risk_check(case_dir)
    gaps=read_json(case_dir/'quality'/'capability_gap_matrix.json', {}) or capability_gap_matrix(case_dir, root=root)
    reuse=read_json(case_dir/'quality'/'protocol_reuse_suggestions.json', {}) or protocol_reuse_suggest(case_dir)
    improvements=[]
    for r in escape.get('gate_escape_risks') or []:
        improvements.append({'priority':'P0' if r.get('severity')=='high' else 'P1','source':'gate_escape_risk','recommendation':r.get('recommended_fix'),'risk':r.get('risk')})
    for g in gaps.get('capability_gaps') or []:
        improvements.append({'priority':'P1','source':'capability_gap','recommendation':g.get('recommended_action'),'atom':g.get('required_atom')})
    report={'status':'warning' if improvements else 'passed','improvements':improvements,'gate_escape_risk_report':escape,'capability_gap_matrix':gaps,'protocol_reuse_suggestions':reuse,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'os_improvement_report.json', report)
    return report
