# Case Directory Specification

`cases/` 是用户运行区。纯净版不内置历史案例。

推荐结构：

```text
cases/<case_id>/
  case.json
  data/
    raw/
    processed/
    manifest/
  workspace/
    problem_corpus.md
    problem_corpus.json
    problem_graph.json
    problem_signatures/
    academic_search/
    method_plan/
  registry/
    questions_registry.json
  questions/
  contracts/
  results/
  evidence/
  quality/
  paper/
  final_outputs/
  package/
```

规则：

- `data/raw/` 放原始题面和附件；
- `workspace/` 放中间结构化产物；
- `quality/` 放审计与门禁报告；
- `paper/` 放论文产物；
- `package/` 放提交包；
- 运行生成物默认不提交到版本库。
