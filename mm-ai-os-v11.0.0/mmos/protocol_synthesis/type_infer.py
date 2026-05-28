from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import write_json, read_json
from mmos.kernel.events import now_iso
from .common import case_text, qids

KEYWORDS = {
    'geometric_physical_optimization': ['坐标','距离','半径','几何','遮挡','碰撞','路径','反射','光线','mirror','ray','shadow','receiver','coordinate','distance'],
    'spatiotemporal_simulation': ['时间','仿真','状态','转移','微分','步长','模拟','simulation','state','time grid','ode'],
    'forecasting_prediction': ['预测','forecast','时间序列','回归','外推','趋势','预测值'],
    'evaluation_ranking': ['评价','排名','权重','指标','综合得分','rank','weight','score'],
    'resource_allocation_optimization': ['分配','调度','路径','成本','收益','容量','资源','规划','allocation','schedule','capacity'],
    'image_measurement_model': ['图像','图片','像素','标定','识别','分割','测量','image','pixel','calibration'],
    'statistical_estimation': ['统计','概率','样本','置信','显著','拟合','分布','statistics','probability']
}
STRUCTURE_KEYWORDS = {
    '3d_coordinate_geometry': ['坐标','x','y','z','三维','3d','coordinate'],
    'projection_or_occlusion': ['投影','阴影','遮挡','shadow','occlusion','blocking'],
    'ray_or_wave_propagation': ['光线','反射','辐射','ray','reflection','light','wave'],
    'nonconvex_optimization': ['最优','最大','最小','尽量','优化','maximize','minimize','optimal'],
    'time_sample_aggregation': ['年平均','月','时间','时刻','time','average'],
    'template_constrained_output': ['result','xlsx','表','模板','sheet','输出文件','excel'],
    'stochastic_or_statistical': ['随机','概率','统计','置信','分布','random','stochastic'],
    'forecast_backtest': ['预测','forecast','回测','backtest'],
}
STRONG_CLAIMS = ['最优','最大','最小','尽量大','尽量小','临界','边界','终止','排名第一','optimal','maximum','minimum','global','critical','boundary','terminal']


def _score(txt: str, words: list[str]) -> int:
    low = txt.lower()
    return sum(1 for w in words if w.lower() in low)


def problem_type_infer(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir)
    txt = case_text(case_dir)
    families=[]
    for fam, words in KEYWORDS.items():
        s=_score(txt, words)
        if s:
            families.append({'family': fam, 'confidence': min(0.99, 0.35 + 0.12*s), 'matched_keyword_count': s, 'evidence_ids': ['problem_corpus','constraint_ledger']})
    if not families:
        families=[{'family':'generic_modeling_problem','confidence':0.35,'matched_keyword_count':0,'evidence_ids':['problem_corpus']}]
    families=sorted(families, key=lambda x: x['confidence'], reverse=True)
    structures=[]
    for st, words in STRUCTURE_KEYWORDS.items():
        s=_score(txt, words)
        if s:
            structures.append({'structure': st, 'confidence': min(0.99, 0.4 + 0.15*s), 'matched_keyword_count': s})
    high_risk=[]
    low=txt.lower()
    for term in STRONG_CLAIMS:
        if term.lower() in low:
            high_risk.append({'risk': f'strong_claim_term:{term}', 'requires_certificate': True})
    result={
        'case_id': case_dir.name,
        'schema_version':'10.1.dynamic_protocol',
        'problem_families': families,
        'mathematical_structures': structures,
        'required_questions': qids(case_dir),
        'high_risk_claims': high_risk,
        'requires_dynamic_protocol': True,
        'generated_at': now_iso(),
    }
    out=case_dir/'workspace'/'dynamic_protocols'/'candidate'/'problem_type_inference.json'
    write_json(out, result)
    return {'status':'passed','path':str(out),'inference':result}
