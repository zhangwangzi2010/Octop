"""RED contracts for flow B attribution.

``octop.infra.diagnosis.flow_b`` does not exist yet. These tests fail because
that API is absent. Item FAIL goes through the existing ``contract_gate``.
SOUL step names, strategy metrics, fulfillment columns, and after-sales class
names are not invented.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

import pytest

from octop.infra.diagnosis.l1_semantic import yellow_metric_names
from octop.infra.diagnosis.orchestrator import contract_gate, retry_policy
from octop.infra.diagnosis.pop_rules import ratio_pop

_MODULE = "octop.infra.diagnosis.flow_b"
_SECTIONS = (
    "〇 执行摘要",
    "一 共性问题",
    "二 特别情况店铺",
    "三 共性店铺",
    "四 整改优先级",
    "五 逐店明细",
)
_SKILLS = ("metrics_catalog", "analysis_guide", "drilldown_playbook", "query_tasks")
_SOUL_STEPS = (
    "① read_file 读取本 run 的切片（slice.json）",
    "② 只解读 hit=true 的项（个体优先 / 权重降序；共性带过，不展开）",
    "③ 按契约 write_file interpretation.json（headline / overall / findings / actions / risks，含 data_refs）",
    "④ execute 强制校验（scripts/validate_*.py：结构 + data_refs 数值逐条核对；不过 → 必须改，禁止静默降级）",
    "⑤ 一行收尾（结论 + 命中最重项）",
)
_LINKS = ("越阈指标", "业务后果", "绩效影响", "平台后果")


def test_schema_or_data_ref_mismatch_marks_the_item_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """结论 schema 失败，或 data_refs 不在切片里，item 记 FAIL。"""
    module = _module()
    seen: dict[str, bool] = {}
    real = contract_gate

    def _wrapped(**kwargs: Any) -> dict[str, Any]:
        seen["called"] = True
        return real(**kwargs)

    monkeypatch.setattr(module, "contract_gate", _wrapped)
    schema = _mapping(
        _call(
            "diagnose_item",
            run_id="run-1",
            store_id="s1",
            attempt=1,
            conclusion=_conclusion(drop="headline"),
            slice_values=("0.08",),
        )
    )
    refs = _mapping(
        _call(
            "diagnose_item",
            run_id="run-1",
            store_id="s1",
            attempt=1,
            conclusion=_conclusion("99"),
            slice_values=("0.08",),
        )
    )
    ok = _mapping(
        _call(
            "diagnose_item",
            run_id="run-1",
            store_id="s1",
            attempt=1,
            conclusion=_conclusion("0.08"),
            slice_values=("0.08",),
        )
    )
    assert seen["called"] is True
    for failed, flag in ((schema, "conclusion_schema"), (refs, "data_refs")):
        assert failed["result"] == "FAIL"
        assert failed["status"] == "FAILED"
        event = _events(failed)[0]
        assert event["kind"] == "contract_gate"
        assert event[flag] is True
        assert failed["attempt"] == 2
        assert failed["threads"] == (
            "diag:run-1:s1:a1",
            "diag:run-1:s1:a2",
        )
        assert failed["stage1_llm_calls"] == 0
    assert ok["result"] == "OK"
    assert ok["status"] == "OK"
    assert ok["attempt"] == 1
    assert ok["threads"] == ("diag:run-1:s1:a1",)


def test_attempt_increment_keeps_the_old_thread() -> None:
    """段2 失败后 attempt+1 换会话，旧 thread 还在。"""
    first = _mapping(
        _call(
            "diagnose_item",
            run_id="run-9",
            store_id="shop-a",
            attempt=1,
            conclusion=_conclusion("99"),
            slice_values=("0.08",),
        )
    )
    second = _mapping(
        _call(
            "diagnose_item",
            run_id="run-9",
            store_id="shop-a",
            attempt=first["attempt"],
            conclusion=_conclusion("0.08"),
            slice_values=("0.08",),
            prior_threads=first["threads"],
        )
    )
    assert first["threads"] == ("diag:run-9:shop-a:a1", "diag:run-9:shop-a:a2")
    assert second["threads"] == (
        "diag:run-9:shop-a:a1",
        "diag:run-9:shop-a:a2",
    )
    assert second["result"] == "OK"


def test_stage1_reuses_ratio_pop_and_skips_yellow_metrics() -> None:
    """段1 复用周期合计环比，不调用 LLM，黄标不产生数值会话。"""
    current_numerators = (1.0, 1.0)
    current_denominators = (4.0, 4.0)
    previous_numerators = (1.0,)
    previous_denominators = (2.0,)
    context = _mapping(
        _call(
            "stage1_context",
            metrics=tuple({"name": name, "value": 1} for name in yellow_metric_names()),
            current_numerators=current_numerators,
            current_denominators=current_denominators,
            previous_numerators=previous_numerators,
            previous_denominators=previous_denominators,
        )
    )
    assert context["llm_calls"] == 0
    assert context["pop"] == ratio_pop(
        current_numerators,
        current_denominators,
        previous_numerators,
        previous_denominators,
    )
    assert context["uses_daily_rate_mean"] is False
    assert context["sessions"] == ()
    assert context["values"] == {}
    policy = _mapping(_call("stage1_policy"))
    assert dict(policy) == dict(retry_policy("diagnose 段1"))
    assert _call("stage2_timeout_seconds") == 600


def test_expert_loads_four_skill_assets_and_soul_steps() -> None:
    """四份技能资产按原文加载。SOUL 五步是内联标题，不是第六份 Skill。"""
    assert _call("skill_assets") == _SKILLS
    loaded = _items(_call("load_skills"))
    assert tuple(item["name"] for item in loaded) == _SKILLS
    assert [item["name"] for item in loaded if item["fact_source"] is True] == ["metrics_catalog"]
    assert all(item["body"] == "" for item in loaded)
    assert _call("soul_steps") == _SOUL_STEPS
    assert _call("causal_chain_links") == _LINKS
    assert _call("unverified_mark") == "待验证"


def test_report_sections_partial_appendix_and_degraded_list() -> None:
    """五段标题按规格原文，PARTIAL 附录列出 FAILED 与 SKIPPED，失败则列表拼接。"""
    report = _mapping(
        _call(
            "synthesize_report",
            (
                {"store_id": "s1", "status": "OK"},
                {"store_id": "s2", "status": "FAILED"},
                {"store_id": "s3", "status": "FAILED"},
                {"store_id": "s4", "status": "SKIPPED"},
            ),
        )
    )
    assert report["sections"] == _SECTIONS
    assert report["partial"] is True
    assert report["degraded"] is False
    assert report["appendix"] == ("s2", "s3", "s4")
    degraded = _mapping(
        _call(
            "synthesize_report",
            (
                {"store_id": "s2", "status": "FAILED"},
                {"store_id": "s3", "status": "FAILED"},
            ),
            summarize_failed=True,
        )
    )
    assert degraded["degraded"] is True
    assert degraded["sections"] == ()
    assert degraded["lines"] == ("s2 FAILED", "s3 FAILED")


def test_yellow_metrics_do_not_open_an_attribution_thread() -> None:
    """黄标不为五项创建归因会话，结论路径也不调用 LLM。"""
    result = _mapping(
        _call(
            "diagnose_item",
            run_id="run-1",
            store_id="s1",
            attempt=1,
            conclusion=_conclusion("0.08"),
            slice_values=("0.08",),
            metrics=yellow_metric_names(),
            llm=lambda: pytest.fail("yellow metrics must not call the LLM"),
        )
    )
    assert result["status"] == "SKIPPED"
    assert result["threads"] == ()
    assert result["llm_calls"] == 0
    assert result["stage1_llm_calls"] == 0


def _conclusion(data_ref: str = "0.08", *, drop: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "headline": "摘要",
        "overall": "总体",
        "findings": [
            {
                "title": "发现",
                "severity": "一般",
                "analysis": "分析",
                "evidence": [],
                "data_refs": [data_ref],
            }
        ],
        "actions": [{"title": "建议", "detail": "说明"}],
        "risks": [],
        "越阈指标": "待验证",
        "业务后果": "待验证",
        "绩效影响": "待验证",
        "平台后果": "待验证",
    }
    if drop is not None:
        del body[drop]
    return body


def _events(result: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return _items(result["events"])


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent("result did not return a sequence")
    return tuple(item for item in value if isinstance(item, Mapping))


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _absent("result did not return a mapping")
    return value


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    return _fn(name)(*args, **kwargs)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module(_MODULE)
    except ImportError as exc:
        _absent(f"{_MODULE} is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"flow B is absent: {detail}")
