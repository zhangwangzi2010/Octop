"""RED contracts for the promoted snapshot JSON shape and keys.

``octop.infra.diagnosis.snapshot_json`` does not exist yet. These tests fail
because that API is absent. They do not change the accepted path, metric ids,
Q4-versus-physical split, or detail tables.

Expected surface once the module exists:

- ``snapshot_shape_fields() -> Sequence[str]``
- ``store_performance_fields() -> Sequence[str]``
- ``metric_json_keys() -> Sequence[str]``
- ``metric_value_keys() -> Sequence[str]``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

from octop.infra.diagnosis.promoted_contracts import (
    drill_templates,
    q4_output_names,
    q4_physical_fields,
    second_level_metric_names,
)

SHAPE_FIELDS = ("店铺", "主体", "负责人", "store_performance")
STORE_PERFORMANCE_FIELDS = ("perf_score", "score_level", "metrics")
METRIC_JSON_KEYS = (
    "用户评价分",
    "非买家责任退货退款率",
    "延迟发货率",
    "延迟到货率",
    "缺货率",
    "24 小时回复率",
    "售后准时率",
    "爆旺款率",
    "售罄健康分",
    "活动报名率",
)


def test_snapshot_shape_uses_the_promoted_fields() -> None:
    """店铺、主体、负责人与 store_performance 同级。metrics 记 10 个键。"""
    assert _texts("snapshot_shape_fields") == SHAPE_FIELDS
    assert _texts("store_performance_fields") == STORE_PERFORMANCE_FIELDS
    assert len(_texts("metric_json_keys")) == 10


def test_score_level_stays_inside_store_performance() -> None:
    """score_level 只作为 store_performance 的形状字段。"""
    assert "score_level" in _texts("store_performance_fields")
    assert "score_level" not in _texts("snapshot_shape_fields")
    assert "score_level" not in _texts("metric_json_keys")
    assert "score_level" not in _texts("metric_value_keys")


def test_metric_json_keys_use_kickoff_spellings() -> None:
    """metrics[10] 的键用 kickoff 表格写法，回复率保留空格。"""
    assert _texts("metric_json_keys") == METRIC_JSON_KEYS


def test_reply_rate_and_refund_wording_stay_separate_keys() -> None:
    """两种回复率、两种退款用词都不并成同一个键。"""
    keys = _texts("metric_json_keys")
    whitelist = second_level_metric_names()
    triggers = [trigger for trigger, _template in drill_templates()]
    assert "24 小时回复率" in keys
    assert "24小时回复率" in whitelist
    assert "24小时回复率" not in keys
    assert "非买家责任退货退款率" in keys
    assert "非买家责任退款退货率" in triggers
    assert "非买家责任退款退货率" not in keys


def test_metric_value_keys_keep_q4_short_names() -> None:
    """指标键下是 latest、over_peers、next_level，不改写成物理列。"""
    value_keys = _texts("metric_value_keys")
    physical = tuple(name for name, _purpose in q4_physical_fields())
    assert value_keys == q4_output_names()
    assert value_keys == ("latest", "over_peers", "next_level")
    assert value_keys != physical
    assert "indicator_data_detail" not in value_keys
    assert "indicator_data_over_peers_rate" not in value_keys
    assert "indicator_data_next_level_threshold" not in value_keys


def _texts(name: str) -> tuple[str, ...]:
    value = _fn(name)()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{name} did not return the promoted strings")
    return tuple(str(item) for item in value)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.snapshot_json")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.snapshot_json is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"snapshot JSON contract is absent: {detail}")
