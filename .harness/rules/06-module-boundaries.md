# Module Boundaries

完整边界以根目录 `AGENTS.md` §5 为准。本文件只列执行检查。

## 检查清单

- 新增领域编排放 `infra/<domain>/`，HTTP 只做薄适配，CLI 只做终端 UX。
- `infra/` 不 import `api/`、`cli/`、`launch.py`；`api/` 不 import `cli/` 或 `launch.py`。
- Repo 只承载 SQL；跨表业务规则放 manager 或领域服务。
- 资源迁移遵守整数代理 PK + 公共字符串 ID 规范，并成对提供 SQLite/PG SQL。
- Dashboard 只经 `dashboard/src/api/` 访问 `/api`，不感知 Python 模块。
- 用户可见服务端文案走 backend i18n；Dashboard chrome 走前端 locales。
- Agent workspace 内容 I/O 经 `HarnessAgent.workspace`，不直接读写路径。

## 店铺诊断落点

- 编排与状态机：`src/octop/infra/diagnosis/`
- 数据访问：`infra/db/repos/` + `infra/backend/` 或 connector
- HTTP：`api/routers/diagnosis.py`
- 前端：`dashboard/src/api/modules/`、页面与共享组件
- Skill/MCP：遵循 `infra/skills/` 与 `infra/connectors/` 现有架构，不在 Skill 内执行 SQL
