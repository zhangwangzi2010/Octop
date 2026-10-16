"""RED contracts for the diagnosis run state machine and node retry table.

``octop.infra.diagnosis.orchestrator`` does not exist yet. These tests fail
because that API is absent. Stage names and timeout budgets are the ones
already written in the orchestration spec and WT-2 task list. This file does
not invent a fifth English stage name, a summarize retry count, symptom
rules, hit lines, or thresholds.

Expected surface once the module exists:

- ``stage_names() -> Sequence[str]`` — PREPARING / ANALYZING / DIAGNOSING / COMPLETING / 终态
- ``terminal_states() -> Sequence[str]`` — COMPLETED / PARTIAL / FAILED / CANCELLED
- ``move(current, target) -> Mapping`` — ``accepted``, ``state``, ``events``
- ``retry_policy(node) -> Mapping`` — written timeout; ``max_attempts`` only where a count is written
- ``run_with_retry(node, action) -> Mapping`` — ``failed``, ``attempts``, ``events``; ``state`` is FAILED when exhausted
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any, NoReturn

import pytest

STAGE_NAMES = ("PREPARING", "ANALYZING", "DIAGNOSING", "COMPLETING", "终态")
TERMINAL_STATES = ("COMPLETED", "PARTIAL", "FAILED", "CANCELLED")

# Flow A skips DIAGNOSING. The machine still allows the written DIAGNOSING edges.
LEGAL_EDGES = (
    ("PREPARING", "ANALYZING"),
    ("ANALYZING", "COMPLETING"),
    ("ANALYZING", "DIAGNOSING"),
    ("DIAGNOSING", "COMPLETING"),
    ("COMPLETING", "COMPLETED"),
    ("COMPLETING", "PARTIAL"),
    ("PREPARING", "FAILED"),
    ("ANALYZING", "FAILED"),
    ("DIAGNOSING", "FAILED"),
    ("COMPLETING", "FAILED"),
    ("PREPARING", "CANCELLED"),
    ("ANALYZING", "CANCELLED"),
    ("DIAGNOSING", "CANCELLED"),
    ("COMPLETING", "CANCELLED"),
)

ILLEGAL_EDGES = (
    ("ANALYZING", "PREPARING"),
    ("COMPLETED", "PREPARING"),
    ("CANCELLED", "DIAGNOSING"),
    ("PREPARING", "COMPLETING"),
    ("PREPARING", "DIAGNOSING"),
    ("FAILED", "COMPLETED"),
    ("COMPLETING", "ANALYZING"),
    ("PARTIAL", "COMPLETED"),
    ("DIAGNOSING", "ANALYZING"),
    ("PREPARING", "COMPLETED"),
    ("ANALYZING", "COMPLETED"),
)


def test_stage_names_are_the_five_written_stages() -> None:
    """五阶段名使用规格原文，终态的四个成员也使用规格原文。"""
    assert tuple(_fn("stage_names")()) == STAGE_NAMES
    assert tuple(_fn("terminal_states")()) == TERMINAL_STATES


def test_illegal_transitions_are_rejected_and_recorded() -> None:
    """非法迁移被拒绝，状态不变，并记下 illegal_transition 事件。"""
    move = _fn("move")
    for current, target in ILLEGAL_EDGES:
        result = _mapping(move(current, target))
        assert result["accepted"] is False
        assert result["state"] == current
        events = _events(result)
        assert events
        assert events[0]["kind"] == "illegal_transition"
        assert events[0]["from"] == current
        assert events[0]["to"] == target


def test_written_forward_edges_are_accepted() -> None:
    """规格写出的正向边可以进入目标状态，且不记非法迁移。"""
    move = _fn("move")
    for current, target in LEGAL_EDGES:
        result = _mapping(move(current, target))
        assert result["accepted"] is True
        assert result["state"] == target
        assert all(event.get("kind") != "illegal_transition" for event in _events(result))

    state = "PREPARING"
    for target in ("ANALYZING", "COMPLETING", "COMPLETED"):
        result = _mapping(move(state, target))
        assert result["accepted"] is True
        state = str(result["state"])
    assert state == "COMPLETED"


def test_retry_policy_uses_the_written_timeout_table() -> None:
    """超时表只使用已写出的秒数和次数；summarize 不另造重试次数。"""
    policy = _fn("retry_policy")
    ready = _mapping(policy("ensure_data_ready"))
    assert ready["timeout_seconds"] == 30 * 60
    assert ready["max_attempts"] == 3

    analysis = _mapping(policy("analysis_run"))
    assert analysis["timeout_seconds"] == 900
    assert analysis["max_attempts"] == 2

    segment = _mapping(policy("diagnose 段1"))
    assert segment["timeout_seconds"] == 60
    assert segment["max_attempts"] == 2

    summarize = _mapping(policy("summarize"))
    assert summarize["timeout_seconds"] == 600
    assert "max_attempts" not in summarize


def test_ensure_data_ready_exhausts_three_timeouts_into_failed() -> None:
    """ensure_data_ready 三次超时后 run 进入 FAILED，并留下三次 timeout 事件。"""
    action = _timeouts(3)
    result = _mapping(_fn("run_with_retry")("ensure_data_ready", action))
    assert result["failed"] is True
    assert result["state"] == "FAILED"
    assert result["attempts"] == 3
    events = _events(result)
    assert [event["attempt"] for event in events] == [1, 2, 3]
    assert [event["reason"] for event in events] == ["timeout", "timeout", "timeout"]


def test_analysis_run_succeeds_on_the_second_attempt() -> None:
    """analysis_run 第一次超时后第二次成功，不进入 FAILED。"""
    action = _timeouts(1)
    result = _mapping(_fn("run_with_retry")("analysis_run", action))
    assert result["failed"] is False
    assert result["attempts"] == 2
    assert result.get("state") in (None, "ANALYZING")
    events = _events(result)
    assert len(events) == 1
    assert events[0]["reason"] == "timeout"
    assert events[0]["attempt"] == 1


def test_analysis_run_two_timeouts_fail_the_run() -> None:
    """analysis_run 两次超时后进入 FAILED。"""
    action = _timeouts(2)
    result = _mapping(_fn("run_with_retry")("analysis_run", action))
    assert result["failed"] is True
    assert result["state"] == "FAILED"
    assert result["attempts"] == 2
    events = _events(result)
    assert [event["reason"] for event in events] == ["timeout", "timeout"]


def test_diagnose_segment_one_two_timeouts_fail_the_run() -> None:
    """diagnose 段1 使用规格里的中文节点名，两次超时后进入 FAILED。"""
    action = _timeouts(2)
    result = _mapping(_fn("run_with_retry")("diagnose 段1", action))
    assert result["failed"] is True
    assert result["state"] == "FAILED"
    assert result["attempts"] == 2


def _timeouts(count: int) -> Callable[[], str]:
    seen = {"n": 0}

    def action() -> str:
        seen["n"] += 1
        if seen["n"] <= count:
            raise TimeoutError("timeout")
        return "ok"

    return action


def _events(result: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = result.get("events", ())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        _absent("events did not return the recorded node events")
    return tuple(_mapping(item) for item in raw)


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _absent("orchestrator did not return a mapping")
    return value


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.orchestrator")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.orchestrator is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"orchestrator is absent: {detail}")
