# Academic Search Gate v7.1

## 1. 设计目标

v7.1 的 `academic-search` 不再只生成泛化关键词，而是基于 `final_problem_signature.json` 生成 **分层、带证据引用、可校验** 的检索计划。

系统仍然不伪造搜索结果。真实检索需要由 Agent、WebSearch、Semantic Scholar、Zotero 或其他外部检索器执行。

## 2. 命令

```bash
python scripts/mmtool.py academic-search <case_id> --budget full
python scripts/mmtool.py search-plan-gate <case_id>
```

## 3. 检索计划结构

每条 query 至少包含：

```json
{
  "query_id": "Q1.domain_model.001",
  "query": "reflow soldering thermal profile heat transfer mathematical model",
  "purpose": "domain_model",
  "reason": "Domain query for physical_process.thermal_process.",
  "priority": 0.9,
  "required": true,
  "evidence_ids": ["EVID-Q1-0001"]
}
```

## 4. Query purpose

v7.1 支持以下检索目的：

```text
domain_model          领域模型
method_algorithm      建模方法 / 算法
solver                求解器 / 数值算法
verification          验证、误差、稳健性
application_case      应用案例
constraint_handling   约束处理
data_processing       数据处理
```

## 5. search-plan-gate 检查

`search-plan-gate` 检查：

```text
query_id 是否存在且唯一；
query 文本是否为空；
purpose 是否合法；
evidence_ids 是否存在；
是否缺少 domain_model query；
是否缺少 verification query；
优化题是否缺少 solver / constraint_handling query。
```

## 6. 搜索结果填充契约

外部检索器应将真实结果写入：

```text
workspace/academic_search/search_results.json
```

每条结果建议包含：

```json
{
  "source_id": "SRC-Q1-0001",
  "query_id": "Q1.domain_model.001",
  "title": "...",
  "url": "...",
  "doi": "...",
  "source_type": "paper",
  "year": 2024,
  "snippet": "...",
  "identified_methods": [
    {
      "method_name": "thermal profile ODE model",
      "role": "primary_model",
      "evidence_span": "...",
      "relevance_score": 0.82
    }
  ]
}
```

如果结果没有 `identified_methods`，`method-recommend` 会输出 `needs_agent_extraction` 和 `method_extraction_tasks`，而不是伪造方法。

