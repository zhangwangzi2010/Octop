# Octop Harness

Octop Harness 是工程流程与协作契约，不替代根目录 `AGENTS.md` 的技术栈、模块边界和命令事实。执行需求时先读 `rules/00-index.md`；只有命中技能触发条件时才读取对应 `skills/*/SKILL.md`。

## 定位

- **OpenSpec 是需求单一事实源**：业务行为、接口、数据、权限、架构和部署变更先创建或更新 change，再实现。
- **Harness 是执行方法**：定义需求分析、方案设计、任务拆分、TDD、多智能体、多 worktree、验证、部署和 UAT 的执行纪律。
- **AGENTS.md 是工程宪法**：模块边界、迁移规则、测试命令和发布流程冲突时优先遵守 AGENTS.md。

## 目录

```text
.harness/
├── rules/                 # 流程与协作规则
│   ├── 00-index.md
│   ├── 01-agent-collaboration.md
│   ├── 02-git-worktree.md
│   ├── 03-testing-tdd.md
│   ├── 04-quality-gates.md
│   ├── 05-openspec-lifecycle.md
│   └── 06-module-boundaries.md
├── skills/                # 阶段化执行技能
│   ├── request-analysis/SKILL.md
│   ├── solution-design-task-breakdown/SKILL.md
│   ├── tdd-implementation/SKILL.md
│   ├── verification/SKILL.md
│   ├── worktree-development/SKILL.md
│   └── uat-deploy/SKILL.md
├── domains/store-diagnosis-baseline.md
├── implementation-plan.md
└── scripts/check_harness.py
```

## 自检

```powershell
uv run .harness/scripts/check_harness.py
```

当前阶段只校验文档结构、链接和 OpenSpec 状态；`make all` 是否接入该自检，待 harness 骨架确认后再单独评估，不在本阶段修改测试或开发功能。
