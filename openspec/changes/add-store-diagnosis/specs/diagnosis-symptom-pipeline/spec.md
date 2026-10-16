## ADDED Requirements

### Requirement: 定时触发与数据就绪
系统 SHALL 支持每日 13:00 Cron 触发流程 A；ensure_data_ready MUST 轮询数据就绪（30 分钟超时 ×3），最终失败置 FAILED 并落事件。

#### Scenario: 数据未就绪
- **WHEN** 轮询超过 30 分钟 ×3 仍无数据
- **THEN** run 进入 FAILED，事件流水记录失败原因

### Requirement: 快照与可重放
取数结果 MUST 按一店一文件快照（schema v2）落库，周期解析由确定性代码完成；相同输入 SHALL 产出一致的症状结论，报告与图表数字 MUST 只来自快照原文。

#### Scenario: 同输入重放
- **WHEN** 对同一快照重复执行症状规则引擎
- **THEN** 输出的症状结论完全一致

### Requirement: 阈值规则引擎
症状判定 MUST 全部代码化：10 项二级指标的阈值命中、环比、共性标记（命中率 ≥40%）、个体分级（P0：个体权重 ≥30% 或绩效分 <3.5；P1：15%~30%；P2：<15%）与影响度（权重 × 命中率）排序 SHALL 与手算一致；阈值 MUST 配置化（thresholds.json），冲突项以影响文档为准（C-S09 ≥2%、C-S12 <90%、C-S13 <95%）。

#### Scenario: 阈值命中判定
- **WHEN** 某店延迟发货率为 12.5%（阈值 ≥2%）
- **THEN** 该指标命中异常，并按权重与命中率参与影响度排序

#### Scenario: 阈值调整不改框架
- **WHEN** thresholds.json 调整某指标阈值
- **THEN** 无需修改框架代码即可生效

### Requirement: 健康店分流
症状正常的店铺 MUST 被标记 SKIPPED，不进入流程 B 归因下钻。

#### Scenario: 健康店不做工
- **WHEN** 某店全部指标未越阈
- **THEN** 该店 item 为 SKIPPED 且不创建归因会话

### Requirement: Q1~Q5 查询口径
取数 MUST 覆盖 Q1 主体汇总 / Q2 店铺快照 / Q3 近 60 天评分趋势 / Q4 二级指标快照 / Q5 三个月指标趋势；时间口径（最新分区、不含今天、最近 60 天 / 3 个月）与展示形态 SHALL 符合数据契约。

#### Scenario: 趋势窗口
- **WHEN** 执行 Q3 查询
- **THEN** 返回最近 60 天（不含今天）的日粒度评分趋势
