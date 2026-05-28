from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from .common import case_text, load_atoms, qids
from .type_infer import problem_type_infer

ATOM_KEYWORDS = {
    'coordinate_system':['坐标','x','y','z','经度','纬度','coordinate'],
    'unit_consistency':['单位','m','km','mw','kw','角度','弧度','unit'],
    'geometric_distance':['距离','半径','间距','中心','distance','radius','spacing'],
    'geometric_intersection':['相交','碰撞','覆盖','交会','接收','intersection','collision','coverage'],
    'projection_geometry':['投影','阴影','遮挡','shadow','blocking','occlusion'],
    'ray_propagation':['光线','反射','辐射','锥形','ray','reflection','light'],
    'formula_evaluation':['公式','sin','cos','exp','计算公式','formula'],
    'state_transition':['状态','转移','仿真','步长','微分','state','transition','simulation'],
    'optimization_objective':['最优','最大','最小','尽量','优化','objective','optimal','maximize','minimize'],
    'constraint_feasibility':['约束','要求','不得','范围','constraint','feasible'],
    'statistical_estimation':['统计','样本','置信','分布','概率','statistics'],
    'forecasting_backtest':['预测','forecast','回测','时间序列'],
    'stochastic_simulation':['随机','monte carlo','蒙特卡洛','stochastic'],
    'sensitivity_analysis':['参数','扰动','敏感','稳健','robust','sensitivity'],
    'boundary_certificate':['临界','边界','终止','最小可行','最大可行','boundary','critical'],
    'candidate_search_certificate':['候选','搜索','启发式','局部','candidate','search','heuristic'],
    'global_optimality_certificate':['全局最优','完整枚举','严格证明','global optimal','proof'],
    'output_schema_validation':['result','xlsx','模板','表','sheet','输出','excel'],
    'ranking_stability':['排名','评价','权重','指标','rank','weight'],
    'image_measurement':['图像','像素','标定','分割','image','pixel']
}


def _score(txt: str, words: list[str]) -> int:
    low=txt.lower()
    return sum(1 for w in words if w.lower() in low)


def capability_atom_match(root: Path, case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir); root=Path(root)
    inf_path=case_dir/'workspace'/'dynamic_protocols'/'candidate'/'problem_type_inference.json'
    if not inf_path.exists():
        problem_type_infer(case_dir)
    inf=read_json(inf_path,{}) or {}
    txt=case_text(case_dir)
    atoms=load_atoms(root)
    matched=[]
    for atom_id, atom in atoms.items():
        score=_score(txt, ATOM_KEYWORDS.get(atom_id, []))
        if score or atom_id in {'unit_consistency','constraint_feasibility','output_schema_validation','sensitivity_analysis'}:
            conf=0.45 + 0.1*score
            if atom_id in {'unit_consistency','constraint_feasibility'}:
                conf=max(conf,0.55)
            if atom_id=='sensitivity_analysis' and inf.get('high_risk_claims'):
                conf=max(conf,0.65)
            if atom_id=='output_schema_validation' and any(w in txt.lower() for w in ['result','xlsx','表','模板','excel']):
                conf=max(conf,0.75)
            matched.append({
                'atom_id':atom_id,
                'confidence':round(min(0.99,conf),3),
                'reason': atom.get('description','matched by keyword and constraint context'),
                'evidence_ids':['problem_type_inference','problem_corpus','constraint_ledger'],
                'required_solver_hooks': atom.get('required_solver_hooks',[]),
                'required_validators': atom.get('required_validators',[]),
                'required_negative_tests': atom.get('required_negative_tests',[]),
                'required_certificates': atom.get('required_certificates',[]),
                'minimum_fidelity': atom.get('minimum_fidelity','L1'),
                'claim_limit': atom.get('claim_limit','approximate')
            })
    if not matched:
        a=atoms.get('constraint_feasibility',{})
        matched.append({'atom_id':'constraint_feasibility','confidence':0.4,'reason':'generic fallback','evidence_ids':['problem_corpus'], 'required_solver_hooks':a.get('required_solver_hooks',[]), 'required_validators':a.get('required_validators',[]), 'required_negative_tests':a.get('required_negative_tests',[]), 'required_certificates':[], 'minimum_fidelity':'L1','claim_limit':'approximate'})
    matched=sorted(matched, key=lambda x:(x['confidence'], x['atom_id']), reverse=True)
    result={'case_id':case_dir.name,'schema_version':'10.1.dynamic_protocol','required_questions':qids(case_dir),'matched_atoms':matched,'generated_at':now_iso()}
    out=case_dir/'workspace'/'dynamic_protocols'/'candidate'/'capability_atom_match.json'
    write_json(out,result)
    return {'status':'passed','path':str(out),'match':result}
