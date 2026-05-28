# .agent

这是 OS 级 agent 控制目录。case 初始化后，每个 case 也会生成自己的 `.agent/` 目录。

职责：

- 保存 agent 操作政策；
- 生成小问任务卡；
- 记录可读写文件白名单；
- 保存 gate 报告、solver verify 报告和 question status；
- 为多 agent/单 agent 长流程提供可审计上下文。
