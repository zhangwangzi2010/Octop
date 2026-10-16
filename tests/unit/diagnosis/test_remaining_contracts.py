"""RED contracts for the remaining promoted rules and unresolved gaps.

``octop.infra.diagnosis.remaining_contracts`` does not exist yet. These tests
fail because that API is absent. They do not invent strategy metric names,
fulfillment column names, or after-sales class names.

Expected surface once the module exists:

- ``hit_annotation_rule() -> str``
- ``grade_statements() -> Sequence[str]``
- ``snapshot_path_template() -> str``
- ``snapshot_has_version_segment() -> bool``
- ``after_sales_merge_rules() -> Sequence[str]``
- ``run_slice_contract() -> Sequence[str]``
- ``interpretation_contract() -> Sequence[str]``
- ``batch_report_contract() -> Sequence[str]``
- ``data_ref_words() -> Sequence[str]``
- ``q4_short_names() -> Sequence[str]``
- ``is_alias(left, right) -> bool``
- ``chosen_ratio_scale() -> str`` — ``0~1``
- ``ratio_display_multiplier() -> int`` — ``100``
- ``score_passthrough_metrics() -> Sequence[str]``
- ``chosen_threshold_set() -> Sequence[str]``
- ``threshold_notes() -> Sequence[str]``
- ``chosen_score_field() -> str`` — ``mall_check_score``
- ``score_field_alias() -> str`` — ``perf_score``
- ``chosen_detail_limit() -> str``
- ``top10_is_hard_cap() -> bool``
- ``top10_reference_n() -> int``
- ``ratio_scale_statements()`` keeps the accepted 0~1 sentences
- ``ratio_scale_notes()`` keeps §3.4「比率 0~100」 and the semantic-layer sentence
- ``threshold_statements()`` keeps source A only
- ``detail_limit_statements()`` keeps the default Top N sentence
- ``detail_limit_notes()`` keeps the kickoff Top 10 sentence
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

from octop.infra.diagnosis.snapshot_json import metric_value_keys

HIT_ANNOTATION_RULE = "命中标注运行时按 thresholds.json 计算"
GRADE_STATEMENTS = (
    "≥4.3 优秀，≥4 正常，≥3.5 低危，<3.5 高危",
    "<3.5 高危 / 3.5~4 低危 / 4~4.3 正常 / ≥4.3 优秀。店铺维度用店铺绩效分，主体维度用主体平均分。",
)
SNAPSHOT_PATH_TEMPLATE = "{data_dir}/{shop_id}.json"
AFTER_SALES_MERGE_RULES = (
    "售后原因先按英文逗号拆分，再归并为固定 6 大类；映射表必须作为受控资产，不能由模型推断。",
    "售后 26 原因 → 6 大类。",
)
RUN_SLICE_CONTRACT = (
    "workspace diagnosis/<item_id>/checklists/<checklist>.json",
    "单店单检查单；追加 grade / individual_* / common_issues / metrics[].hit|is_common",
)
INTERPRETATION_CONTRACT = (
    "headline / overall / findings[{title,severity,analysis,evidence[],data_refs[]}] / actions[{title,detail,priority?,owner_hint?}] / risks[]",
    "perf_score",
    "metrics.<指标名|key>.<latest|prev|weight>",
    "label 与英文 key 双匹配",
    "value 必须与切片一致",
)
BATCH_REPORT_CONTRACT = (
    "mode(single|multi)",
    "coverage",
    "common_issues[]（影响度降序）",
    "priority[]（P0→P1→P2→共性）",
    "stores[]",
    "概览/共性问题/店铺明细=症状+归因/行动建议/附录 FAIL·SKIPPED",
)
DATA_REF_WORDS = ("latest", "prev", "weight")
Q4_SHORT_NAMES = ("latest", "over_peers", "next_level")
CHOSEN_RATIO_SCALE = "0~1"
RATIO_DISPLAY_MULTIPLIER = 100
SCORE_PASSTHROUGH_METRICS = ("用户评价分", "售罄健康分")
ACCEPTANCE_THRESHOLDS = ("C-S09 ≥10%", "C-S12 <90%", "C-S13 <95%")
THRESHOLD_NOTES = (
    "C-S09 ≥2%（超同行 70%）",
    "C-S12 <100%",
    "C-S13 <100%",
    "C-S09 ≥2%、C-S12 <90%、C-S13 <95%",
)
CANONICAL_SCORE_FIELD = "mall_check_score"
SCORE_FIELD_ALIAS = "perf_score"
CHOSEN_DETAIL_LIMIT = "默认 Top N + 完整进附件"
TOP10_REFERENCE_N = 10
RATIO_SCALE_STATEMENTS = (
    "用户评价分 / 售罄健康分为分值、直通；其余 8 项比率指标为比例（0~1），×100 后再判定/展示；over_peers_rate / next_level_threshold 同指标量纲、同指标规则。",
    "除用户评价分、售罄健康分为分值外，8 项比率指标源表为 0~1 比例，展示需 ×100。",
)
RATIO_SCALE_NOTES = (
    "文件只存原始值（比率 0~100）。",
    "比率类源值通常为 0~1，展示与判定统一换算为百分比；只有延迟发货率在语义层显式标注 scale 时也要全指标统一应用实测口径。",
)
THRESHOLD_SOURCE_A = (
    "延迟发货率 (C-S09) 来源 A ≥ 10%",
    "24h 回复率 (C-S12) 来源 A < 90%",
    "售后准时率 (C-S13) 来源 A < 95%",
)
DETAIL_LIMIT_STATEMENTS = ("明细默认 Top N，完整单据只进 Excel/附件，不进入 LLM 上下文。",)
DETAIL_LIMIT_NOTES = (
    "单据级明细只在 Excel（每店铺每类 Top 10）；报告正文只写结论 + 占比。同节另写 4 区块 × Top 10。",
)
_UNSELECTED_DOCSTRINGS = (
    "Neither is selected",
    "Neither count is selected",
    "Both threshold columns",
    "Unresolved gaps stay unchosen",
    "does not pick a ratio scale",
)


def test_hit_annotation_uses_thresholds_json() -> None:
    """命中标注运行时按 thresholds.json 计算。"""
    assert _fn("hit_annotation_rule")() == HIT_ANNOTATION_RULE


def test_grade_bands_keep_both_source_wordings() -> None:
    """两处等级原文都保留，不收成一套切分。"""
    statements = _texts("grade_statements")
    assert statements == GRADE_STATEMENTS
    assert statements[0] != statements[1]
    combined = " ".join(statements)
    for label in ("高危", "低危", "正常", "优秀"):
        assert label in combined
    assert "3.5" in combined
    assert "4.3" in combined
    assert "≥4" in statements[0]
    assert "4~4.3" in statements[1]


def test_snapshot_path_has_no_version_segment() -> None:
    """路径仍是 {data_dir}/{shop_id}.json，没有版本段。"""
    template = _fn("snapshot_path_template")()
    assert template == SNAPSHOT_PATH_TEMPLATE
    assert template.split("/") == ["{data_dir}", "{shop_id}.json"]
    assert _fn("snapshot_has_version_segment")() is False


def test_after_sales_merge_rule_keeps_the_source_sentences() -> None:
    """只登记归并规则。不列出六个类名。"""
    rules = _texts("after_sales_merge_rules")
    assert rules == AFTER_SALES_MERGE_RULES
    combined = " ".join(rules)
    assert "英文逗号拆分" in combined
    assert "固定 6 大类" in combined
    assert "26 原因 → 6 大类" in combined
    assert "映射表必须作为受控资产" in combined


def test_section_34_shapes_keep_the_source_text() -> None:
    """run 切片、interpretation、批次报告按原文登记。"""
    assert _texts("run_slice_contract") == RUN_SLICE_CONTRACT
    assert _texts("interpretation_contract") == INTERPRETATION_CONTRACT
    assert _texts("batch_report_contract") == BATCH_REPORT_CONTRACT


def test_prev_and_weight_are_not_aliases() -> None:
    """prev 不是 over_peers 的别名，weight 不是 next_level 的别名。"""
    alias = _fn("is_alias")
    assert _texts("data_ref_words") == DATA_REF_WORDS
    assert _texts("q4_short_names") == Q4_SHORT_NAMES
    assert alias("prev", "over_peers") is False
    assert alias("weight", "next_level") is False
    assert metric_value_keys() == Q4_SHORT_NAMES
    assert "prev" not in metric_value_keys()
    assert "weight" not in metric_value_keys()


def test_ratio_scale_stores_zero_to_one_and_displays_times_100() -> None:
    """内部保存 0~1。展示和判定 ×100。两个分值直通。"""
    assert _fn("chosen_ratio_scale")() == CHOSEN_RATIO_SCALE
    assert _fn("ratio_display_multiplier")() == RATIO_DISPLAY_MULTIPLIER
    assert _texts("score_passthrough_metrics") == SCORE_PASSTHROUGH_METRICS
    assert _fn("chosen_ratio_scale")() != "0~100"


def test_threshold_acceptance_is_source_a_only() -> None:
    """验收只有 ≥10% / <90% / <95%。来源 B 和旧症状列只是注记。"""
    chosen = _fn("chosen_threshold_set")()
    assert chosen == ACCEPTANCE_THRESHOLDS
    notes = _texts("threshold_notes")
    assert notes == THRESHOLD_NOTES
    assert "C-S09 ≥2%" not in chosen
    assert "<100%" not in chosen
    assert "C-S09 ≥2%、C-S12 <90%、C-S13 <95%" not in chosen


def test_mall_check_score_is_the_canonical_field() -> None:
    """规范名是 mall_check_score。perf_score 是别名 / 旧键。"""
    assert _fn("chosen_score_field")() == CANONICAL_SCORE_FIELD
    assert _fn("score_field_alias")() == SCORE_FIELD_ALIAS
    assert _fn("chosen_score_field")() != SCORE_FIELD_ALIAS


def test_detail_limit_is_default_top_n_plus_attachments() -> None:
    """验收是默认 Top N 加完整进附件。Top 10 不是写死上限。"""
    assert _fn("chosen_detail_limit")() == CHOSEN_DETAIL_LIMIT
    assert _fn("top10_is_hard_cap")() is False
    assert _fn("top10_reference_n")() == TOP10_REFERENCE_N


def test_statement_functions_keep_only_the_accepted_wording() -> None:
    """语句函数不再把落选口径和验收常量并列。落选句只留在注记。"""
    ratio = _texts("ratio_scale_statements")
    thresholds = _texts("threshold_statements")
    details = _texts("detail_limit_statements")
    ratio_blob = "\n".join(ratio)
    threshold_blob = "\n".join(thresholds)
    detail_blob = "\n".join(details)
    assert "比率 0~100" not in ratio_blob
    assert "语义层" not in ratio_blob
    assert "来源 B" not in threshold_blob
    assert "C-S09 ≥2%" not in threshold_blob
    assert "< 100%" not in threshold_blob
    assert "C-S09 ≥2%、C-S12 <90%、C-S13 <95%" not in threshold_blob
    assert "Top 10" not in detail_blob
    assert ratio == RATIO_SCALE_STATEMENTS
    assert thresholds == THRESHOLD_SOURCE_A
    assert details == DETAIL_LIMIT_STATEMENTS
    ratio_notes = _texts("ratio_scale_notes")
    detail_notes = _texts("detail_limit_notes")
    assert ratio_notes == RATIO_SCALE_NOTES
    assert detail_notes == DETAIL_LIMIT_NOTES
    assert "比率 0~100" in "\n".join(ratio_notes)
    assert "语义层" in "\n".join(ratio_notes)
    assert "Top 10" in "\n".join(detail_notes)
    assert _fn("chosen_ratio_scale")() == CHOSEN_RATIO_SCALE
    assert "语义层" not in _fn("chosen_ratio_scale")()
    assert _texts("threshold_notes") == THRESHOLD_NOTES
    assert _fn("score_fields_are_same")() is False
    assert _fn("is_alias")("prev", "over_peers") is False
    assert _fn("is_alias")("weight", "next_level") is False


def test_statement_docstrings_do_not_call_the_choice_unselected() -> None:
    """说明不再写比率、阈值列或明细条数尚未选取。"""
    module = _module()
    docs = [module.__doc__ or ""]
    for name in (
        "ratio_scale_statements",
        "threshold_statements",
        "detail_limit_statements",
    ):
        docs.append(_fn(name).__doc__ or "")
    combined = "\n".join(docs)
    for phrase in _UNSELECTED_DOCSTRINGS:
        assert phrase not in combined


def _texts(name: str) -> tuple[str, ...]:
    value = _fn(name)()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{name} did not return the recorded statements")
    return tuple(str(item) for item in value)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.remaining_contracts")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.remaining_contracts is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"remaining contracts are absent: {detail}")
