## ADDED Requirements

### Requirement: 诊断中心入口
Dashboard SHALL 提供诊断中心页面：创建 run（时间窗口 / 店铺集）、Run 列表、详情与报告查看；前端 MUST 经 `dashboard/src/api/` 封装调用，组件禁止直连 fetch。

#### Scenario: 创建运行
- **WHEN** 用户在诊断中心提交创建
- **THEN** 列表出现新 run，且状态可刷新至终态

### Requirement: 报告与 PARTIAL 呈现
报告页 SHALL 渲染五段 markdown 结构；PARTIAL run MUST 醒目标注并展示附录失败清单。

#### Scenario: PARTIAL 标注
- **WHEN** run 终态为 PARTIAL
- **THEN** 报告页显示 PARTIAL 徽标与失败 / 跳过清单

### Requirement: 权限一致的界面表现
非 owner 用户 SHALL 不可见他人 run（与 API 隔离一致）；界面文案 MUST 走 i18n（zh / en 键同步）。

#### Scenario: 越权不可见
- **WHEN** 非 owner 打开诊断中心
- **THEN** 仅见本人 run 列表

### Requirement: 追问入口
报告页 SHALL 提供针对该诊断 run 的追问入口，会话上下文关联该 run（官方 Dashboard / IM 同一 run 线程可见）。

#### Scenario: 报告追问
- **WHEN** 用户在报告页发起追问
- **THEN** 会话携带该 run 上下文并可继续对话
