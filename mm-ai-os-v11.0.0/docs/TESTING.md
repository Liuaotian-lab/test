# Testing Strategy

## 1. Smoke

```bash
python scripts/run_tests.py --tier smoke
```

检查语法编译、版本一致性和 CLI 帮助。

## 2. Dev

```bash
python scripts/run_tests.py --tier dev
```

在 smoke 基础上运行 pytest。

## 3. Release

```bash
python scripts/run_tests.py --tier release
```

执行环境验证。发布前建议依次运行 `--tier dev` 和 `--tier release`。

## 4. 关键测试目标

- 版本一致性；
- CLI 正式命令存在；
- 路径安全；
- 题目语义签名能稳定输出；
- 学术检索计划不伪造结果；
- 方法计划必须可追溯；
- 覆盖缺口能够明确报告；
- 纯净版不依赖历史案例或 legacy 目录。
