"""Background fixture run.

Reads snapshots through snapshot_store. Diagnosis uses the existing flow B
and the locked hit, commonality, and priority functions. C-S11 and C-S14
use the sign of the period change. Drill routes hang off the routing table.
Level-1 derived values are recorded as a gap.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from typing import Any

from octop.infra.db.repos.diagnosis_runs import DiagnosisRunsRepo
from octop.infra.diagnosis.flow_b import (
    diagnose_item,
    drill_route,
    report_sections,
    synthesize_report,
    undrillable_mark,
)
from octop.infra.diagnosis.hit_weights import (
    common_hit_rate,
    counts_toward_common_denominator,
    individual_weight,
    judgment_basis,
    metric_ids,
    metric_name,
    metric_weight_percent,
    pop_direction_hits,
    score_hits,
    stored_ratio_hits,
    total_weight,
)
from octop.infra.diagnosis.pop_rules import pop_direction
from octop.infra.diagnosis.remaining_contracts import chosen_detail_limit
from octop.infra.diagnosis.snapshot_store import read_snapshot, read_store_fetch
from octop.infra.diagnosis.snapshot_structure import preload_consumable
from octop.infra.diagnosis.symptom_engine import (
    impact,
    individual_priority,
    is_common,
    score_band,
)

_GAPS: tuple[str, ...] = ("一级派生展示值不从快照现算",)
_PHASES: tuple[str, ...] = ("SKIP", "individual", "commonality")
_PRIORITIES: tuple[str, ...] = ("P0", "P1", "P2")
_APPENDIX: frozenset[str] = frozenset({"FAILED", "SKIPPED"})
_DETAIL_SHEETS: frozenset[str] = frozenset({"评价", "售后", "发货", "到货"})
FakeLlm = Callable[[str, tuple[object, ...]], Mapping[str, Any]]
_TASKS: dict[str, asyncio.Task[None]] = {}
_REPORTS: dict[str, dict[str, Any]] = {}


def known_gaps() -> tuple[str, ...]:
    """Rules this slice does not invent."""
    return _GAPS


def run_fixture(
    *,
    data_dir: str,
    stores: Sequence[str],
    llm: FakeLlm | None = None,
    run_id: str = "fixture",
) -> dict[str, Any]:
    """Run the three-way fixture to completion. Snapshots come from ``data_dir``."""
    loaded = tuple(_load(data_dir, store_id) for store_id in stores)
    common = _common_metrics(loaded)
    for row in loaded:
        row["role"] = _role(row["hits"], common)
    phases = _ordered(loaded)
    threads: list[str] = []
    flow_b_calls = 0
    for row in phases:
        if row["role"] == "SKIP":
            row["status"] = "SKIPPED"
            row["attempt"] = 1
            continue
        slice_values = _slice_values(row)
        outcome = diagnose_item(
            run_id=run_id,
            store_id=str(row["store_id"]),
            attempt=1,
            conclusion=None,
            slice_values=slice_values,
            llm=None if llm is None else _bound(llm, str(row["store_id"]), slice_values),
        )
        row["status"] = str(outcome["status"])
        row["attempt"] = int(outcome["attempt"])
        threads.extend(str(name) for name in outcome["threads"])
        flow_b_calls += int(outcome["llm_calls"])
    report = synthesize_report(
        tuple({"store_id": row["store_id"], "status": row["status"]} for row in phases)
    )
    numbers = _numbers(phases)
    body = _body(phases, common, numbers)
    groups = _groups(phases, common)
    return {
        "status": "PARTIAL" if report["partial"] else "COMPLETED",
        "partial": bool(report["partial"]),
        "appendix": tuple(report["appendix"]),
        "sections": report["sections"],
        "body": body,
        "numbers": numbers,
        "llm_calls": 0,
        "flow_b_llm_calls": flow_b_calls,
        "order": _PHASES,
        "threads": tuple(threads),
        "yellow_values": tuple(value for row in loaded for value in row["yellow_values"]),
        "groups": groups,
        "top5": _top5(phases, common),
        "store_weights": _store_weights(phases, common),
        "drills": _drills(phases),
        "commonality": _common_names(loaded, common),
        "gaps": _GAPS,
        "items": tuple(
            {
                "store_id": row["store_id"],
                "status": row["status"],
                "attempt": row["attempt"],
            }
            for row in phases
        ),
    }


def fixture_report(run_id: str) -> dict[str, Any] | None:
    """Return the stored report, if the background run has finished one."""
    return _REPORTS.get(run_id)


def schedule_fixture_run(
    *,
    run_id: str,
    data_dir: str,
    stores: Sequence[str],
    repo: DiagnosisRunsRepo,
    preload_status: str,
    row_count: int,
    llm: FakeLlm | None = None,
) -> None:
    """Start the fixture without waiting for it to finish."""
    task = asyncio.create_task(
        _finish(
            run_id=run_id,
            data_dir=data_dir,
            stores=stores,
            repo=repo,
            preload_status=preload_status,
            row_count=row_count,
            llm=llm,
        )
    )
    _TASKS[run_id] = task


async def wait_fixture(run_id: str) -> None:
    """Wait until the scheduled fixture task ends."""
    await _TASKS[run_id]


async def cancel_fixture_task(run_id: str) -> None:
    """Cancel the task when it is still running."""
    task = _TASKS.get(run_id)
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return


def stop_at_checkpoint(*, action: str) -> dict[str, Any]:
    """Timeout or cancel stops the checkpoint before any store is diagnosed."""
    return asyncio.run(_stop_at_checkpoint(action))


async def _finish(
    *,
    run_id: str,
    data_dir: str,
    stores: Sequence[str],
    repo: DiagnosisRunsRepo,
    preload_status: str,
    row_count: int,
    llm: FakeLlm | None,
) -> None:
    try:
        if not preload_consumable(preload_status, row_count):
            return
        report = await asyncio.to_thread(
            run_fixture,
            data_dir=data_dir,
            stores=stores,
            llm=llm,
            run_id=run_id,
        )
        current = repo.get_run(run_id)
        if current is None or current.status != "PREPARING":
            return
        _store_report(run_id, report)
        _persist(repo, run_id, report)
    except asyncio.CancelledError:
        repo.update_run_status(run_id, "CANCELLED")
        repo.cancel_unfinished_items(run_id)
        raise


def _store_report(run_id: str, report: Mapping[str, Any]) -> None:
    _REPORTS[run_id] = {
        "run_id": run_id,
        "partial": report["partial"],
        "appendix": list(report["appendix"]),
        "sections": list(report["sections"]),
        "body": report["body"],
        "numbers": list(report["numbers"]),
        "llm_calls": 0,
        "ready": True,
    }


def _persist(repo: DiagnosisRunsRepo, run_id: str, report: Mapping[str, Any]) -> None:
    by_store = {item.store_id: item for item in repo.list_items(run_id)}
    raw_items = report["items"]
    if isinstance(raw_items, tuple):
        for row in raw_items:
            if not isinstance(row, Mapping):
                continue
            stored = by_store.get(str(row["store_id"]))
            if stored is None:
                continue
            repo.update_item(
                stored.item_id,
                status=str(row["status"]),
                attempt=int(row["attempt"]),
            )
    repo.update_run_status(run_id, str(report["status"]))
    for stage in ("PREPARING", "ANALYZING", "DIAGNOSING", "COMPLETING"):
        repo.append_event(run_id=run_id, item_id=None, node=stage, event="stage")


async def _stop_at_checkpoint(action: str) -> dict[str, Any]:
    diagnosed: list[str] = []
    started = asyncio.Event()
    hold = asyncio.Event()

    async def _work() -> None:
        started.set()
        await asyncio.wait_for(hold.wait(), 0 if action == "timeout" else 30)
        diagnosed.append("later")

    task = asyncio.create_task(_work())
    await started.wait()
    status = "FAILED"
    if action == "cancel":
        task.cancel()
        status = "CANCELLED"
    with suppress(asyncio.CancelledError, TimeoutError):
        await task
    return {"status": status, "continued": False, "diagnosed": tuple(diagnosed)}


def _load(data_dir: str, store_id: str) -> dict[str, Any]:
    document = read_snapshot(data_dir, store_id)
    fetch = read_store_fetch(data_dir, store_id)
    performance = document["store_performance"]
    score = float(performance["mall_check_score"])
    metrics = performance.get("metrics")
    values = _metric_values(metrics)
    prevs = _metric_prevs(metrics)
    yellow_values: list[float] = []
    yellow = fetch["yellow"]
    if isinstance(yellow, tuple):
        for item in yellow:
            if not isinstance(item, Mapping):
                continue
            raw = item.get("value")
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            yellow_values.append(float(raw))
    hits = _hits(values, prevs)
    return {
        "store_id": store_id,
        "score": score,
        "values": values,
        "prevs": prevs,
        "hits": hits,
        "yellow_values": yellow_values,
        "role": "SKIP",
        "status": "PENDING",
        "attempt": 1,
    }


def _metric_values(metrics: object) -> dict[str, float]:
    """Latest values stored under the locked metric names."""
    if not isinstance(metrics, Mapping):
        return {}
    values: dict[str, float] = {}
    for metric_id in metric_ids():
        name = metric_name(metric_id)
        raw_metric = metrics.get(name)
        if not isinstance(raw_metric, Mapping):
            continue
        raw = raw_metric.get("latest")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        values[name] = float(raw)
    return values


def _metric_prevs(metrics: object) -> dict[str, float]:
    """Optional previous values stored for replay. They are not a new column."""
    if not isinstance(metrics, Mapping):
        return {}
    prevs: dict[str, float] = {}
    for metric_id in metric_ids():
        name = metric_name(metric_id)
        raw_metric = metrics.get(name)
        if not isinstance(raw_metric, Mapping):
            continue
        raw = raw_metric.get("prev")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        prevs[name] = float(raw)
    return prevs


def _hits(values: Mapping[str, float], prevs: Mapping[str, float]) -> tuple[str, ...]:
    found: list[str] = []
    for metric_id in metric_ids():
        name = metric_name(metric_id)
        if name not in values:
            continue
        value = values[name]
        basis = judgment_basis(metric_id)
        score_hit = basis == "score_passthrough" and score_hits(metric_id, value)
        ratio_hit = basis in {"latest_vs_threshold", "document_ratio"} and stored_ratio_hits(
            metric_id, value
        )
        direction_hit = _direction_hit(metric_id, name, value, prevs, basis)
        if score_hit or ratio_hit or direction_hit:
            found.append(metric_id)
    return tuple(found)


def _direction_hit(
    metric_id: str,
    name: str,
    value: float,
    prevs: Mapping[str, float],
    basis: str,
) -> bool:
    if basis != "pop_direction" or name not in prevs:
        return False
    label = pop_direction(value, prevs[name])
    return label is not None and pop_direction_hits(metric_id, label)


def _common_metrics(rows: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    common: set[str] = set()
    for metric_id in metric_ids():
        name = metric_name(metric_id)
        eligible = 0
        hits = 0
        for row in rows:
            values = row["values"]
            present = isinstance(values, Mapping) and name in values
            if counts_toward_common_denominator(present, False):
                eligible += 1
            row_hits = row["hits"]
            if isinstance(row_hits, tuple) and metric_id in row_hits:
                hits += 1
        if eligible == 0:
            continue
        if is_common(common_hit_rate(hits, eligible) * 100):
            common.add(metric_id)
    return frozenset(common)


def _role(hits: tuple[str, ...], common: frozenset[str]) -> str:
    if not hits:
        return "SKIP"
    if any(metric_id not in common for metric_id in hits):
        return "individual"
    return "commonality"


def _ordered(rows: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    ordered: list[dict[str, Any]] = []
    for phase in _PHASES:
        ordered.extend(row for row in rows if row["role"] == phase)
    return tuple(ordered)


def _slice_values(row: Mapping[str, Any]) -> tuple[float, ...]:
    values = row["values"]
    if not isinstance(values, Mapping):
        return ()
    ordered = [
        float(values[metric_name(metric_id)])
        for metric_id in metric_ids()
        if metric_name(metric_id) in values
    ]
    score = row["score"]
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        ordered.append(float(score))
    return tuple(ordered)


def _bound(
    llm: FakeLlm,
    store_id: str,
    slice_values: tuple[object, ...],
) -> Callable[[], Mapping[str, Any]]:
    def _call() -> Mapping[str, Any]:
        return llm(store_id, slice_values)

    return _call


def _numbers(rows: Sequence[Mapping[str, Any]]) -> tuple[float, ...]:
    found: list[float] = []
    for row in rows:
        values = row["values"]
        if not isinstance(values, Mapping):
            continue
        for metric_id in metric_ids():
            name = metric_name(metric_id)
            if name in values:
                found.append(float(values[name]))
        score = row["score"]
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            found.append(float(score))
    return tuple(found)


def _hit_ids(row: Mapping[str, Any]) -> tuple[str, ...]:
    hits = row["hits"]
    if not isinstance(hits, tuple):
        return ()
    return tuple(str(metric_id) for metric_id in hits)


def _store_weights(
    rows: Sequence[Mapping[str, Any]],
    common: frozenset[str],
) -> tuple[dict[str, Any], ...]:
    weighed: list[dict[str, Any]] = []
    for row in rows:
        hits = _hit_ids(row)
        weighed.append(
            {
                "store_id": str(row["store_id"]),
                "hits": hits,
                "individual_weight": individual_weight(hits, common),
                "total_weight": total_weight(hits),
            }
        )
    return tuple(weighed)


def _drills(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        for metric_id in _hit_ids(row):
            if metric_id in seen:
                continue
            seen.add(metric_id)
            found.append(
                {
                    "metric_id": metric_id,
                    "route": drill_route(metric_id),
                    "mark": undrillable_mark(metric_id),
                }
            )
    return tuple(found)


def _groups(
    rows: Sequence[Mapping[str, Any]],
    common: frozenset[str],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {name: [] for name in _PRIORITIES}
    for row in _ranked_individuals(rows, common):
        hits = _hit_ids(row)
        priority = individual_priority(individual_weight(hits, common), float(row["score"]))
        grouped[priority].append(str(row["store_id"]))
    return {name: tuple(grouped[name]) for name in _PRIORITIES}


def _top5(rows: Sequence[Mapping[str, Any]], common: frozenset[str]) -> tuple[str, ...]:
    ranked = _ranked_individuals(rows, common)
    return tuple(str(row["store_id"]) for row in ranked[:5])


def _ranked_individuals(
    rows: Sequence[Mapping[str, Any]],
    common: frozenset[str],
) -> list[Mapping[str, Any]]:
    ranked = [row for row in rows if row["role"] == "individual"]
    ranked.sort(key=lambda row: _rank_key(row, common))
    return ranked


def _rank_key(row: Mapping[str, Any], common: frozenset[str]) -> tuple[float, float, float]:
    hits = _hit_ids(row)
    return (
        -individual_weight(hits, common),
        -total_weight(hits),
        float(row["score"]),
    )


def _common_names(
    rows: Sequence[Mapping[str, Any]],
    common: frozenset[str],
) -> tuple[str, ...]:
    ranked: list[tuple[float, str]] = []
    for metric_id in common:
        name = metric_name(metric_id)
        eligible = 0
        hits = 0
        for row in rows:
            values = row["values"]
            present = isinstance(values, Mapping) and name in values
            if counts_toward_common_denominator(present, False):
                eligible += 1
            row_hits = row["hits"]
            if isinstance(row_hits, tuple) and metric_id in row_hits:
                hits += 1
        rate = common_hit_rate(hits, eligible) if eligible else 0
        ranked.append((impact(metric_weight_percent(metric_id), rate), name))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return tuple(name for _score, name in ranked)


def _body(
    rows: Sequence[Mapping[str, Any]],
    common: frozenset[str],
    numbers: Sequence[float],
) -> str:
    groups = _groups(rows, common)
    lines = [report_sections()[0]]
    lines.append(report_sections()[1])
    common_names = _common_names(rows, common)
    for index, name in enumerate(common_names):
        mark = "⭐ " if index == 0 else ""
        lines.append(f"{mark}{name}")
    lines.append(report_sections()[2])
    for priority in _PRIORITIES:
        joined = "、".join(groups[priority])
        lines.append(f"{priority} {joined}".rstrip())
    lines.append("Top5 " + "、".join(_top5(rows, common)))
    lines.append(report_sections()[3])
    common_stores = [
        row
        for row in rows
        if isinstance(row["hits"], tuple) and any(metric_id in common for metric_id in row["hits"])
    ]
    common_stores.sort(key=lambda row: float(row["score"]))
    for row in common_stores:
        score = float(row["score"])
        band = score_band(score)
        hint = " 高危提示" if score < 3.5 else ""
        lines.append(f"{row['store_id']} {row['score']} {band}{hint}")
    lines.append(report_sections()[4])
    for name in common_names:
        lines.append(f"整改 {name}")
    lines.append(report_sections()[5])
    for row in _ranked_individuals(rows, common)[:5]:
        lines.append(str(row["store_id"]))
        for metric_id in _hits_by_weight(row):
            lines.append(_evidence_line(row, metric_id))
    for number in numbers:
        lines.append(str(number))
    for row in rows:
        status = str(row["status"])
        if status in _APPENDIX:
            lines.append(f"{status} {row['store_id']}")
    return "\n".join(lines)


def _hits_by_weight(row: Mapping[str, Any]) -> tuple[str, ...]:
    order = {metric_id: index for index, metric_id in enumerate(metric_ids())}
    hits = list(_hit_ids(row))
    hits.sort(key=lambda metric_id: (-metric_weight_percent(metric_id), order[metric_id]))
    return tuple(hits)


def _evidence_line(row: Mapping[str, Any], metric_id: str) -> str:
    name = metric_name(metric_id)
    values = row["values"]
    raw: object = ""
    if isinstance(values, Mapping):
        raw = values.get(name, "")
    route = drill_route(metric_id)
    if route in _DETAIL_SHEETS:
        tail = f"sheet {route}"
    else:
        tail = undrillable_mark(metric_id) or "无明细下钻能力"
    limit = chosen_detail_limit()
    return f"{name} 指标值 {raw} 明细条数 {limit} {tail}"
