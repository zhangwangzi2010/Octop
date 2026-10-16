"""Contracts for the diagnosis run state machine, retry table, and flow A spine.

Stage names and timeout budgets are the ones already written in the
orchestration spec and WT-2 task list. These tests do not invent a fifth
English stage name, a summarize retry count, symptom rules, hit lines, or
thresholds.

Surface:

- ``stage_names() -> Sequence[str]`` — PREPARING / ANALYZING / DIAGNOSING / COMPLETING / 终态
- ``terminal_states() -> Sequence[str]`` — COMPLETED / PARTIAL / FAILED / CANCELLED
- ``move(current, target) -> Mapping`` — ``accepted``, ``state``, ``events``
- ``retry_policy(node) -> Mapping`` — written timeout; ``max_attempts`` only where a count is written
- ``run_with_retry(node, action) -> Mapping`` — ``failed``, ``attempts``, ``events``; ``state`` is FAILED when exhausted
- ``DiagnosisOrchestrator`` — flow A gate, zero LLM, idempotency, resume, caller-set limit
- ``reset_orphan_items`` — startup resets a DIAGNOSING crash and continues
- ``contract_gate`` — conclusion-schema or data_refs failure is recorded as FAIL
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


def test_flow_a_is_zero_llm_and_skips_diagnosing() -> None:
    """流程 A 不调用 LLM，依次经过 PREPARING、ANALYZING、COMPLETING 后进入 COMPLETED。"""
    calls: list[object] = []

    def llm(*_args: object, **_kwargs: object) -> None:
        calls.append("called")

    orch = _orchestrator(attribution_limit=3, llm=llm)
    result = _submit(orch, client_request_id="flow-a", stores=("s1",))
    assert calls == []
    assert result["llm_calls"] == 0
    assert result["stages"] == ["PREPARING", "ANALYZING", "COMPLETING", "COMPLETED"]
    assert result["state"] == "COMPLETED"
    assert result["conclusion"] == "快照原文"
    assert orch.attribution_held == 0


def test_injected_analysis_port_replaces_the_default_conclusion() -> None:
    """分析口可以替换默认的快照结论回显。"""
    orch = _orchestrator(attribution_limit=3, analysis=lambda text: f"port:{text}")
    result = _submit(orch, client_request_id="port", stores=("s1",))
    assert result["conclusion"] == "port:快照原文"
    assert result["analysis_called"] is True


def test_preload_failure_is_not_the_contract_gate() -> None:
    """预加载未通过时不进入分析，也不把这件事记成契约门禁。"""
    seen = {"n": 0}

    def analysis(text: str) -> str:
        seen["n"] += 1
        return text

    orch = _orchestrator(attribution_limit=3, analysis=analysis)
    running = _submit(
        orch,
        client_request_id="running",
        stores=("s1",),
        preload_status="RUNNING",
        row_count=4,
    )
    empty = _submit(
        orch,
        client_request_id="empty",
        stores=("s1",),
        preload_status="COMPLETED",
        row_count=0,
    )
    assert seen["n"] == 0
    for result in (running, empty):
        assert result["analysis_called"] is False
        assert result["state"] == "PREPARING"
        assert result["stages"] == ["PREPARING"]
        events = _events(result)
        assert events
        assert all(event.get("reason") != "timeout" for event in events)
        assert all(event.get("kind") != "contract_gate" for event in events)


def test_contract_gate_records_schema_and_data_ref_failures_as_fail() -> None:
    """结论 schema 或 data_refs 对不上时，契约门禁记 FAIL。"""
    gate = _fn("contract_gate")
    schema = _mapping(gate(conclusion_schema_ok=False, cited_values=("12",), slice_values=("12",)))
    refs = _mapping(gate(conclusion_schema_ok=True, cited_values=("99",), slice_values=("12",)))
    ok = _mapping(gate(conclusion_schema_ok=True, cited_values=("12",), slice_values=("12", "4")))
    for failed, flag in ((schema, "conclusion_schema"), (refs, "data_refs")):
        assert failed["result"] == "FAIL"
        events = _events(failed)
        assert events[0]["kind"] == "contract_gate"
        assert events[0]["result"] == "FAIL"
        assert events[0][flag] is True
    assert ok["result"] == "OK"
    assert all(event.get("result") != "FAIL" for event in _events(ok))


def test_startup_resumes_a_diagnosing_crash() -> None:
    """启动调用 reset_orphan_items，DIAGNOSING 崩溃可以续跑，且不从头进入 PREPARING。"""
    try:
        orch = _orchestrator(attribution_limit=3, orphans=(_diagnosing_orphan(),))
    except TypeError as exc:
        pytest.fail(f"startup does not accept a DIAGNOSING crash ({exc})")
    if not callable(getattr(orch, "reset_orphan_items", None)):
        pytest.fail("reset_orphan_items is not implemented")
    if getattr(orch, "reset_orphan_calls", 0) < 1:
        pytest.fail("startup did not call reset_orphan_items")
    result = _submit(orch, client_request_id="diag-crash", stores=("s1", "s2"))
    assert result["stages"] == ["DIAGNOSING", "COMPLETING", "COMPLETED"]
    assert result["state"] == "COMPLETED"
    assert result["conclusion"] == "快照原文"
    assert result["llm_calls"] == 0
    assert [item["store_id"] for item in result["items"]] == ["s1"]
    assert result["items"][0]["state"] == "OK"
    assert any(event.get("kind") == "reset_orphan_items" for event in _events(result))
    orch.reset_orphan_items()
    again = _submit(orch, client_request_id="diag-crash", stores=("s9",))
    assert again["run_id"] == result["run_id"]
    assert again["stages"] == result["stages"]
    assert list(again["events"]) == list(result["events"])
    assert [item["store_id"] for item in again["items"]] == ["s1"]


def test_client_request_id_returns_the_same_run_without_new_items() -> None:
    """同一个 client_request_id 返回既有 run，不追加店铺 item。"""
    orch = _orchestrator(attribution_limit=3)
    first = _submit(orch, client_request_id="same", stores=("s1",))
    second = _submit(orch, client_request_id="same", stores=("s1", "s2"))
    assert first["run_id"] == second["run_id"]
    assert [item["store_id"] for item in second["items"]] == ["s1"]


def test_resume_from_analyzing_does_not_reenter_preparing() -> None:
    """从 ANALYZING 断点续跑，不再进入 PREPARING。"""
    orch = _orchestrator(attribution_limit=5)
    result = _submit(
        orch,
        client_request_id="resume",
        stores=("s1",),
        snapshot_text="续跑",
        checkpoint="ANALYZING",
    )
    assert result["stages"] == ["ANALYZING", "COMPLETING", "COMPLETED"]
    assert result["state"] == "COMPLETED"
    assert result["conclusion"] == "续跑"
    again = _submit(
        orch,
        client_request_id="resume",
        stores=("s1", "s9"),
        checkpoint="PREPARING",
    )
    assert again["run_id"] == result["run_id"]
    assert again["stages"] == ["ANALYZING", "COMPLETING", "COMPLETED"]


def test_attribution_limit_rejects_the_next_acquire() -> None:
    """归因槽由调用方指定为 3 或 5；纯数据节点不占槽。"""
    limited = _orchestrator(attribution_limit=3)
    assert [limited.try_acquire_attribution() for _ in range(3)] == [True, True, True]
    assert limited.try_acquire_attribution() is False
    held = limited.attribution_held
    limited.run_data_node("ensure_data_ready")
    assert limited.attribution_held == held

    wider = _orchestrator(attribution_limit=5)
    assert [wider.try_acquire_attribution() for _ in range(5)] == [True, True, True, True, True]
    assert wider.try_acquire_attribution() is False


def _diagnosing_orphan() -> dict[str, Any]:
    return {
        "client_request_id": "diag-crash",
        "state": "DIAGNOSING",
        "snapshot_text": "快照原文",
        "items": ({"store_id": "s1", "state": "DIAGNOSING"},),
    }


def _orchestrator(**kwargs: Any) -> Any:
    return _fn("DiagnosisOrchestrator")(**kwargs)


def _submit(orch: Any, **kwargs: Any) -> Mapping[str, Any]:
    payload: dict[str, Any] = {
        "preload_status": "COMPLETED",
        "row_count": 1,
        "snapshot_text": "快照原文",
    }
    payload.update(kwargs)
    return _mapping(orch.submit(**payload))


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
