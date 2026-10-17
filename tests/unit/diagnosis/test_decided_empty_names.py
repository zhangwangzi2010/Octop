"""策略额外指标名与履约宽表列名已拍板为空。六个售后类名仍阻断。"""

from __future__ import annotations

from pathlib import Path

from octop.infra.diagnosis.fetch_catalog import (
    product_strategy_dimensions,
    product_strategy_metric_names,
)
from octop.infra.diagnosis.hit_weights import (
    after_sales_class_names as hit_after_sales_class_names,
)
from octop.infra.diagnosis.hit_weights import (
    fulfillment_column_names as hit_fulfillment_column_names,
)
from octop.infra.diagnosis.hit_weights import (
    strategy_metric_names as hit_strategy_metric_names,
)
from octop.infra.diagnosis.l1_semantic import strategy_metric_names as l1_strategy_metric_names
from octop.infra.diagnosis.symptom_engine import (
    after_sales_class_names as symptom_after_sales_class_names,
)
from octop.infra.diagnosis.symptom_engine import (
    fulfillment_column_names as symptom_fulfillment_column_names,
)
from octop.infra.diagnosis.symptom_engine import (
    strategy_metric_names as symptom_strategy_metric_names,
)

DECIDED_STRATEGY = "已拍板：额外指标名为空；策略切片只用 SPU 概览三列"
DECIDED_FULFILLMENT = "已拍板：履约 139 列为空 / 无此宽表"
STRATEGY_DIMENSIONS = ("原创款", "跟卖款", "裂变款")
_CHANGE = Path(__file__).resolve().parents[3] / "openspec" / "changes" / "add-store-diagnosis"
_DOC_PATHS = (
    _CHANGE / "specs" / "diagnosis-fetch-fields" / "spec.md",
    _CHANGE / "design.md",
    _CHANGE / "tasks.md",
)


def test_strategy_and_fulfillment_empties_are_decided() -> None:
    """空元组是已拍板结果。规格、设计、任务写明两句结论，售后类名仍不关闭。"""
    assert product_strategy_dimensions() == STRATEGY_DIMENSIONS
    assert product_strategy_metric_names() == ()
    assert l1_strategy_metric_names() == ()
    assert symptom_strategy_metric_names() == ()
    assert hit_strategy_metric_names() == ()
    assert symptom_fulfillment_column_names() == ()
    assert hit_fulfillment_column_names() == ()
    assert symptom_after_sales_class_names() == ()
    assert hit_after_sales_class_names() == ()

    for path in _DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert DECIDED_STRATEGY in text
        assert DECIDED_FULFILLMENT in text
        assert "指标名待补" not in text
        assert "商品策略指标名待补" not in text
        assert "139 列待补" not in text
        assert "列名待完整清单" not in text
        assert "履约表 139 个列名" not in text
        assert "已拍板：六个售后类名" not in text
