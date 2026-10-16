# Harness Implementation Plan

## 阶段 1：骨架落地（本次完成）

- 创建 `.harness/`：7 条规则、6 张技能卡、店铺诊断领域基线、实施说明和结构自检脚本。
- 在根目录 `AGENTS.md` §10 增加 Harness 入口引用。
- 不启动店铺诊断开发、不创建功能 worktree、不修改业务代码、不修改 `Makefile`、不运行开发测试。

## 阶段 2：骨架确认

1. 运行 `uv run .harness/scripts/check_harness.py`。
2. 运行 `openspec validate add-store-diagnosis`。
3. 人工审阅规则是否与团队授权、合并和 UAT 闸门匹配。
4. 确认店铺诊断领域基线与飞书 wiki、OpenSpec change 没有口径冲突。

## 阶段 3：实战演练（需用户明确授权）

以 `add-store-diagnosis` 为首个 change，按 `tasks.md` 的 WT 分组创建 worktree，只执行一轮“需求核对 → 设计核对 → 任务核对 → RED 测试设计 → 门禁设计”。这一步仍不直接实现业务，除非用户再次明确授权编码。

## 阶段 4：长期防漂移（需用户单独授权）

评估把 `uv run .harness/scripts/check_harness.py` 加入 `make all` 或 pre-commit。先测量耗时和跨平台表现，再修改 Makefile；避免让文档检查阻塞紧急文档修复。

## 阶段 5：真实开发、测试、部署与 UAT

按 OpenSpec tasks 启动实现：DB+Data → Orchestrator → API → Agent/Skill/MCP → Dashboard → E2E/UAT。每个模块保持 RED→GREEN→REFACTOR，合并前运行对应门禁，部署与 UAT 只记录实际结果。
