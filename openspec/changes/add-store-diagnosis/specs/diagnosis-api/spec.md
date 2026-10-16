## ADDED Requirements

### Requirement: Run 创建与幂等
`POST /api/diagnosis/runs` SHALL 支持指定时间窗口与店铺集并返回 run_id；重复 client_request_id MUST 幂等返回既有 run。

#### Scenario: 幂等创建
- **WHEN** 携带相同 client_request_id 的两次创建请求
- **THEN** 返回同一 run_id，且仅创建一次

### Requirement: 查询与列表
`GET /api/diagnosis/runs` 与 `GET /api/diagnosis/runs/{run_id}` SHALL 返回 run 状态、items、阶段与失败原因；路由 MUST 具备 summary 与类型化 response_model，并在 /api/docs 可读渲染。

#### Scenario: 详情可观测
- **WHEN** 打开 run 详情接口
- **THEN** 响应包含 items 状态、stage 与失败原因

### Requirement: 取消
`POST /api/diagnosis/runs/{run_id}/cancel` SHALL 取消运行中的 run，并触发编排层终止与并发槽释放。

#### Scenario: 取消成功
- **WHEN** 对运行中 run 调用取消
- **THEN** run 终态为 CANCELLED

### Requirement: 所有权隔离
诊断 Run MUST 按 owner 隔离：非 owner 用户访问他人 run SHALL 被拒绝（不泄露存在性），admin 可查看全部。

#### Scenario: 越权访问
- **WHEN** 用户 A 访问用户 B 的 run
- **THEN** 请求被拒绝，且不返回 B 的数据
