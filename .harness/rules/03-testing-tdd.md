# Testing and TDD

## 测试矩阵先行

实现前把验收标准映射到最低可观察层级：

| 层级 | 工具 | 适用 |
|---|---|---|
| 纯函数/规则 | pytest | 阈值、分级、排序、周期解析 |
| Repo/迁移 | pytest + SQLite/PG fixture | 成对迁移、幂等、恢复、owner 过滤 |
| API 契约 | FastAPI test client | 状态码、schema、i18n、权限 |
| 前端 | `npx tsc -b`、既有测试 | 类型、页面状态、i18n |
| 集成 | pytest + fake boundary | 编排、MCP、Agent、报告 |
| E2E/UAT | Playwright + 人工检查表 | 登录、创建 run、终态、报告、回归 |

## RED → GREEN → REFACTOR

1. 新增失败测试并运行，确认失败原因就是目标缺陷或缺失行为。
2. 记录命令和失败摘要到任务记录或交付说明。
3. 实现最小闭环，再跑同一命令转绿。
4. 只在绿灯后重构，并复跑受影响测试。

## 测试诚实

- 禁止删除断言、跳过测试、扩大容差、增加无意义等待或修改正确测试来制造通过。
- Mock 只能隔离所有权边界；对外部数据库、网络、容器或真实 LLM 的结论必须有真实验证。
- 先记录基线失败，再证明交付没有新增失败。
- 前端和 E2E 命令以 `AGENTS.md` §6 为准；不要虚构不存在的 npm script。
