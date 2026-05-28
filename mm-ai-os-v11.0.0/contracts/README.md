# contracts

这是 OS 级 contract 定义目录。case 初始化后，每个 case 会有自己的 `contracts/` 目录。

v5.1 将 contracts 恢复为一等公民：

- global contracts：约束整个 case；
- question contracts：约束每个小问；
- gate contracts：约束每个阶段的验收条件；
- quality contracts：约束全局最优/启发式/近似等质量声明。
