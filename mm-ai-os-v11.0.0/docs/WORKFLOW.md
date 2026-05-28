# MM-AI OS 7.4.0-candidate-official-split Workflow

## 1. 标准流程

```bash
python scripts/mmtool.py case-init <case_id>
python scripts/mmtool.py ingest-documents <case_id>
python scripts/mmtool.py problem-parse-v2 <case_id>
python scripts/mmtool.py problem-understand <case_id>
python scripts/mmtool.py understanding-gate <case_id>
python scripts/mmtool.py academic-search <case_id> --budget full
python scripts/mmtool.py search-plan-gate <case_id>
python scripts/mmtool.py method-recommend <case_id> --all
python scripts/mmtool.py method-plan-synthesize <case_id> --all
python scripts/mmtool.py coverage-gap-analysis <case_id> --all
python scripts/mmtool.py citation-validate <case_id>
python scripts/mmtool.py question-activate <case_id> --all --type auto
python scripts/mmtool.py agent-task-generate <case_id> --all --phase all
python scripts/mmtool.py final-gate <case_id>
python scripts/mmtool.py paper-build <case_id>
python scripts/mmtool.py package-submit <case_id>
```

## 2. 阶段说明

1. `case-init`：创建干净 case 目录。
2. `ingest-documents`：把题面和附件整理为统一语料。
3. `problem-parse-v2`：拆分子问题。
4. `problem-understand`：执行证据切片、Agent 候选签名读取、启发式兜底、critic 与 validator，生成正式题目理解产物。
5. `understanding-gate`：判断当前题目理解是否足以进入学术检索。
6. `academic-search`：基于 `final_problem_signature.json` 生成分层、带证据引用的检索计划与结果容器。
7. `search-plan-gate`：检查 query_id、purpose、evidence、验证类检索、求解/约束检索是否完备。
8. `method-recommend`：从真实检索结果中抽取候选方法；如果缺少 `identified_methods`，会生成 Agent 抽取任务。
9. `method-plan-synthesize`：合成每个问题的方法计划。
10. `coverage-gap-analysis`：检查模型、求解、验证、约束和引用覆盖缺口。
11. `citation-validate`：检查引用可追溯性。
12. `question-activate`：生成问题合同。
13. `agent-task-generate`：生成 Agent 任务卡。
14. `final-gate`：执行最终质量门禁。
15. `paper-build`：生成论文材料。
16. `package-submit`：生成提交包。

## 3. 兼容命令

`problem-signature-extract` 仍可使用，但它现在是 v7.1 的兼容包装器：内部调用 `problem-understand`，并生成 `workspace/problem_signatures/case.signatures.json` 供旧 v7.0 模块读取。

## 4. 学术检索边界

`academic-search` 不会自动联网检索。它会输出 queries 和结构化结果容器。真实检索结果应由 Agent 或外部搜索执行器补充。没有检索证据的内容不能进入正式方法计划。
