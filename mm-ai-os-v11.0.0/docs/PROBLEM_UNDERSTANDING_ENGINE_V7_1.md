# Problem Understanding Engine v7.1

## 1. 设计目标

v7.1 将建模初期的题目结构化理解从“固定关键词脚本”升级为“AI 约束式理解 + 确定性强校验”。系统本身不调用在线模型，而是提供 Agent 可填写的严格契约，同时内置证据切片、启发式兜底、critic、validator 与 gate。

核心原则：

```text
AI 负责生成候选理解；
证据块负责可追溯；
Schema 负责结构；
Validator 负责拒绝非法结果；
Critic 负责发现遗漏和过度推断；
Gate 负责决定能否进入学术检索。
```

## 2. 模块位置

```text
mmos/problem_understanding/
  evidence/document_slicer.py
  ai_extractors/signature_extractor.py
  critics/signature_critic.py
  validators/validators.py
  adjudication/consensus_builder.py
  orchestrator.py
```

## 3. 命令

```bash
python scripts/mmtool.py problem-understand <case_id>
python scripts/mmtool.py understanding-gate <case_id>
```

兼容命令：

```bash
python scripts/mmtool.py problem-signature-extract <case_id>
```

该命令现在调用 `problem_understanding`，然后输出旧 v7.0 模块可读取的兼容视图。

## 4. 关键产物

```text
workspace/problem_understanding/evidence_index.json
workspace/problem_understanding/candidate_signatures.json
workspace/problem_understanding/signature_review.json
workspace/problem_understanding/final_problem_signature.json
quality/understanding_gate_report.json
workspace/problem_signatures/case.signatures.json
```

## 5. 证据切片

`evidence_index.json` 为每段题面、问题片段和数据清单生成 `evidence_id`。

后续所有正式语义判断都应引用证据：

```json
{
  "claim": "需要优化传送带速度",
  "claim_type": "inference",
  "evidence_ids": ["EVID-Q1-0001"],
  "confidence": 0.72
}
```

## 6. Agent 候选签名

外部 Agent 可写入：

```text
workspace/problem_understanding/agent_candidate_signature.json
```

系统优先采用 Agent 候选，但仍执行：

```text
证据 ID 是否真实存在；
每个关键字段是否有 evidence_ids；
confidence 是否合法；
优化题是否有变量/约束准备度；
预测题是否有目标变量准备度；
题面出现约束词时 constraints 是否为空；
题面出现附件/数据词时 data_requirements 是否为空。
```

## 7. 确定性兜底

如果没有 Agent 候选，系统使用启发式兜底生成 candidate signature。兜底结果会标记为：

```text
heuristic_bootstrap_agent_review_required
```

该结果适合启动流程，不应被视为最终题意理解。

## 8. Gate 语义

`understanding-gate` 的状态：

| 状态 | 含义 |
|---|---|
| passed | 可进入 academic-search |
| warning | 可继续试运行，但正式提交前需 Agent/人工复核 |
| failed | 不应进入 academic-search，应修复题目理解 |

