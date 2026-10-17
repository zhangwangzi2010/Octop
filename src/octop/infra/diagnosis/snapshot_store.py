"""Schema v2 snapshot files and the two-level fetch.

One JSON file per shop. Keys, table names, and display names come from the
promoted contracts and the diagnosis modules already on this branch. Yellow
metrics are not queried. This module does not call an LLM.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from octop.infra.diagnosis.fetch_catalog import (
    l1_age_displays,
    l1_display_names,
    l2_leaves,
    yellow_labels,
)
from octop.infra.diagnosis.hit_weights import (
    document_denominator,
    document_numerator,
    locked_metric_name,
    metric_ids,
    metric_name,
)
from octop.infra.diagnosis.l1_semantic import (
    active_spu_metric,
    age_active_rate_metric,
    category_dimension,
    on_sale_spu_metric,
    overall_decline_fields,
    slice_overview_fields,
    yellow_gap_mark,
)
from octop.infra.diagnosis.promoted_contracts import q4_physical_fields, snapshot_path
from octop.infra.diagnosis.remaining_contracts import chosen_score_field, score_field_alias
from octop.infra.diagnosis.snapshot_json import (
    metric_json_keys,
    metric_value_keys,
    snapshot_shape_fields,
    store_performance_fields,
)

_PERFORMANCE_TABLE = "ai_nlsql.dwd_sto_temu_store_performance_df"
_PERFORMANCE_PARTITION = "ds=max_pt"
_PERFORMANCE_BUSINESS_TIME = "business_date"
_PERFORMANCE_ROW_KEY = "performance_indicator"
_PERFORMANCE_STORE_KEYS = ("store_id", "store_name")
_FULFILLMENT_SIDE_KEYS = ("shop_id", "shop_name")
_FULFILLMENT_TIME_FIELDS = ("order_time", "pay_time")
_OVERALL_COUNT = 6
_TOP_COUNT = 11


def performance_table() -> str:
    """Performance fact table named in the promoted contract."""
    return _PERFORMANCE_TABLE


def performance_partition() -> str:
    """Partition predicate written for that table."""
    return _PERFORMANCE_PARTITION


def performance_business_time() -> str:
    """Business-time column on the performance table."""
    return _PERFORMANCE_BUSINESS_TIME


def performance_row_key() -> str:
    """Row key that holds a second-level metric name."""
    return _PERFORMANCE_ROW_KEY


def performance_store_keys() -> tuple[str, str]:
    """Store keys on the performance table."""
    return _PERFORMANCE_STORE_KEYS


def fulfillment_side_keys() -> tuple[str, str]:
    """Shop keys on the fulfillment table. They are not ``store_id``."""
    return _FULFILLMENT_SIDE_KEYS


def fulfillment_time_fields() -> tuple[str, str]:
    """Time fields written for the fulfillment table."""
    return _FULFILLMENT_TIME_FIELDS


def fulfillment_has_business_date() -> bool:
    """The fulfillment table has no ``business_date`` column."""
    return False


def documented_ratio_fields(name: str) -> tuple[str, ...]:
    """Numerator and denominator already written for one metric.

    Only 延迟发货率 and 延迟到货率 have those fields. The other fulfillment
    columns are not listed.
    """
    for metric_id in metric_ids():
        if metric_name(metric_id) != name:
            continue
        numerator = document_numerator(metric_id)
        denominator = document_denominator(metric_id)
        if numerator is None or denominator is None:
            return ()
        return (numerator, denominator)
    return ()


def build_snapshot(
    *,
    shop: str,
    subject: str,
    owner: str,
    mall_check_score: float,
    perf_score: float,
    score_level: str,
    rows: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a schema v2 document from performance rows.

    Physical columns are read off the row. The snapshot stores Q4 short
    names under the kickoff JSON key. ``mall_check_score`` stays the
    canonical score and ``perf_score`` stays the shape alias.
    """
    metrics = _blank_metrics()
    allowed = set(metric_json_keys())
    row_key = performance_row_key()
    for row in rows:
        indicator = row.get(row_key)
        if not isinstance(indicator, str) or indicator not in allowed:
            continue
        for physical, short in _physical_pairs():
            if physical in row:
                metrics[indicator][short] = _passthrough(row[physical])
        if "prev" in row:
            stored_prev = _passthrough(row["prev"])
            if stored_prev is not None:
                metrics[indicator]["prev"] = stored_prev
    return _document(shop, subject, owner, mall_check_score, perf_score, score_level, metrics)


