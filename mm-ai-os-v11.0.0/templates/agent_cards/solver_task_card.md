# Solver Task Card: __QUESTION__

## Solver 要求

- 入口：`engineering/questions/__QUESTION__/run.py`
- 标准阶段：`validate`、`reduced`、`real`、`report`
- 结果文件：`results/__QUESTION__/outputs/solution_real.json`

## 结构化输出字段

必须包含：

```json
{
  "question_id": "__QUESTION__",
  "status": "success",
  "quality_level": "heuristic_feasible",
  "diagnostics": {
    "fallback_used": false,
    "warnings": []
  }
}
```

## 质量声明

没有完整枚举、数学证明、对偶界或 solver certificate 时，不得声明 `global_optimal`。
