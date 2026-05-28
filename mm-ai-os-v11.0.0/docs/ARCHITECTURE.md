# MM-AI OS 7.4.0-candidate-official-split Architecture

## 1. 定位

MM-AI OS 7.4.0-candidate-official-split 是面向数学建模竞赛的 Agentic Modeling OS。纯净版只保留当前正式主线：题面理解、学术检索计划、方法计划、合同激活、语义审计、论文生成和提交门禁。

纯净版不包含历史案例、不包含旧能力包、不包含旧路由器、不包含历史 benchmark 数据。

## 2. 架构层次

```text
原始题面材料
  ↓
ingestion：材料摄取与语料归一化
  ↓
problem_graph：问题图谱与子问题拆分
  ↓
problem_signature：题目语义签名
  ↓
academic_research_engine：检索计划、方法匹配、覆盖缺口、引用校验
  ↓
contracts：问题合同、变量、目标、约束、输出、证据与质量合同
  ↓
agent_protocols / workflow_runtime：Agent 任务卡与执行流程
  ↓
semantic_audit / semantic_checks：语义审计与一致性检查
  ↓
paper_excellence / paper_latex：论文结构与 LaTeX 生成
  ↓
gates / submission：最终门禁与提交包
```

## 3. 正式主线模块

- `mmos/ingestion/`：读取题面、附件与数据文件，生成统一语料。
- `mmos/problem_graph/`：识别 Q1/Q2/Q3 等子问题。
- `mmos/problem_signature/`：抽取领域、任务、变量、约束与输出需求。
- `mmos/academic_research_engine/`：生成检索计划、承接检索结果、匹配方法、合成方法计划、检查覆盖缺口。
- `mmos/contracts/`：激活结构化求解合同。
- `mmos/agent_protocols/`：生成 Agent 任务卡与协议检查。
- `mmos/semantic_checks/` 与 `mmos/semantic_audit/`：检查模型、数据、时间、附件与结果语义一致性。
- `mmos/paper_excellence/` 与 `mmos/paper_latex/`：生成和检查论文。
- `mmos/gates/` 与 `mmos/submission/`：执行最终门禁与提交打包。

## 4. 非正式内容

纯净版不包含以下内容：

- 历史案例归档；
- v6 capability packs；
- v6 capability router；
- v6 capability atoms；
- 历史答案 benchmark 数据；
- 依赖历史案例的测试。

## 5. 证据边界

Academic Research Engine 当前是“检索计划与证据容器”，不是内置联网搜索器。它不会凭空生成文献证据。外部 Agent 或检索器必须把真实搜索结果写入 `workspace/academic_search/search_results.json`，后续模块才会进行方法匹配与引用校验。

## 6. v7.3 Schema Gate

`7.4.0-candidate-official-split` adds a formal schema layer without changing the v7.1-compatible workflow. Critical JSON artifacts now have contracts under `schemas/`, validation utilities under `mmos/core/schema.py`, and CLI access through `schema-list` and `schema-validate`.

The schema layer is intentionally backward-compatible and permissive about extra fields. It is designed to make AI-generated and workflow-generated JSON artifacts machine-checkable before the stricter `7.4.0` candidate/official artifact split.
