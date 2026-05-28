# Version Policy

当前版本：`7.4.0-candidate-official-split`。

版本号采用：

```text
MAJOR.MINOR.PATCH[-profile]
```

含义：

- MAJOR：主工作流或合同结构发生不兼容变化；
- MINOR：新增正式模块或重要命令；
- PATCH：修复、清理、文档和测试更新；
- profile：发行形态，例如 `academic-research-engine-pure`。

单一可信版本源是 `VERSION.txt`。以下文件必须保持一致：

- `VERSION.txt`
- `mmos/__init__.py`
- `os_manifest.json`
- `contracts/os_contract.json`
