# Problem Signature 与 Academic Research Engine 改进与测试方案

## 1. 改进目标

目标不是让系统直接代替建模者，而是让建模初期的“题意理解、方法选择和证据链构建”更可靠、更可审计、更可测试。

优先级：

1. 提高题目语义识别准确性；
2. 提高检索查询质量；
3. 建立严格的检索结果 schema；
4. 让方法匹配从“人工字段依赖”升级为“自动抽取 + Agent 复核”；
5. 让覆盖检查按任务类型执行差异化门禁；
6. 用测试防止系统再次依赖历史案例或旧能力包。

## 2. 模块改进计划

### P0：纯净性与版本边界

- 保证仓库不含历史案例；
- 不含 legacy 源码；
- CLI 不暴露旧能力命令；
- 测试不依赖历史题目；
- 文档不把历史案例作为必要输入。

验收测试：

```text
不存在 examples/legacy_cases_archive
不存在 legacy/
不存在 mmos/capability_router
不存在 mmos/capability_planning
README 不引用历史案例归档
pytest 不读取历史案例路径
```

### P1：语义识别增强

新增 `problem_signature/analyzers/`：

```text
domain_classifier.py
task_classifier.py
quantity_extractor.py
constraint_extractor.py
artifact_extractor.py
confidence_calibrator.py
```

改进点：

- 领域识别支持多标签；
- 任务识别支持主任务与辅助任务；
- 变量识别带单位、来源和上下文；
- 约束识别带约束方向、阈值、单位；
- 输出需求识别区分数值表、图、算法、证明、论文叙述；
- 每个结论给出 evidence span。

### P2：检索计划增强

新增 query planner：

```text
academic_research_engine/query_planner.py
```

每个问题生成分层 queries：

```text
domain_model_queries
method_queries
solver_queries
verification_queries
data_processing_queries
application_case_queries
```

每条 query 包含：

```json
{
  "query_id": "Q1.domain.001",
  "query": "...",
  "language": "en|zh",
  "purpose": "domain_model|solver|verification",
  "priority": 0.0,
  "required": true
}
```

### P3：检索结果 schema

新增：

```text
schemas/academic_research/search_result.schema.json
schemas/academic_research/identified_method.schema.json
```

约束：

- 每个 result 必须有 title；
- 每个 result 必须有 url、doi 或 snippet 至少一个；
- 每个 method 必须有 evidence_span；
- 每个 method 必须有 role；
- relevance_score 范围为 0 到 1。

### P4：方法自动抽取与复核

当 result 没有 `identified_methods` 时，系统不应直接假设无方法，而应输出：

```json
{
  "status": "needs_agent_extraction",
  "action": "extract identified_methods from search results"
}
```

随后由 Agent 或外部抽取器填充方法。

### P5：覆盖检查分题型策略

新增：

```text
academic_research_engine/coverage_policies/
  prediction.json
  constrained_optimization.json
  mechanistic_modeling.json
  simulation.json
  evaluation.json
```

不同题型使用不同检查项。

## 3. 测试矩阵

### 3.1 纯净性测试

新增 `tests/test_purity_contract.py`。

检查：

```python
assert not (ROOT / "legacy").exists()
assert not (ROOT / "examples" / "legacy_cases_archive").exists()
assert not (ROOT / "mmos" / "capability_router").exists()
assert not (ROOT / "mmos" / "capability_planning").exists()
```

### 3.2 题目语义识别测试

新增 `tests/test_problem_signature_semantics.py`。

覆盖题型：

- 热过程优化；
- 液压压力控制；
- 图网络最短路/最大流；
- 交通流预测；
- 统计评价排序；
- 随机仿真；
- 纯文本弱语义题。

每个测试检查：

- primary domain；
- task_archetypes；
- quantities；
- constraints；
- confidence 合理范围；
- unknown 场景不会错误高置信。

### 3.3 检索计划测试

新增 `tests/test_academic_query_planning.py`。

检查：

- fast/regression/full 三档 query 数量；
- 热学题必须生成 heat/thermal/temperature 相关 query；
- 图论题不能误生成 thermal query；
- 优化题必须包含 solver/optimization query；
- 有约束时必须包含 constraint query；
- query_id 唯一；
- query 去重。

### 3.4 检索结果 schema 测试

新增 `tests/test_search_result_schema.py`。

场景：

- 合法论文结果；
- 缺少 title；
- 缺少 url/doi/snippet；
- identified_methods 缺少 role；
- relevance_score 越界。

### 3.5 方法匹配测试

新增 `tests/test_method_matching.py`。

场景：

- 有 identified_methods：应生成 method_matches；
- 只有 title/url/snippet：应输出 needs_agent_extraction；
- 空 results：应失败且不伪造方法；
- method role 不合法：应 schema fail。

### 3.6 方法计划测试

新增 `tests/test_method_plan_builder.py`。

检查：

- primary_model 选择；
- alternative_models 数量；
- optimization_method 存在；
- verification_approach 存在；
- literature_references 去重；
- 无引用方法不能通过 strict 模式。

### 3.7 覆盖缺口测试

新增 `tests/test_coverage_policies.py`。

按题型检查：

- 优化题无优化算法应 fail；
- 预测题无误差指标应 fail；
- 机理题无守恒或参数校准应 warning/fail；
- 仿真题无重复次数和随机种子应 fail；
- 评价题无权重稳健性应 warning/fail。

### 3.8 端到端测试

新增小型非历史 synthetic case：

```text
fixtures/synthetic_cases/thermal_optimization_minimal/
```

流程：

```bash
case-init
ingest-documents
problem-parse-v2
problem-signature-extract
academic-search
method-recommend
method-plan-synthesize
coverage-gap-analysis
citation-validate
```

要求：

- 不依赖历史案例；
- 不联网；
- 用人工构造的 search_results fixture 测方法链路；
- strict 模式能准确区分通过、警告和失败。

## 4. 发布验收

发布前必须通过：

```bash
python -m compileall -q mmos scripts tests
python scripts/check_version_consistency.py
python -m pytest tests -q
python setup_verify.py
python scripts/run_tests.py --tier release
```

并确认：

```text
历史案例数量 = 0
legacy 目录不存在
旧 capability 模块不存在
README 不引用历史案例归档
正式测试不依赖历史案例路径
```
