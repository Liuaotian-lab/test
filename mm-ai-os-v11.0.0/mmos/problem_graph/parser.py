from __future__ import annotations
from pathlib import Path
import re
from mmos.kernel.jsonio import write_json, read_json

CN_NUM = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}

QUESTION_PATTERNS = [
    # 问题一 / 任务一 / 小问一
    re.compile(r'(?m)^\s*(?:问题|任务|小问)\s*([一二三四五六七八九十]|\d{1,2})\s*[：:、.\s]'),
    # 第1问 / 第一题
    re.compile(r'(?m)^\s*第\s*([一二三四五六七八九十]|\d{1,2})\s*(?:问|题)\s*[：:、.\s]'),
    # Q1 / Question 1 / Task 1
    re.compile(r'(?mi)^\s*(?:Q|Question|Task)\s*([0-9]{1,2})\s*[：:、.\s]'),
    # 1、 2. 3: at line start. This is common in CUMCM statements.
    re.compile(r'(?m)^\s*([1-9]\d?)\s*[、.]\s*(?=\S)'),
    # （1） / (1)
    re.compile(r'(?m)^\s*[（(]\s*([1-9]\d?)\s*[）)]\s*(?=\S)'),
]

STOP_SECTION_PATTERNS = [
    re.compile(r'(?m)^\s*##\s*SOURCE:'),
    re.compile(r'(?m)^\s*(?:附录|附件|参考文献|Appendix|References)\b'),
    re.compile(r'(?m)^\s*(?:一、|二、|三、|四、|五、|六、|七、|八、|九、|十、)\s*(?:附录|参考|模型|结论|问题重述)'),
]

DOMAIN_HINTS = [
    (r'炉温曲线|回焊炉|温区|焊接区域|传送带|峰值温度|217ºC|217°C', 'generic_optimization'),
    (r'反射面|抛物面|馈源舱|促动器|主索|基准球面|接收比|FAST', 'physics_fast_active_reflector'),
    (r'定日镜|吸收塔|太阳高度角|太阳方位角|光学效率|截断效率', 'solar_heliostat_field'),
    (r'置信|抽样|次品率|假设检验|显著性', 'statistical_decision'),
    (r'预测|时间序列|回归|误差|外推', 'forecasting'),
    (r'路径|网络流|最短路|社交网络|传播', 'graph_network'),
]


def num_to_q(x: str) -> str:
    x = str(x).strip()
    if x.isdigit():
        return f'Q{int(x)}'
    return f'Q{CN_NUM.get(x, x)}'


def _find_hits(text: str) -> list[dict]:
    hits = []
    for pat in QUESTION_PATTERNS:
        for m in pat.finditer(text):
            # Avoid chapter headers like "1.1" and bare list items that are not task anchors.
            line_end = text.find('\n', m.start())
            line = text[m.start(): line_end if line_end != -1 else len(text)].strip()
            if re.match(r'^\d+\.\d+', line):
                continue
            if len(line) > 220 and not re.search(r'求|确定|计算|给出|建立|分析|设计|比较|输出|保存|解决|如何|设置|调整|控制|稳定', line):
                continue
            raw = m.group(1)
            hits.append({'id': num_to_q(raw), 'start': m.start(), 'match': m.group(0).strip(), 'line': line})
    # Keep earliest hit per question id, but do not allow a later generic numbered list to override explicit question anchors.
    by_id = {}
    for h in sorted(hits, key=lambda x: x['start']):
        if h['id'] not in by_id:
            by_id[h['id']] = h
    return sorted(by_id.values(), key=lambda x: x['start'])


def _guess_problem_type(text: str) -> str:
    for pat, typ in DOMAIN_HINTS:
        if re.search(pat, text, flags=re.I):
            return typ
    if re.search(r'优化|最大|最小|约束|规划|objective|optimi[sz]e', text, flags=re.I):
        return 'generic_optimization'
    return 'unknown'



def _normalize_inline_question_anchors(text: str) -> str:
    """Insert line breaks before explicit inline Chinese question anchors.

    DOCX/PDF extraction often collapses CUMCM statements into one long paragraph,
    e.g. "...问题1 请...问题2 假设...". The parser historically only matched
    anchors at line starts, so multi-question real statements could collapse into Q1.
    Do not split references such as "结合问题3" or "根据问题1".
    """
    def repl(m: re.Match) -> str:
        start = m.start()
        prev = text[max(0, start-8):start]
        if re.search(r'(结合|根据|基于|参见|参考|上述|前述|见|如)', prev):
            return m.group(0)
        if start > 0 and text[start-1] != '\n':
            return '\n' + m.group(0)
        return m.group(0)
    return re.sub(r'问题\s*([一二三四五六七八九十]|\d{1,2})\s*[：:、.\s]', repl, text)

