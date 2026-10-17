## ADDED Requirements

### Requirement: 后台运行并从快照文件取数
验收运行 MUST 在后台执行，创建请求返回时运行尚未走完。快照 MUST 通过 `snapshot_store.read_store_fetch` 按店铺读取，MUST NOT 使用请求体里的快照正文。本需求不实现 :8787 数据服务。

#### Scenario: 请求不携带快照正文
- **WHEN** 创建请求给出数据目录和店铺，不把快照数字放进请求体
- **THEN** 运行从该目录的一店一文件读取快照，并且创建响应先于终态返回

### Requirement: 健康、个体、共性按既有规则分流
分流 MUST 使用已经锁定的规则：可取数指标未越阈的店是健康店并 SKIP，不调用 LLM；然后处理个体异常；再处理共性。共性比较仍是命中率 ≥40%。个体分级仍调用 `individual_priority`。黄标五项不产生数值，也不当成越阈。

分析指南分流表没有正文。本需求不发明下钻路由。环比方向没有写在快照里的指标不新造升降结论。一级派生展示值仍保持现有读取结果，不从快照现算新数字。总权重没有单独的汇总函数，本需求不新造总权重公式；排序只用已锁定的单指标权重和 `mall_check_score`。

#### Scenario: 健康店先跳过
- **WHEN** 一批里同时有健康店、只有非共性命中的店、以及共性命中的店
- **THEN** 健康店为 SKIPPED 且没有归因会话，其后才进入个体，再进入共性

### Requirement: DIAGNOSING 调用现有流程 B
DIAGNOSING MUST 调用现有 `diagnose_item`。验收里的 LLM 是假实现。假结论引用快照中不存在的数字时，现有 `contract_gate` MUST 判 FAIL，`attempt+1`，并打开新会话。流程 A 的 `llm_calls` MUST 仍是 0。

#### Scenario: 编造数字换会话
- **WHEN** 假 LLM 引用了该店快照里没有的数字
- **THEN** 该店 FAILED，attempt 增加，线程名换成新的 attempt，流程 A 的 llm_calls 仍是 0

### Requirement: 报告正文与读取接口
报告正文 MUST 含有快照中的数字、共性发现、P0/P1/P2 分组和 Top 5。章节名仍是现有五段。PARTIAL 附录仍列出 FAILED 与 SKIPPED。报告中的指标数字 MUST 能追溯到快照，不得写入假 LLM 编造的数字，也不得写入黄标五项的数值。

`GET /api/diagnosis/runs/{run_id}/report` SHALL 返回这份报告。既有创建、列表、详情、取消路径的路径字符串不改。

#### Scenario: 三店验收为 PARTIAL
- **WHEN** 同一运行包含健康店、个体异常店和编造数字的店
- **THEN** 运行终态为 PARTIAL，编造数字的店在附录中，报告里的指标数字都来自这三份快照

### Requirement: 超时和取消停掉正在跑的工作
超时与取消 MUST 停掉当时仍在执行的后台工作，而不是只改一条已经结束的状态。取消后的终态仍是 CANCELLED。超时后不再继续后续店铺。

#### Scenario: 取消正在等待的运行
- **WHEN** 运行还停在可中断的执行点时收到取消
- **THEN** 该执行点结束，运行进入 CANCELLED，并且不再诊断后面的店

#### Scenario: 超时停掉正在执行的工作
- **WHEN** 运行还停在可中断的执行点时发生超时
- **THEN** 该执行点结束，运行不再继续后续店铺
