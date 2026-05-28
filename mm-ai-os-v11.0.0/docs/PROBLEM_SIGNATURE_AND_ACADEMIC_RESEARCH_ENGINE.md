# Problem Signature 与 Academic Research Engine 设计说明

## 1. 建模初期为什么需要这两层

数学建模竞赛的前期错误通常不是代码错误，而是题意理解、方法选择和证据链错误。新版 OS 将建模初期拆成两层：

1. `problem_signature`：把题目文本转化为结构化语义签名；
2. `academic_research_engine`：基于语义签名生成检索计划、承接真实检索结果、匹配方法、合成方法计划并检查覆盖缺口。

这两层的目标不是直接求解，而是把“读题与选型”变成可审计的结构化过程。

## 2. Problem Signature 当前实现

入口函数：

```python
mmos.problem_signature.extractor.extract_problem_signature(case_dir, question_id=None)
```

输入来源：

- `workspace/problem_corpus.md`
- `workspace/problem_graph.json`
- 必要时回退读取 `data/raw/*.txt|*.md|*.csv`

核心流程：

```text
读取题面语料
  ↓
读取问题图谱
  ↓
确定 Q1/Q2/Q3 等子问题
  ↓
对每个问题执行启发式匹配
  ↓
输出 case.signatures.json
```

当前使用的规则表：

- `DOMAIN_RULES`：识别领域，例如热过程、液压压力控制、定日镜场、图网络、交通流、统计评价、随机仿真、约束优化；
- `TASK_RULES`：识别任务类型，例如机理建模、预测、参数估计、约束优化、仿真、评价；
- `QUANTITY_RULES`：识别物理量和变量，例如温度、时间、速度、位置、压力、流量、功率、成本；
- 约束抽取正则：识别“不超过、不少于、至少、至多、约束、限制、必须、不能、上限、下限”等表达。

输出文件：

```text
workspace/problem_signatures/case.signatures.json
```

典型输出结构：

```json
{
  "schema_version": "7.1.0-understanding-gated",
  "status": "passed",
  "case_id": "demo_case",
  "mode": "heuristic_bootstrap_agent_review_required",
  "questions": {
    "Q1": {
      "domain_family": {
        "primary": "physical_process.thermal_process",
        "confidence": 0.76,
        "evidence_terms": ["炉温", "温度"]
      },
      "physical_quantities": ["temperature", "time", "velocity"],
      "task_archetypes": [
        {"task": "mechanistic_modeling", "confidence": 0.47},
        {"task": "constrained_optimization", "confidence": 0.59}
      ],
      "constraints": [],
      "outputs_required": [
        {"artifact": "optimal_parameters", "confidence": 0.65},
        {"artifact": "model_and_solution_report", "confidence": 0.8}
      ]
    }
  }
}
```

## 3. Academic Research Engine 当前实现

主模块：

```text
mmos/academic_research_engine/search_orchestrator.py
mmos/academic_research_engine/method_matcher.py
mmos/academic_research_engine/plan_builder.py
mmos/academic_research_engine/coverage_checker.py
mmos/academic_research_engine/citation_manager.py
```

### 3.1 search_orchestrator

入口：

```python
orchestrate_academic_search(case_dir, question_id=None, budget="full", strict=True)
```

功能：

1. 读取 `workspace/problem_signatures/case.signatures.json`；
2. 确定需要检索的问题；
3. 根据领域、任务、实体、物理量和约束生成查询；
4. 写出 `workspace/academic_search/search_results.json`。

当前重要边界：它只生成检索计划与结果容器，不会自动联网检索。

### 3.2 method_matcher

入口：

```python
match_methods(case_dir, question_id=None, strict=True)
```

功能：

1. 读取 `workspace/academic_search/search_results.json`；
2. 要求每个真实搜索结果中包含 `identified_methods`；
3. 汇总方法候选；
4. 写出 `workspace/academic_search/method_matches.json`。

它不会凭空创造方法。如果 `results` 为空或结果中没有 `identified_methods`，严格模式下会失败。

### 3.3 plan_builder

入口：

```python
build_method_plan(case_dir, question_id=None, strict=True)
```

功能：

1. 读取 `method_matches.json`；
2. 按角色拆分为主模型、备选模型、优化方法、验证方法；
3. 汇总文献引用；
4. 写出 `workspace/method_plan/<QID>_method_plan.json` 与 `case.method_plan_summary.json`。

当前角色依赖字段：

- `role = "model"` 或 `"primary_model"`；
- `role = "optimization"`；
- `role = "verification"`。

### 3.4 coverage_checker

入口：

```python
check_coverage(case_dir, question_id=None, strict=True)
```

检查维度：