def write_snapshot(data_dir: str, shop_id: str, document: Mapping[str, Any]) -> str:
    """Write one schema v2 file. The path has no version segment."""
    path = snapshot_path(data_dir, shop_id)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = _normalize(document)
    destination.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def read_snapshot(data_dir: str, shop_id: str) -> dict[str, Any]:
    """Read the schema v2 file for one shop."""
    raw: Any = json.loads(Path(snapshot_path(data_dir, shop_id)).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("snapshot is not an object")
    return {str(key): value for key, value in raw.items()}


def two_level_fetch(
    document: Mapping[str, Any],
    sources: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Read level-1 displays and level-2 leaves from a schema v2 document.

    ``sources`` may hold semantic-field numbers. Derived displays do not
    turn those numbers into a value, and the age sell-through rate is not
    copied onto a display band.
    """
    del sources
    normalized = _normalize(document)
    performance = normalized["store_performance"]
    metrics = performance["metrics"]
    if not isinstance(metrics, Mapping):
        metrics = {}
    return {
        "level1": _level1(),
        "level2": _level2(metrics),
        "yellow": tuple(_yellow_item(label, "") for label in yellow_labels()),
    }


def read_store_fetch(data_dir: str, shop_id: str) -> dict[str, Any]:
    """Read one shop file and project it onto the two-level names."""
    return two_level_fetch(read_snapshot(data_dir, shop_id))


def _document(
    shop: str,
    subject: str,
    owner: str,
    mall_check_score: Any,
    perf_score: Any,
    score_level: Any,
    metrics: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    shop_key, subject_key, owner_key, performance_key = _shape_keys()
    return {
        shop_key: shop,
        subject_key: subject,
        owner_key: owner,
        performance_key: _performance(mall_check_score, perf_score, score_level, metrics),
    }


def _performance(
    mall_check_score: Any,
    perf_score: Any,
    score_level: Any,
    metrics: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    shape_perf, shape_level, shape_metrics = _performance_keys()
    return {
        chosen_score_field(): mall_check_score,
        shape_perf: perf_score,
        shape_level: score_level,
        shape_metrics: metrics,
    }


def _normalize(document: Mapping[str, Any]) -> dict[str, Any]:
    shop_key, subject_key, owner_key, performance_key = _shape_keys()
    raw_performance = document.get(performance_key)
    performance = raw_performance if isinstance(raw_performance, Mapping) else {}
    shape_perf, shape_level, shape_metrics = _performance_keys()
    raw_metrics = performance.get(shape_metrics)
    return _document(
        _text(document.get(shop_key)),
        _text(document.get(subject_key)),
        _text(document.get(owner_key)),
        performance.get(chosen_score_field()),
        performance.get(shape_perf, performance.get(score_field_alias())),
        performance.get(shape_level),
        _metrics_from(raw_metrics if isinstance(raw_metrics, Mapping) else None),
    )


def _metrics_from(raw: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    metrics = _blank_metrics()
    if raw is None:
        return metrics
    for key in metric_json_keys():
        incoming = raw.get(key)
        if not isinstance(incoming, Mapping):
            continue
        for short in metric_value_keys():
            if short in incoming:
                metrics[key][short] = _passthrough(incoming[short])
        if "prev" in incoming:
            stored_prev = _passthrough(incoming["prev"])
            if stored_prev is not None:
                metrics[key]["prev"] = stored_prev
    return metrics


def _blank_metrics() -> dict[str, dict[str, Any]]:
    return {key: dict.fromkeys(metric_value_keys()) for key in metric_json_keys()}


def _physical_pairs() -> tuple[tuple[str, str], ...]:
    """Pair each physical column with the Q4 short name on the same spec row."""
    physical = tuple(name for name, _purpose in q4_physical_fields())
    return tuple(zip(physical, metric_value_keys(), strict=True))


def _level1() -> tuple[dict[str, Any], ...]:
    names = l1_display_names()
    overall = set(names[:_OVERALL_COUNT])
    top = set(names[_OVERALL_COUNT : _OVERALL_COUNT + _TOP_COUNT])
    items: list[dict[str, Any]] = []
    for name in names:
        if name in top:
            items.append(_open_item(name, "Top", "", slice_overview_fields(), derived=True))
        elif name in overall:
            items.append(_open_item(name, "", "", _overall_fields(name), derived=True))
        else:
            fields = (*slice_overview_fields(), category_dimension())
            items.append(_open_item(name, "品类", "", fields, derived=True))
    for band, metric in l1_age_displays():
        if metric == "动销率":
            items.append(
                _open_item(metric, "售龄", band, (age_active_rate_metric(),), derived=False)
            )
        else:
            items.append(_open_item(metric, "售龄", band, slice_overview_fields(), derived=True))
    return tuple(items)


def _overall_fields(name: str) -> tuple[str, ...]:
    decline = overall_decline_fields()
    if name == "GMV环比下滑幅度":
        return (decline[0],)
    if name == "销量环比下滑幅度":
        return (decline[1],)
    if name == "订单量下滑占比":
        return (decline[2],)
    if name == "动销SPU下滑占比":
        return (active_spu_metric(),)
    if name == "在售SPU下滑占比":
        return (on_sale_spu_metric(),)
    return ()


def _level2(metrics: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    yellow = set(yellow_labels())
    keys = set(metric_json_keys())
    items: list[dict[str, Any]] = []
    for checklist, leaf in l2_leaves():
        if leaf in yellow:
            items.append(_yellow_item(leaf, checklist))
            continue
        resolved = locked_metric_name(leaf)
        incoming = metrics.get(resolved) if isinstance(resolved, str) else None
        if isinstance(resolved, str) and resolved in keys and isinstance(incoming, Mapping):
            items.append(_metric_item(checklist, leaf, incoming))
            continue
        items.append(_gap_item(checklist, leaf))
    return tuple(items)


def _metric_item(group: str, name: str, metric: Mapping[str, Any]) -> dict[str, Any]:
    details = tuple((short, _passthrough(metric.get(short))) for short in metric_value_keys())
    latest = _passthrough(metric.get("latest"))
    value = latest if isinstance(latest, (int, float)) else None
    return _item(
        name=name,
        group=group,
        band="",
        queried=True,
        skipped=False,
        value=value,
        details=details,
        mark="",
        fields=(),
        derived=False,
    )


def _open_item(
    name: str,
    group: str,
    band: str,
    fields: tuple[str, ...],
    *,
    derived: bool,
) -> dict[str, Any]:
    return _item(
        name=name,
        group=group,
        band=band,
        queried=bool(fields),
        skipped=False,
        value=None,
        details=(),
        mark="",
        fields=fields,
        derived=derived,
    )


def _gap_item(group: str, name: str) -> dict[str, Any]:
    return _item(
        name=name,
        group=group,
        band="",
        queried=False,
        skipped=False,
        value=None,
        details=(),
        mark="",
        fields=(),
        derived=False,
    )


def _yellow_item(name: str, group: str) -> dict[str, Any]:
    return _item(
        name=name,
        group=group,
        band="",
        queried=False,
        skipped=True,
        value=None,
        details=(),
        mark=yellow_gap_mark(),
        fields=(),
        derived=False,
    )


def _item(
    *,
    name: str,
    group: str,
    band: str,
    queried: bool,
    skipped: bool,
    value: float | None,
    details: tuple[tuple[str, Any], ...] | tuple[()],
    mark: str,
    fields: tuple[str, ...],
    derived: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "group": group,
        "band": band,
        "queried": queried,
        "skipped": skipped,
        "value": value,
        "details": details,
        "mark": mark,
        "fields": fields,
        "derived": derived,
    }


def _shape_keys() -> tuple[str, str, str, str]:
    fields = snapshot_shape_fields()
    return (fields[0], fields[1], fields[2], fields[3])


def _performance_keys() -> tuple[str, str, str]:
    fields = store_performance_fields()
    return (fields[0], fields[1], fields[2])


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _passthrough(value: Any) -> Any:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