def parse_questions_from_text(text: str) -> list[dict]:
    text = _normalize_inline_question_anchors(text)
    hits = _find_hits(text)
    if not hits:
        return []
    # If first numbered hit starts before phrase "解决以下问题" but later hits exist after it, prefer later task region.
    anchor = re.search(r'解决以下问题|请.*解决.*问题|要求.*如下|问题如下', text)
    if anchor:
        after = [h for h in hits if h['start'] >= anchor.start()]
        if len(after) >= 2:
            hits = after
    # Limit terminal span before appendix/reference if it appears after last hit.
    stop_positions = []
    for pat in STOP_SECTION_PATTERNS:
        for m in pat.finditer(text):
            if hits and m.start() > hits[0]['start']:
                stop_positions.append(m.start())
    doc_end = min(stop_positions) if stop_positions else len(text)
    ordered = hits
    out = []
    for i, h in enumerate(ordered):
        end = ordered[i+1]['start'] if i+1 < len(ordered) else doc_end
        if end <= h['start']:
            end = len(text)
        span = text[h['start']:end].strip()
        qid = h['id']
        title = guess_title(span, qid)
        out.append({
            'question_id': qid,
            'title': title,
            'required': not bool(re.search(r'选做|有余力|optional|bonus', span[:400], re.I)),
            'type': _guess_problem_type(span),
            'source_span': {'start': h['start'], 'end': end, 'anchor': h.get('match')},
            'source_excerpt': span[:1500],
            'extracted_requirements': extract_requirements(span),
        })
    return out


def guess_title(span: str, qid: str) -> str:
    lines = [x.strip() for x in span.splitlines() if x.strip()]
    line = lines[0] if lines else qid
    line = re.sub(r'^\s*(?:问题|任务|小问|第|Q|Question|Task)?\s*[一二三四五六七八九十\d]+\s*(?:问|题)?[：:、.）)\s]*', '', line, flags=re.I)
    return line[:100] or qid


def extract_requirements(span: str) -> dict:
    return {
        'has_output_file_requirement': bool(re.search(r'result\.(xlsx|csv)|结果.*保存|附件\s*\d|提交|输出', span, re.I)),
        'has_constraints': bool(re.search(r'约束|不超过|范围|不少于|大于|小于|不小于|不大于|满足', span)),
        'has_comparison': bool(re.search(r'比较|对比|提升|改善|接收比|优化前|优化后|基准', span)),
        'has_simulation_or_sampling': bool(re.search(r'模拟|蒙特卡洛|采样|仿真|射线|追迹|随机', span)),
    }


def build_problem_graph(case_dir: Path) -> dict:
    case_dir = Path(case_dir).resolve()
    corpus = case_dir / 'workspace' / 'problem_corpus.md'
    text = corpus.read_text(encoding='utf-8', errors='ignore') if corpus.exists() else ''
    questions = parse_questions_from_text(text)
    if not questions:
        questions = [{'question_id': 'Q1', 'title': '默认问题', 'required': True, 'type': _guess_problem_type(text), 'source_span': {}, 'source_excerpt': text[:1500], 'extracted_requirements': extract_requirements(text[:3000])}]
    registry_path = case_dir / 'registry' / 'questions_registry.json'
    existing = read_json(registry_path, default={'questions': []}) or {'questions': []}
    existing_by_id = {q.get('question_id'): q for q in existing.get('questions', [])}
    merged = []
    for q in questions:
        old = existing_by_id.get(q['question_id'], {})
        preserved = {k:v for k,v in old.items() if k in {'depends_on','status'} and v not in (None, '')}
        # Preserve curated type/title only if parser cannot infer better info.
        if old.get('type') and q.get('type') in {None, '', 'unknown'}:
            preserved['type'] = old.get('type')
        if old.get('title') and q.get('title') in {None, '', q['question_id']}:
            preserved['title'] = old.get('title')
        if old.get('required') is not None:
            preserved['required'] = old.get('required')
        merged.append({**q, **preserved, 'status': old.get('status','parsed')})
    graph = {'case_id': case_dir.name, 'questions': merged, 'question_count': len(merged), 'dependencies': infer_dependencies(merged), 'parser_version': 'v5.6.1-inline-question-longline-fix'}
    write_json(case_dir / 'workspace' / 'problem_graph.json', graph)
    write_json(registry_path, {'case_id': case_dir.name, 'questions': merged, 'question_count': len(merged)})
    return graph


def infer_dependencies(questions: list[dict]) -> list[dict]:
    deps=[]
    ids=[q['question_id'] for q in questions]
    for q in questions:
        txt=(q.get('source_excerpt') or '')[:600]
        for prev in ids:
            if prev == q['question_id']:
                continue
            n = re.sub(r'\D','',prev)
            if n and re.search(fr'第\s*{n}\s*问|问题\s*{n}|基于.*第\s*{n}|根据.*第\s*{n}', txt):
                deps.append({'from': prev, 'to': q['question_id'], 'reason': 'textual_reference'})
    return deps
