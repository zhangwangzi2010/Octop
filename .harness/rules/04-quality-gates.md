# Quality Gates

## 证据分级

| 级别 | 必要证据 |
|---|---|
| 只读分析 | 现场检查、假设、风险；不声称实现 |
| 设计完成 | OpenSpec artifact 齐备并通过 `openspec validate <change>` |
| 实现增量 | RED/GREEN 证据 + 受影响测试 + 相关文档同步 |
| Review-ready | `make all` 最新通过；API/UI 变更含契约或界面验证 |
| 发布候选 | 迁移/回滚说明、部署冒烟、集成/UAT 证据、已知差距 |

## 标准命令

以后端为例：`uv run pytest tests/unit -x -q` → `make all`。UI 变更加 `cd dashboard && npx tsc -b`。i18n 变更加 `uv run pytest tests/unit/i18n -q`。

## 交付报告

必须包含：范围、实际命令与退出状态、新增/修改测试、RED 证据、已知差距、受影响文件。命令不可用时如实记录缺口。

## Harness 自检

文档或流程规则变更运行：

```powershell
uv run .harness/scripts/check_harness.py
```
