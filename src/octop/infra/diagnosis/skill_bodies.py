"""Diagnosis skill text and the expert package that stores it.

The strings come from the locked diagnosis constants. ``analysis_guide`` is
copied, not rewritten. This module does not add formulas, SQL, or service
addresses.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from octop.infra.diagnosis.flow_b import (
    analysis_guide_body,
    diagnose_item,
    drill_route,
    load_skills,
    soul_steps,
    undrillable_mark,
    unverified_mark,
)
from octop.infra.diagnosis.hit_weights import (
    after_sales_class_names,
    common_mark_percent,
    document_denominator,
    document_numerator,
    hit_rule,
    locked_metric_name,
    metric_ids,
    metric_name,
    metric_weight_percent,
)
from octop.infra.diagnosis.l1_semantic import age_bands, yellow_gap_mark, yellow_metric_names
from octop.infra.diagnosis.promoted_contracts import (
    detail_tables,
    drill_templates,
    kickoff_metric_ids,
    performance_score_ids,
    q4_column_labels,
    q4_output_names,
    q4_physical_fields,
)
from octop.infra.diagnosis.remaining_contracts import (
    chosen_detail_limit,
    chosen_ratio_scale,
    chosen_score_field,
    grade_statements,
    ratio_display_multiplier,
    score_field_alias,
    score_passthrough_metrics,
    snapshot_path_template,
)
from octop.infra.diagnosis.snapshot_store import (
    fulfillment_has_business_date,
    fulfillment_side_keys,
    fulfillment_time_fields,
)
from octop.infra.diagnosis.snapshot_structure import q3_window, query_names
from octop.infra.utils.frontmatter import parse_frontmatter

_EXPERT_ID = "store-diagnosis"
_SKILL_NAMES: tuple[str, ...] = (
    "metrics_catalog",
    "analysis_guide",
    "drilldown_playbook",
    "query_tasks",
)
_DESCRIPTIONS: dict[str, str] = {
    "metrics_catalog": "店铺诊断指标清单与已锁定阈值。本资产是唯一事实源。",
    "analysis_guide": "店铺诊断下钻分流表。阈值和权重用已锁定命中线。",
    "drilldown_playbook": "店铺诊断下钻手册。分流以 analysis_guide 为准，不另写命中线。",
    "query_tasks": "店铺诊断 Q1 到 Q5 查询任务。不写 SQL。",
}
_LEAF_INPUTS: tuple[str, ...] = ("用户评价", "48小时发货率", "24小时回复率")
_DRILLABLE: tuple[str, ...] = ("绩效分", "C-S07", "C-S08", "C-S09", "C-S10")
_UNDRILLABLE: tuple[str, ...] = ("C-S11", "C-S12", "C-S13", "C-S14", "C-S15", "C-S16")
_Q3_SAMPLE_DAY = date(2026, 1, 1)


def expert_id() -> str:
    """Bundled expert id for the diagnosis ontology."""
    return _EXPERT_ID


def expert_root() -> Path:
    """On-disk expert package. Skill files and ``SOUL.md`` live here."""
    return Path(__file__).resolve().parents[1] / "agents" / "experts" / "library" / _EXPERT_ID


def render_skill_body(name: str) -> str:
    """Body for one skill. ``analysis_guide`` is the existing routing table."""
    if name == "metrics_catalog":
        return _metrics_catalog()
    if name == "analysis_guide":
        return analysis_guide_body()
    if name == "drilldown_playbook":
        return _drilldown()
    if name == "query_tasks":
        return _query_tasks()
    raise KeyError(name)


def render_skill_file(name: str) -> str:
    """Skill file text. The body below the frontmatter is the loaded body."""
    if name not in _DESCRIPTIONS:
        raise KeyError(name)
    body = render_skill_body(name)
    description = _DESCRIPTIONS[name]
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"


def render_soul() -> str:
    """SOUL text. The five steps are the locked inline workflow."""
    lines = [
        "# 店铺诊断专家",
        "",
        "五步是已批准的 SOUL 内联工作流，不是 Skill。流程 A 保持零 LLM。",
        "metrics_catalog 是唯一事实源。下钻分流以 analysis_guide 为准，不另写命中线。",
        "四份 Skill：metrics_catalog、analysis_guide、drilldown_playbook、query_tasks。",
        "建议排序：权重 → 可定位 → 成本。每条建议绑定数据依据。",
        f"无数据支撑的因果环节标注{unverified_mark()}。",
        "",
        *soul_steps(),
    ]
    return "\n".join(lines) + "\n"


def read_skill_body(name: str) -> str:
    """Read one skill body from the expert package."""
    text = _skill_path(name).read_text(encoding="utf-8")
    _meta, body = parse_frontmatter(text)
    return body.strip("\n")


def read_soul() -> str:
    """Read the diagnosis expert SOUL."""
    return (expert_root() / "SOUL.md").read_text(encoding="utf-8")


def diagnose_with_expert(
    *,
    run_id: str,
    store_id: str,
    attempt: int,
    slice_values: Sequence[object],
    llm: Callable[[Mapping[str, Any]], Any],
    prior_threads: Sequence[str] = (),
    metrics: Sequence[str] = (),
) -> dict[str, Any]:
    """Inject SOUL and the four skills, then run the existing interpretation."""
    packet: dict[str, Any] = {
        "expert_id": expert_id(),
        "soul": read_soul(),
        "steps": soul_steps(),
        "skills": load_skills(),
    }

    def _call() -> Any:
        return llm(packet)

    return diagnose_item(
        run_id=run_id,
        store_id=store_id,
        attempt=attempt,
        conclusion=None,
        slice_values=slice_values,
        prior_threads=prior_threads,
        metrics=metrics,
        llm=_call,
    )


def _metrics_catalog() -> str:
    lines = [
        "metrics_catalog。唯一事实源。阈值和权重用已锁定常量。",
        f"量纲 {chosen_ratio_scale()}，展示与判定乘 {ratio_display_multiplier()}。",
        "分值直通 " + "、".join(score_passthrough_metrics()) + "。",
        f"绩效分规范名 {chosen_score_field()}。",
        f"绩效分别名 {score_field_alias()} 不是同一个字段。",
        "绩效分语义 " + "、".join(performance_score_ids()) + "。",
        f"共性阈值 {common_mark_percent()}%。",
        "环比方向正号为上升，负号为下降。",
        "影响度等于权重乘以命中率。",
    ]
    lines.extend(grade_statements())
    for metric_id in metric_ids():
        weight = metric_weight_percent(metric_id)
        lines.append(
            f"{metric_id} {metric_name(metric_id)} 权重 {weight:g}% 命中 {hit_rule(metric_id)}"
        )
    for display, semantic in kickoff_metric_ids():
        lines.append(f"语义 {display} {semantic}")
    lines.append("叶名只读别名，JSON 键不改。")
    for alias in _LEAF_INPUTS:
        locked = locked_metric_name(alias)
        if locked is not None:
            lines.append(f"叶名 {alias} → {locked}")
    yellow = "、".join(yellow_metric_names())
    lines.append(f"黄标不取数 {yellow}。{yellow_gap_mark()}。")
    lines.append("商品策略额外指标名为空。")
    lines.append("履约 139 列为空。")
    lines.append("售龄四档 " + "、".join(age_bands()) + "。")
    lines.append("TOP X 的 X 与无公式一级不在本资产补公式。")
    return "\n".join(lines)


def _drilldown() -> str:
    lines = [
        "drilldown_playbook。下钻分流以 analysis_guide 为准，不另写命中线。",
        "不内嵌查询语句，不写外部服务地址。",
        chosen_detail_limit() + "。",
    ]
    for name in _DRILLABLE:
        lines.append(f"可下钻 {name} 路由 {drill_route(name)}")
    for metric_id in _UNDRILLABLE:
        lines.append(f"不可下钻 {metric_id} {undrillable_mark(metric_id)}")
    for label, table in detail_tables():
        lines.append(f"明细 {label} {table}")
    for trigger, kind in drill_templates():
        lines.append(f"触发 {trigger} → {kind}")
    lines.append("售后类名 " + "、".join(after_sales_class_names()) + "。")
    lines.append("9-未分类不进入类名。")
    for metric_id in ("C-S09", "C-S10"):
        numerator = document_numerator(metric_id)
        denominator = document_denominator(metric_id)
        lines.append(f"{metric_id} 单据分子 {numerator} 分母 {denominator}")
    lines.append("履约侧键 " + "、".join(fulfillment_side_keys()) + "。")
    lines.append("履约时间 " + "、".join(fulfillment_time_fields()) + "。")
    if not fulfillment_has_business_date():
        lines.append("履约表没有 business_date。")
    lines.append("履约 139 列为空。")
    lines.append("商品策略额外指标名为空。")
    lines.append("分流表复用 analysis_guide：")
    lines.append(analysis_guide_body())
    return "\n".join(lines)


def _query_tasks() -> str:
    lines = [
        "query_tasks。Q1 到 Q5 用已锁定名称。不写 SQL。",
        *query_names(),
        f"Q3 窗口天数 {len(q3_window(_Q3_SAMPLE_DAY))}。不含今天。",
        "Q4 输出 " + "、".join(q4_output_names()) + "。",
        "Q4 列 " + "、".join(q4_column_labels()) + "。",
    ]
    for field, purpose in q4_physical_fields():
        lines.append(f"Q4 字段 {field} {purpose}")
    lines.append(f"快照 {snapshot_path_template()}。无版本段。")
    lines.append(
        "预加载在 COMPLETED 且 row_count > 0 时消费。RUNNING 不重复灌数。FAILED 可以重试。"
    )
    return "\n".join(lines)


def _skill_path(name: str) -> Path:
    if name not in _SKILL_NAMES:
        raise KeyError(name)
    return expert_root() / "skills" / name / "SKILL.md"
