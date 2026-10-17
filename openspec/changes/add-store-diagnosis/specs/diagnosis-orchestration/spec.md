## ADDED Requirements

### Requirement: Run 五阶段状态机
诊断 Run SHALL 遵循 PREPARING → ANALYZING → DIAGNOSING → COMPLETING → 终态（COMPLETED / PARTIAL / FAILED / CANCELLED）的单向状态机；Item SHALL 遵循 PENDING → PREPARING → DIAGNOSING → OK / FAILED / SKIPPED。非法状态迁移 MUST 被拒绝并记录节点事件。

#### Scenario: 正常推进
- **WHEN** 流程 A 症状管线全部节点成功
- **THEN** Run 依次经过 PREPARING、ANALYZING、COMPLETING 后进入 COMPLETED

#### Scenario: 部分店铺失败
- **WHEN** 批次中存在 item FAILED 且其余成功
- **THEN** Run 终态为 PARTIAL，且报告附录包含失败清单

### Requirement: 提交幂等
创建 Run MUST 以 client_request_id 唯一约束去重：重复提交 SHALL 返回既有 Run，不产生新 Run 或重复 items。

#### Scenario: 重复提交
- **WHEN** 携带同一 client_request_id 的创建请求被提交两次
- **THEN** 两次响应指向同一 run_id，且 diag_runs 中仅有一条记录

### Requirement: 执行认领幂等与重试换会话
Item 执行 MUST 以 (run_id, store_id, attempt) 唯一认领（条件更新）；diagnose 段2 失败重试 SHALL 以 attempt+1 更换会话（thread 命名 diag:{run_id}:{store_id}:a{attempt}），旧会话留痕不删除。

#### Scenario: 归因重试
- **WHEN** 段2 stream 失败或结论 JSON 校验不通过
- **THEN** 系统以 attempt+1 新会话重试，且旧 thread 保留可追溯

### Requirement: 断点恢复
进程启动时 MUST 调用 reset_orphan_items 将孤儿运行中 item 复位并自动续跑；恢复过程 SHALL 幂等、可重复执行。

#### Scenario: 崩溃后续跑
- **WHEN** 进程在 DIAGNOSING 阶段崩溃后重启
- **THEN** 孤儿 item 被复位并继续执行，终态与事件流水完整

### Requirement: 取消与并发
Run 在任意阶段 MUST 可被取消：取消 SHALL 置 CANCELLED、释放并发槽并终止在途执行；归因并发 MUST 由可配置 Semaphore（默认 3~5）限制，纯数据节点不占用归因并发槽。

#### Scenario: 取消运行中批次
- **WHEN** 用户对 DIAGNOSING 中的 run 发起取消
- **THEN** run 与未完成 items 进入 CANCELLED，且在途会话被终止

### Requirement: 节点事件审计
每个节点 MUST 写入 diag_node_events（开始/结束/耗时/重试/失败原因），支持按 run_id 完整对账。

#### Scenario: 失败对账
- **WHEN** 某节点超时重试后仍失败
- **THEN** 事件流水包含每次尝试的耗时与失败原因
