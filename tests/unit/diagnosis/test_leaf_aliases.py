"""RED: read-only aliases from checklist leaves onto locked metric names.

JSON keys stay the locked spellings. 活动覆盖率 is not 活动报名率.
缺货率 stays on the locked ten-metric rule.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from octop.infra.diagnosis.fetch_catalog import l2_leaves
from octop.infra.diagnosis.snapshot_json import metric_json_keys
from octop.infra.diagnosis.snapshot_store import two_level_fetch


def test_leaf_aliases_do_not_change_json_keys() -> None:
    """叶名只读映射到锁定名。活动覆盖率不是活动报名率。"""
    locked = _fn("locked_metric_name")
    assert locked("用户评价") == "用户评价分"
    assert locked("48小时发货率") == "延迟发货率"
    assert locked("24小时回复率") == "24 小时回复率"
    assert locked("24 小时回复率") == "24 小时回复率"
    assert locked("缺货率") == "缺货率"
    assert locked("活动报名率") == "活动报名率"
    assert locked("活动覆盖率") is None
    assert "用户评价" not in metric_json_keys()
    assert "48小时发货率" not in metric_json_keys()
    assert "24小时回复率" not in metric_json_keys()
    assert "缺货率" in metric_json_keys()
    assert "活动报名率" in metric_json_keys()
    assert ("店铺绩效", "缺货率") not in l2_leaves()


def test_level2_reads_aliased_leaves_from_locked_keys() -> None:
    """检查单叶名读到锁定键上的 latest，键本身不改写。"""
    fetched = two_level_fetch(_document())
    by_leaf = {(item["group"], item["name"]): item for item in _items(fetched["level2"])}
    review = by_leaf[("店铺绩效", "用户评价")]
    assert review["name"] == "用户评价"
    assert review["value"] == 4.25
    ship = by_leaf[("店铺绩效", "48小时发货率")]
    assert ship["value"] == 0.1
    reply = by_leaf[("店铺绩效", "24小时回复率")]
    assert reply["value"] == 0.8
    coverage = by_leaf[("店铺运营", "活动覆盖率")]
    assert coverage["queried"] is False
    assert coverage["value"] is None
    keys = set(_document()["store_performance"]["metrics"])
    assert "用户评价" not in keys
    assert "48小时发货率" not in keys
    assert "24小时回复率" not in keys
    assert "24 小时回复率" in keys
    assert "活动报名率" in keys


def _document() -> dict[str, Any]:
    metrics = {
        key: {"latest": None, "over_peers": None, "next_level": None} for key in metric_json_keys()
    }
    metrics["用户评价分"] = {"latest": 4.25, "over_peers": None, "next_level": None}
    metrics["延迟发货率"] = {"latest": 0.1, "over_peers": None, "next_level": None}
    metrics["24 小时回复率"] = {"latest": 0.8, "over_peers": None, "next_level": None}
    metrics["活动报名率"] = {"latest": 0.95, "over_peers": None, "next_level": None}
    metrics["缺货率"] = {"latest": 0.2, "over_peers": None, "next_level": None}
    return {
        "店铺": "一店",
        "主体": "主体甲",
        "负责人": "负责人甲",
        "store_performance": {
            "mall_check_score": 4.1,
            "perf_score": 3.8,
            "score_level": "正常",
            "metrics": metrics,
        },
    }


def _items(value: object) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        pytest.fail("level2 did not return items")
    return tuple(item for item in value if isinstance(item, Mapping))


def _fn(name: str) -> Any:
    module = importlib.import_module("octop.infra.diagnosis.hit_weights")
    function = getattr(module, name, None)
    if not callable(function):
        pytest.fail(f"{name} is not implemented")
    return function