- 是否有主模型；
- 是否有足够备选模型；
- 优化任务是否有优化算法；
- 是否有独立验证方法；
- 是否有引用；
- 有约束时是否有约束处理方法。

输出：

```text
quality/coverage_gap_analysis.json
```

### 3.5 citation_manager

入口：

```python
build_citation_list(case_dir)
validate_citations(case_dir, strict=True)
```

功能：

- 从方法计划中汇总文献；
- 检查 title、url/snippet、referenced_by 等字段；
- 输出引用清单与引用校验报告。

## 4. 当前主要缺陷

### 4.1 题目语义识别仍然是浅层规则系统

当前识别依赖关键词命中，不能真正理解复杂语义、隐含变量、跨句约束、公式和图表中的语义。因此容易出现：

- 领域误判；
- 任务类型漏判；
- 变量抽取不完整；
- 约束抽取过宽或过窄；
- 对图表、附件和单位的理解不足。

### 4.2 置信度计算过于简单

当前 confidence 基本由命中词数量线性决定，没有考虑：

- 词语位置；
- 是否出现在问题要求部分；
- 是否属于附件说明；
- 多个领域之间的冲突；
- 反向证据。

### 4.3 检索查询生成过于模板化

查询主要来自领域模板、任务名、实体名和物理量组合。缺陷包括：

- 查询语义较粗；
- 中文题面到英文检索词的映射不够系统；
- 对公式名、标准模型名和竞赛常用建模术语覆盖不足；
- 没有 query 去重、排序和质量评分；
- 没有分层检索策略，例如综述、经典模型、求解算法、验证方法、应用案例分开检索。

### 4.4 学术检索执行链未闭环

当前不会自动联网执行检索，也不会自动抓取摘要、DOI、BibTeX 或 PDF 元数据。真实结果需要外部 Agent 或人工填充。

### 4.5 方法匹配依赖人工结构化字段

`method_matcher` 目前依赖搜索结果中已经存在 `identified_methods`。如果外部 Agent 只是填入 title/url/snippet，系统不会自动抽取方法名和角色。

### 4.6 方法计划缺少强 schema

当前方法字段较自由，容易出现不同 Agent 输出风格不一致的问题。例如同一个含义可能写成：

- `primary_model`
- `model`
- `approach`
- `method`

这会降低自动检查可靠性。

### 4.7 覆盖检查偏硬编码

coverage checker 当前只检查少数字段，尚未根据不同问题类型建立差异化覆盖标准。预测题、优化题、仿真题、评价题、机理题需要不同检查维度。

## 5. 改进方向

### 5.1 语义识别从关键词升级为多阶段解析

建议分为五级：

```text
L1 关键词召回
L2 句法与问题段落定位
L3 变量-单位-约束抽取
L4 问题类型分类与多标签冲突消解
L5 Agent/LLM 审阅增强与人工确认
```

### 5.2 建立领域本体与方法本体

新增：

```text
knowledge_packs/domain_ontology/
knowledge_packs/method_ontology/
```

领域本体记录领域别名、典型变量、常见方程、常见约束和推荐检索词。

方法本体记录方法名称、适用任务、输入要求、输出类型、验证方式和常用引用方向。

### 5.3 检索计划分层

每个问题至少生成五类查询：

1. 领域模型查询；
2. 任务方法查询；
3. 求解算法查询；
4. 验证方法查询；
5. 应用案例或竞赛相似问题查询。

### 5.4 search_results 增加严格 schema

每个真实检索结果建议包含：

```json
{
  "title": "...",
  "url": "...",
  "source_type": "paper|book|docs|article|dataset",
  "year": 2024,
  "venue": "...",
  "doi": "...",
  "snippet": "...",
  "query_id": "Q1.full.001",
  "identified_methods": [
    {
      "method_name": "...",
      "role": "primary_model|optimization|verification|data_preprocessing",
      "evidence_span": "...",
      "relevance_score": 0.0
    }
  ]
}
```

### 5.5 方法匹配加入自动抽取器

当 `identified_methods` 缺失时，系统可以先进入 `needs_agent_extraction` 状态，并生成 Agent 任务卡，而不是直接失败或空转。

### 5.6 覆盖检查按任务类型分策略

例如：

- 预测题：数据划分、误差指标、基准模型、外推风险；
- 优化题：变量、目标、约束、算法、可行性、灵敏度；
- 机理题：守恒关系、参数估计、数值稳定性、维度一致性；
- 仿真题：随机种子、重复次数、置信区间、方差分析；
- 评价题：指标体系、权重方法、一致性检验、稳健性排序。

## 6. 建议新增测试

详见 `docs/IMPROVEMENT_AND_TEST_PLAN.md`。
