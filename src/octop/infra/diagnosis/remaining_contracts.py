"""Recorded remaining contract text. Unresolved gaps stay unchosen.

This module does not pick a ratio scale or a threshold column, and it does
not list strategy metrics, fulfillment columns, or after-sales class names.
"""

from __future__ import annotations

_GRADE_STATEMENTS: tuple[str, ...] = (
    "≥4.3 优秀，≥4 正常，≥3.5 低危，<3.5 高危",
    "<3.5 高危 / 3.5~4 低危 / 4~4.3 正常 / ≥4.3 优秀。店铺维度用店铺绩效分，主体维度用主体平均分。",
)
_AFTER_SALES_MERGE_RULES: tuple[str, ...] = (
    "售后原因先按英文逗号拆分，再归并为固定 6 大类；映射表必须作为受控资产，不能由模型推断。",
    "售后 26 原因 → 6 大类。",
)
_RUN_SLICE_CONTRACT: tuple[str, ...] = (
    "workspace diagnosis/<item_id>/checklists/<checklist>.json",
    "单店单检查单；追加 grade / individual_* / common_issues / metrics[].hit|is_common",
)
_INTERPRETATION_CONTRACT: tuple[str, ...] = (
    "headline / overall / findings[{title,severity,analysis,evidence[],data_refs[]}] / actions[{title,detail,priority?,owner_hint?}] / risks[]",
    "perf_score",
    "metrics.<指标名|key>.<latest|prev|weight>",
    "label 与英文 key 双匹配",
    "value 必须与切片一致",
)
_BATCH_REPORT_CONTRACT: tuple[str, ...] = (
    "mode(single|multi)",
    "coverage",
    "common_issues[]（影响度降序）",
    "priority[]（P0→P1→P2→共性）",
    "stores[]",
    "概览/共性问题/店铺明细=症状+归因/行动建议/附录 FAIL·SKIPPED",
)
_DATA_REF_WORDS: tuple[str, ...] = ("latest", "prev", "weight")
_Q4_SHORT_NAMES: tuple[str, ...] = ("latest", "over_peers", "next_level")
_RATIO_SCALE_STATEMENTS: tuple[str, ...] = (
    "文件只存原始值（比率 0~100）。",
    "用户评价分 / 售罄健康分为分值、直通；其余 8 项比率指标为比例（0~1），×100 后再判定/展示；over_peers_rate / next_level_threshold 同指标量纲、同指标规则。",
    "除用户评价分、售罄健康分为分值外，8 项比率指标源表为 0~1 比例，展示需 ×100。",
    "比率类源值通常为 0~1，展示与判定统一换算为百分比；只有延迟发货率在语义层显式标注 scale 时也要全指标统一应用实测口径。",
)
_THRESHOLD_STATEMENTS: tuple[str, ...] = (
    "延迟发货率 (C-S09) 来源 A ≥ 10%；来源 B ≥ 2%（超同行 70%）",
    "24h 回复率 (C-S12) 来源 A < 90%；来源 B < 100%",
    "售后准时率 (C-S13) 来源 A < 95%；来源 B < 100%",
    "C-S09 ≥2%、C-S12 <90%、C-S13 <95%",
)
_SCORE_FIELD_NAMES: tuple[str, ...] = ("mall_check_score", "perf_score")
_DETAIL_LIMIT_STATEMENTS: tuple[str, ...] = (
    "单据级明细只在 Excel（每店铺每类 Top 10）；报告正文只写结论 + 占比。同节另写 4 区块 × Top 10。",
    "明细默认 Top N，完整单据只进 Excel/附件，不进入 LLM 上下文。",
)


def hit_annotation_rule() -> str:
    """Hit marks are computed at runtime from thresholds.json."""
    return "命中标注运行时按 thresholds.json 计算"


def grade_statements() -> tuple[str, ...]:
    """Both grade wordings. They are not collapsed into one boundary table."""
    return _GRADE_STATEMENTS


def snapshot_path_template() -> str:
    """The snapshot path template. It has no version segment."""
    return "{data_dir}/{shop_id}.json"


def snapshot_has_version_segment() -> bool:
    """The promoted path does not include a version segment."""
    return False


def after_sales_merge_rules() -> tuple[str, ...]:
    """Merge rules only. Class names are not listed."""
    return _AFTER_SALES_MERGE_RULES


def run_slice_contract() -> tuple[str, ...]:
    """Run-slice path and the fields the source appends."""
    return _RUN_SLICE_CONTRACT


def interpretation_contract() -> tuple[str, ...]:
    """Interpretation shape text, including the data_refs pattern."""
    return _INTERPRETATION_CONTRACT


def batch_report_contract() -> tuple[str, ...]:
    """Batch-report shape text and the five section names."""
    return _BATCH_REPORT_CONTRACT


def data_ref_words() -> tuple[str, ...]:
    """Words in the data_refs pattern. They are not the Q4 short names."""
    return _DATA_REF_WORDS


def q4_short_names() -> tuple[str, ...]:
    """Q4 short names. ``prev`` and ``weight`` are not in this tuple."""
    return _Q4_SHORT_NAMES


def is_alias(left: str, right: str) -> bool:
    """No promoted pair is an alias. ``prev`` is not ``over_peers``."""
    del left, right
    return False


def ratio_scale_statements() -> tuple[str, ...]:
    """Both scale sentences. Neither is selected."""
    return _RATIO_SCALE_STATEMENTS


def chosen_ratio_scale() -> None:
    """No single ratio scale is chosen."""
    return None


def threshold_statements() -> tuple[str, ...]:
    """Both threshold columns and the symptom-spec sentence."""
    return _THRESHOLD_STATEMENTS


def chosen_threshold_set() -> None:
    """No single C-S threshold column is chosen."""
    return None


def score_field_names() -> tuple[str, ...]:
    """Both score field names. They stay separate."""
    return _SCORE_FIELD_NAMES


def chosen_score_field() -> None:
    """Neither score field name is selected as the only one."""
    return None


def score_fields_are_same() -> bool:
    """``mall_check_score`` and ``perf_score`` are not the same field."""
    return False


def detail_limit_statements() -> tuple[str, ...]:
    """Both detail-limit sentences. Neither count is selected."""
    return _DETAIL_LIMIT_STATEMENTS


def chosen_detail_limit() -> None:
    """No single detail-row limit is chosen."""
    return None
