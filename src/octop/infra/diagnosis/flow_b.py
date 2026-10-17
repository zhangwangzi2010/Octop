"""Flow B attribution.

Stage 1 builds context without an LLM. Stage 2 may call an LLM only to
produce an interpretation, then the existing contract gate decides FAIL.
Skill asset names and report headings are the ones already written in the
spec. SOUL titles are the five inline steps from kickoff §6.1.1.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from octop.infra.diagnosis.hit_weights import (
    hit_rule,
    metric_ids,
    metric_name,
    metric_weight_percent,
)
from octop.infra.diagnosis.l1_semantic import yellow_metric_names
from octop.infra.diagnosis.orchestrator import contract_gate, retry_policy
from octop.infra.diagnosis.pop_rules import ratio_pop
from octop.infra.diagnosis.snapshot_store import performance_table

_SKILL_ASSETS: tuple[str, ...] = (
    "metrics_catalog",
    "analysis_guide",
    "drilldown_playbook",
    "query_tasks",
)
_CAUSAL_LINKS: tuple[str, ...] = ("越阈指标", "业务后果", "绩效影响", "平台后果")
_UNVERIFIED = "待验证"
_REPORT_SECTIONS: tuple[str, ...] = (
    "〇 执行摘要",
    "一 共性问题",
    "二 特别情况店铺",
    "三 共性店铺",
    "四 整改优先级",
    "五 逐店明细",
)
_TOP_KEYS: tuple[str, ...] = ("headline", "overall", "findings", "actions", "risks")
_FINDING_KEYS: tuple[str, ...] = ("title", "severity", "analysis", "evidence", "data_refs")
_ACTION_KEYS: tuple[str, ...] = ("title", "detail")
_STAGE2_TIMEOUT_SECONDS = 600
_NO_DRILL = "无明细下钻能力"
_UNDRILLABLE: frozenset[str] = frozenset({"C-S11", "C-S12", "C-S13", "C-S14", "C-S15", "C-S16"})


def skill_assets() -> tuple[str, ...]:
    """The four skill asset names. ``metrics_catalog`` is the fact source."""
    return _SKILL_ASSETS


def load_skills() -> tuple[dict[str, Any], ...]:
    """Load the four assets. Only analysis_guide has the routing table."""
    guide = analysis_guide_body()
    return tuple(
        {
            "name": name,
            "body": guide if name == "analysis_guide" else "",
            "fact_source": name == "metrics_catalog",
        }
        for name in _SKILL_ASSETS
    )


def analysis_guide_body() -> str:
    """Routing table with locked hit lines. C-S09 stays ≥10%."""
    lines = [
        "下钻分流。阈值和权重用已锁定命中线。",
        "可下钻：绩效分、用户评价分（C-S07）、非买家责任退货退款率（C-S08）、"
        "延迟发货率（C-S09）、延迟到货率（C-S10）。",
        "不可下钻：缺货率（C-S11）、24 小时回复率（C-S12）、售后准时率（C-S13）、"
        f"爆旺款率（C-S14）、售罄健康分（C-S15）、活动报名率（C-S16）。{_NO_DRILL}。",
    ]
    for metric_id in metric_ids():
        weight = metric_weight_percent(metric_id)
        lines.append(
            f"{metric_id} {metric_name(metric_id)} 权重 {weight:g}% 命中 {hit_rule(metric_id)}"
        )
    return "\n".join(lines)


def drill_route(name: str) -> str | None:
    """Detail route for a drillable item. The other six have none."""
    routes = {
        "绩效分": performance_table(),
        "C-S07": "评价",
        "C-S08": "售后",
        "C-S09": "发货",
        "C-S10": "到货",
    }
    return routes.get(name)


def undrillable_mark(name: str) -> str:
    """The six platform metrics must say they have no detail drill."""
    if name in _UNDRILLABLE:
        return _NO_DRILL
    return ""


def soul_steps() -> tuple[str, ...]:
    """Inline SOUL titles from kickoff §6.1.1. They are not a skill asset."""
    return (
        "① read_file 读取本 run 的切片（slice.json）",
        "② 只解读 hit=true 的项（个体优先 / 权重降序；共性带过，不展开）",
        "③ 按契约 write_file interpretation.json（headline / overall / findings / actions / risks，含 data_refs）",
        "④ execute 强制校验（scripts/validate_*.py：结构 + data_refs 数值逐条核对；不过 → 必须改，禁止静默降级）",
        "⑤ 一行收尾（结论 + 命中最重项）",
    )


def causal_chain_links() -> tuple[str, ...]:
    """The four links in the written causal-chain pattern."""
    return _CAUSAL_LINKS


def unverified_mark() -> str:
    """Mark for a causal link that has no supporting data."""
    return _UNVERIFIED


def report_sections() -> tuple[str, ...]:
    """Report headings from the attribution spec, in order."""
    return _REPORT_SECTIONS


def stage1_policy() -> Mapping[str, int]:
    """段1 uses the existing diagnose 段1 retry row."""
    return retry_policy("diagnose 段1")


def stage2_timeout_seconds() -> int:
    """段2 budget written in the attribution spec. It has no attempt count."""
    return _STAGE2_TIMEOUT_SECONDS


def stage1_context(
    *,
    metrics: Sequence[Mapping[str, Any]],
    current_numerators: Sequence[float],
    current_denominators: Sequence[float],
    previous_numerators: Sequence[float] | None,
    previous_denominators: Sequence[float] | None,
) -> dict[str, Any]:
    """Period-total ratio context. Yellow metrics contribute no value."""
    yellow = set(yellow_metric_names())
    values: dict[str, Any] = {}
    for metric in metrics:
        name = str(metric["name"])
        if name in yellow:
            continue
        values[name] = metric.get("value")
    return {
        "llm_calls": 0,
        "pop": ratio_pop(
            current_numerators,
            current_denominators,
            previous_numerators,
            previous_denominators,
        ),
        "uses_daily_rate_mean": False,
        "sessions": (),
        "values": values,
    }


def diagnose_item(
    *,
    run_id: str,
    store_id: str,
    attempt: int,
    conclusion: Mapping[str, Any] | None,
    slice_values: Sequence[object],
    prior_threads: Sequence[str] = (),
    metrics: Sequence[str] = (),
    llm: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Run 段2 interpretation under the existing contract gate.

    A yellow-only metric list does not open a thread and does not call the
    LLM. A gate FAIL keeps the current thread and adds ``attempt + 1``.
    """
    if metrics and set(metrics) <= set(yellow_metric_names()):
        return {
            "status": "SKIPPED",
            "result": "OK",
            "events": (),
            "attempt": attempt,
            "threads": (),
            "llm_calls": 0,
            "stage1_llm_calls": 0,
        }

    produced, llm_calls = _interpret(conclusion, llm)
    gate = contract_gate(
        conclusion_schema_ok=_schema_ok(produced),
        cited_values=_cited(produced),
        slice_values=slice_values,
    )
    threads = [str(name) for name in prior_threads]
    _remember(threads, _thread_name(run_id, store_id, attempt))
    next_attempt = attempt
    if gate["result"] == "FAIL":
        next_attempt = attempt + 1
        _remember(threads, _thread_name(run_id, store_id, next_attempt))
    status = "FAILED" if gate["result"] == "FAIL" else "OK"
    return {
        "status": status,
        "result": gate["result"],
        "events": tuple(gate["events"]),
        "attempt": next_attempt,
        "threads": tuple(threads),
        "llm_calls": llm_calls,
        "stage1_llm_calls": 0,
    }


