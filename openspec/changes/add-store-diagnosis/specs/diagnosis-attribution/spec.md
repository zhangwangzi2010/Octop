## ADDED Requirements

### Requirement: 症状分流
流程 B MUST 依据流程 A 症状分流：健康店 SKIP；个体异常与共性问题分别进入下钻；下钻能力按 analysis_guide 分流表执行，越阈指标 MUST 分流处理。

#### Scenario: 个体与共性并行
- **WHEN** 批次同时存在个体异常店与共性问题
- **THEN** 两类 item 均进入 DIAGNOSING 并受全局并发限制

### Requirement: 两段式 diagnose
单店归因 MUST 分两段：段1 确定性生成症状上下文（无 LLM，60s ×2）；段2 由诊断专家 Agent 产出归因 JSON（600s，失败 attempt+1 换会话）；结论 SHALL 遵循因果链范式（[越阈指标] → [业务后果] → [绩效影响] → [平台后果]），无数据支撑的环节 MUST 标注"待验证"。

#### Scenario: 归因结论结构
- **WHEN** 段2 成功返回
- **THEN** 结论 JSON 通过 schema 校验，且包含因果链与证据引用

### Requirement: 契约门禁与数值保真
Agent 引用的每个数字 MUST 与输入切片一致：data_refs 逐条核对失败 SHALL 判定该次执行 FAILED（不静默降级），并按重试策略换会话重试。

#### Scenario: 编造数字被拦截
- **WHEN** 结论引用了切片中不存在的数值
- **THEN** 该 item 判定 FAILED 并触发换会话重试

### Requirement: 报告五段合成
报告 MUST 按固定章节合成：〇 执行摘要 / 一 共性问题（影响度降序，⭐ 标注首要项）/ 二 特别情况店铺（P0/P1/P2 分组，单店章节取 Top5，按个体权重 ↓ → 总权重 ↓ → 绩效分 ↑ 排序）/ 三 共性店铺（绩效分升序，<3.5 高危提示）/ 四 整改优先级（影响度降序）/ 五 逐店明细；明细上限每店每类 Top10，单据级明细只在 Excel 且报告引用 sheet 名；PARTIAL 时附录 MUST 列出 FAILED / SKIPPED 清单；summarize 失败 SHALL 降级为列表拼接。

#### Scenario: PARTIAL 报告
- **WHEN** 批次中 2 家店 FAILED
- **THEN** 报告正常输出五段主体，且附录包含失败店铺清单

### Requirement: 诊断专家 Skill 资产
诊断专家 Agent MUST 加载 metrics_catalog（唯一事实源）/ analysis_guide / drilldown_playbook / query_tasks 四份资产与检查单 Skill；建议排序 SHALL 遵循权重 → 可定位 → 成本原则，且每条建议绑定数据依据。

#### Scenario: 建议绑定证据
- **WHEN** 报告输出整改建议
- **THEN** 每条建议附指标值 / 明细条数 / 时间范围依据
