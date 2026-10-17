"""L1 fetch mapping onto the semantic layer.

Six acceptance constants only. Strategy metric names, fulfillment columns,
and after-sales class names are not listed. Derived display values have no
frozen formula.
"""

from __future__ import annotations

_OVERALL_DECLINE_FIELDS: tuple[str, ...] = (
    "sales_amount",
    "sales_quantity",
    "order_count",
)
_SLICE_KINDS: tuple[str, ...] = ("品类", "售龄", "策略", "Top")
_SLICE_OVERVIEW_FIELDS: tuple[str, ...] = (
    "spu_sold_amount",
    "spu_sold_quantity",
    "spu_order_count",
)
_AGE_BANDS: tuple[str, ...] = ("0–10", "11–29", "30–89", "≥90")
_YELLOW_METRICS: tuple[str, ...] = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
_DERIVED_LABEL = "派生在诊断侧、语义层无同名 metric"


def overall_decline_source() -> str:
    """Order-detail table for GMV, quantity, and order count."""
    return "订单明细"


def overall_decline_fields() -> tuple[str, ...]:
    """Fields read for an overall decline."""
    return _OVERALL_DECLINE_FIELDS


def slice_kinds() -> tuple[str, ...]:
    """Slices that read the SPU overview."""
    return _SLICE_KINDS


def slice_overview_fields() -> tuple[str, ...]:
    """Shared SPU overview measures. Slice-specific names stay elsewhere."""
    return _SLICE_OVERVIEW_FIELDS


def strategy_metric_names() -> tuple[str, ...]:
    """Decided empty. Strategy slices use the three SPU overview columns."""
    return ()


def top_slice_extra_metric_ids() -> tuple[str, ...]:
    """Empty. Top has no extra unnamed metric id."""
    return ()


def active_spu_metric() -> str:
    """Active-SPU count."""
    return "active_spu_count"


def on_sale_spu_metric() -> str:
    """On-sale SPU count."""
    return "on_sale_spu_count"


def category_dimension() -> str:
    """Category dimension on the SPU overview."""
    return "spu_category"


def age_clock_field() -> str:
    """Column subtracted from the current time to get selling age."""
    return "ads_bi_temu_spu_overview_self_df.min_first_join_time"


def age_is_difference_from_now() -> bool:
    """Selling age is that column's difference from the current time."""
    return True


def age_bands() -> tuple[str, ...]:
    """Four selling-age bands, in days. Day 30 is not one of these labels."""
    return _AGE_BANDS


def day_30_age_band() -> str:
    """Recorded band for day 30. It is not computed from a formula."""
    return "30–90"


def age_active_rate_metric() -> str:
    """Sell-through rate used inside a selling-age band."""
    return "ecommerce.metric.active_spu_rate"


def age_active_rate_filters_by_band() -> bool:
    """The sell-through rate is filtered by selling-age band."""
    return True


def yellow_metric_names() -> tuple[str, ...]:
    """The five yellow metrics. Nothing is added or substituted."""
    return _YELLOW_METRICS


def yellow_is_queried(name: str) -> bool:
    """Yellow metrics are not queried."""
    del name
    return False


def yellow_is_substituted(name: str) -> bool:
    """Yellow metrics are not replaced with another metric."""
    del name
    return False


def yellow_gap_mark() -> str:
    """Mark used when a yellow metric is judged or attributed."""
    return "指标及相关明细空缺"


def derived_value_label(kind: str) -> str:
    """Label for 环比, 贡献, and 权重. No semantic-layer metric is named."""
    del kind
    return _DERIVED_LABEL


def derived_formula(kind: str) -> None:
    """No period-over-period, contribution, or weight formula is frozen."""
    del kind
    return None