def synthesize_report(
    items: Sequence[Mapping[str, Any]],
    *,
    summarize_failed: bool = False,
) -> dict[str, Any]:
    """Five written headings, or a status list when summarize fails."""
    appendix = tuple(
        str(item["store_id"]) for item in items if item["status"] in {"FAILED", "SKIPPED"}
    )
    partial = any(item["status"] == "FAILED" for item in items)
    if summarize_failed:
        lines = tuple(f"{item['store_id']} {item['status']}" for item in items)
        return {
            "degraded": True,
            "sections": (),
            "appendix": appendix,
            "partial": partial,
            "lines": lines,
        }
    return {
        "degraded": False,
        "sections": _REPORT_SECTIONS,
        "appendix": appendix,
        "partial": partial,
        "lines": (),
    }


def _interpret(
    conclusion: Mapping[str, Any] | None,
    llm: Callable[[], Any] | None,
) -> tuple[Mapping[str, Any], int]:
    if llm is None:
        return (conclusion or {}, 0)
    produced = llm()
    if not isinstance(produced, Mapping):
        return ({}, 1)
    return (produced, 1)


def _schema_ok(conclusion: Mapping[str, Any]) -> bool:
    for key in _TOP_KEYS:
        if key not in conclusion:
            return False
    if not _is_sequence(conclusion["findings"]) or not _is_sequence(conclusion["actions"]):
        return False
    if not _is_sequence(conclusion["risks"]):
        return False
    if any(not _has_keys(finding, _FINDING_KEYS) for finding in conclusion["findings"]):
        return False
    if any(not _has_keys(action, _ACTION_KEYS) for action in conclusion["actions"]):
        return False
    return all(link in conclusion for link in _CAUSAL_LINKS)


def _cited(conclusion: Mapping[str, Any]) -> tuple[object, ...]:
    findings = conclusion.get("findings", ())
    if not _is_sequence(findings):
        return ()
    cited: list[object] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        refs = finding.get("data_refs", ())
        if _is_sequence(refs):
            cited.extend(refs)
    return tuple(cited)


def _has_keys(value: object, keys: tuple[str, ...]) -> bool:
    return isinstance(value, Mapping) and all(key in value for key in keys)


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _thread_name(run_id: str, store_id: str, attempt: int) -> str:
    return f"diag:{run_id}:{store_id}:a{attempt}"


def _remember(threads: list[str], name: str) -> None:
    if name not in threads:
        threads.append(name)
