# Agent Task Card: __QUESTION__

## 任务边界

- Case: `__CASE_ID__`
- Question: `__QUESTION__`
- Title: __TITLE__
- Required: __REQUIRED__
- Type: __TYPE__

## 必读文件

1. `contracts/questions/__QUESTION__/problem_spec.json`
2. `contracts/questions/__QUESTION__/tool_contract.json`
3. `contracts/questions/__QUESTION__/quality_contract.json`
4. `workspace/tool_recommendations/__QUESTION__.agent_bootstrap.md`

## 允许修改

- `engineering/questions/__QUESTION__/**`
- `results/__QUESTION__/**`
- `reports/**`
- `.agent/question_status/**`

## 禁止修改

- `data/raw/**`
- 上游小问的正式结果，除非显式重跑上游 workflow。

## 完成定义

- solver result 通过 `solver-verify`；
- required outputs 通过 `output-validate`；
- evidence map 中有关键结论来源；
- report 中披露 quality_level 和限制。
