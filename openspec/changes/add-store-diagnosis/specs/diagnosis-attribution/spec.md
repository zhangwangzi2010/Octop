## ADDED Requirements

### Requirement: 症状分流
流程 B MUST 依据流程 A 症状分流：健康店 SKIP；个体异常与共性问题分别进入下钻；下钻能力按 analysis_guide 分流表执行，越阈的可取数指标 MUST 分流处理。`fetchable=false` 的指标不得因为缺少数值而被当成越阈项。

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

### Requirement: 不可取数指标不得进入归因
飞书看板黄格 MUST 保持 `fetchable=false`：库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas。这五项 MUST NOT 作为归因证据或下钻对象，MUST NOT 在结论、因果链或建议中出现数值。「推广 roas」与「推广 Roas」都排除；单独的「流量异常」不代替后两项流量黄格。归因引用的环比与比率 MUST 来自症状管线快照中按周期合计口径算出的值：比率来自窗口内分子合计除以分母合计，累计指标在等长窗口使用累计值，仅累计指标在两侧天数不等时使用日均。归因 MUST NOT 改用日比率均值，也 MUST NOT 为缺失值补数。验收以飞书需求文档为准；黄标以飞书看板五项为准，环比口径绑定 2026-10-16 环比截图。架构 wiki 不把上述黄格改成可取数。

#### Scenario: 黄标不参与下钻
- **WHEN** 店铺的库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比与推广 Roas 为 SKIP，且其余可取数指标正常
- **THEN** 系统不为这五项创建归因会话，结论中不出现它们的数值

#### Scenario: 归因沿用周期合计环比
- **WHEN** 段1 组装退货率环比上下文
- **THEN** 上下文中的退货率等于对应窗口的退货订单合计除以订单合计，环比由这两个比率按 `(本期 − 上期) / 上期 × 100%` 得出
