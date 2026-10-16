---
name: uat-deploy
description: Execute deployment smoke, migration checks, UAT scripts, rollback evidence, and OpenSpec archive preparation.
---

# UAT and Deploy

## 触发

实现与自动化验证已完成，进入本地部署、预发、UAT 或归档准备。

## 步骤

1. 冻结版本与配置，记录环境、服务地址和外部依赖。
2. 执行部署冒烟：服务健康、Dashboard 登录、关键路由、定时任务。
3. 核对迁移与回滚步骤；不可回滚数据先备份并取得授权。
4. 按 UAT 检查表执行，保存截图或 trace，不预填通过结论。
5. 人工签字后整理 OpenSpec 归档材料。

## 店铺诊断 UAT 基线

登录、诊断入口、创建 run、详情、健康店 SKIP、异常店归因、五段报告、权限、取消/重试、原有聊天回归；Cron 按服务器时区验证 13:00 链路。
