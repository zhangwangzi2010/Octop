"""RED contracts for snapshot structure already stated by the specs.

``octop.infra.diagnosis.snapshot_structure`` does not exist yet. These tests
fail because that module is absent. They do not assert JSON keys, SQL columns,
file-path templates, ratio scales, or metric names under 商品策略结构.

Expected surface once the module exists:

- ``snapshot_file_for_store(store_id) -> object`` — one opaque file identity per store
- ``parse_period(label, *, today) -> object`` — deterministic period parse
- ``q3_window(today) -> Sequence[date]`` — sixty daily dates, excluding today
- ``symptom_conclusion(snapshot_text) -> str`` — same text in, same conclusion out
- ``query_names() -> Sequence[str]`` — the five Q1–Q5 display names
- ``preload_consumable(status, row_count) -> bool``
- ``preload_refill_allowed(status) -> bool``
- ``preload_retry_allowed(status) -> bool``
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, NoReturn

import pytest

QUERY_NAMES = (
    "Q1 主体汇总",
    "Q2 店铺快照",
    "Q3 近 60 天评分趋势",
    "Q4 二级指标快照",
    "Q5 三个月指标趋势",
)
PERIOD_LABELS = (
    "最新分区",
    "最近 60 天（不含今天）",
    "3 个月",
)
_NUMBER = re.compile(r"(?<![A-Za-z0-9.])\d+(?:\.\d+)?(?![A-Za-z0-9.])")


def test_one_store_maps_to_one_snapshot_file() -> None:
    """同一店铺始终对应同一个文件身份，不同店铺不共用。不检查路径字符串。"""
    bind = _fn("snapshot_file_for_store")
    stores = ("店铺甲", "店铺乙", "店铺丙")
    first = [bind(store) for store in stores]
    second = [bind(store) for store in stores]
    assert first == second
    assert _unique_count(first) == len(stores)


def test_period_parsing_is_deterministic() -> None:
    """同一口径、同一天解析两次必须相同。三个已写明的口径互不相等。"""
    parse = _fn("parse_period")
    today = date(2026, 10, 16)
    parsed = tuple(parse(label, today=today) for label in PERIOD_LABELS)
    again = tuple(parse(label, today=today) for label in PERIOD_LABELS)
    assert parsed == again
    assert parsed[0] != parsed[1]
    assert parsed[1] != parsed[2]
    assert parsed[0] != parsed[2]


def test_q3_window_is_sixty_days_excluding_today() -> None:
    """Q3 是最近 60 个日点，不含今天。"""
    window = _fn("q3_window")
    today = date(2026, 10, 16)
    expected = tuple(today - timedelta(days=delta) for delta in range(60, 0, -1))
    assert tuple(window(today)) == expected
    assert tuple(window(today)) == tuple(window(today))
    assert today not in expected
    assert len(expected) == 60
    tomorrow = today + timedelta(days=1)
    assert tuple(window(tomorrow)) == tuple(
        tomorrow - timedelta(days=delta) for delta in range(60, 0, -1)
    )


def test_replaying_one_snapshot_repeats_the_conclusion() -> None:
    """同一快照原文重复执行，结论字符串相同。"""
    conclude = _fn("symptom_conclusion")
    snapshot = "快照原文 17"
    assert conclude(snapshot) == conclude(snapshot)
    assert isinstance(conclude(snapshot), str)


def test_conclusion_numbers_come_only_from_snapshot_text() -> None:
    """结论里的数字只能来自这次传入的快照原文。"""
    conclude = _fn("symptom_conclusion")
    for snapshot in ("快照原文 17", "快照原文 19", "没有数字的原文"):
        conclusion = conclude(snapshot)
        assert isinstance(conclusion, str)
        assert _numbers(conclusion) <= _numbers(snapshot)
        assert conclusion == conclude(snapshot)


def test_query_names_are_q1_through_q5() -> None:
    """五个查询名使用规格原文。"""
    names = _fn("query_names")()
    if isinstance(names, (str, bytes)) or not isinstance(names, Sequence):
        _absent("query_names did not return the five display names")
    assert tuple(str(name) for name in names) == QUERY_NAMES


def test_preload_consumes_only_completed_with_rows() -> None:
    """只有 COMPLETED 且行数大于 0 可以消费。"""
    consumable = _fn("preload_consumable")
    assert consumable("COMPLETED", 1) is True
    assert consumable("COMPLETED", 3) is True
    assert consumable("COMPLETED", 0) is False
    assert consumable("RUNNING", 3) is False
    assert consumable("FAILED", 3) is False


def test_running_preload_is_not_refilled() -> None:
    """RUNNING 禁止重复补数。"""
    assert _fn("preload_refill_allowed")("RUNNING") is False


def test_failed_preload_may_be_retried() -> None:
    """FAILED 允许人工重试。"""
    assert _fn("preload_retry_allowed")("FAILED") is True


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text))


def _unique_count(items: list[Any]) -> int:
    unique: list[Any] = []
    for item in items:
        if not any(item == kept for kept in unique):
            unique.append(item)
    return len(unique)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.snapshot_structure")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.snapshot_structure is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"snapshot structure is absent: {detail}")
