"""六个售后类名已拍板。9-未分类不进入元组。"""

from __future__ import annotations

from pathlib import Path

from octop.infra.diagnosis.hit_weights import after_sales_class_names as hit_after_sales_class_names
from octop.infra.diagnosis.symptom_engine import (
    after_sales_class_names as symptom_after_sales_class_names,
)

AFTER_SALES_CLASS_NAMES = (
    "1-物流履约",
    "2-产品满意度",
    "3-商品价格",
    "4-店铺原因",
    "5-平台原因",
    "6-其他原因",
)
DECIDED_AFTER_SALES = (
    "已拍板：六个售后类名依次是 1-物流履约、2-产品满意度、3-商品价格、"
    "4-店铺原因、5-平台原因、6-其他原因；9-未分类只作 SQL ELSE 回退，不进入元组。"
)
_CHANGE = Path(__file__).resolve().parents[3] / "openspec" / "changes" / "add-store-diagnosis"
_DOC_PATHS = (
    _CHANGE / "specs" / "diagnosis-fetch-fields" / "spec.md",
    _CHANGE / "design.md",
    _CHANGE / "tasks.md",
)


def test_after_sales_class_names_are_the_six_decided_labels() -> None:
    """元组按顺序给出六个类名。规格、设计和任务不再把这份名单标成阻断。"""
    assert symptom_after_sales_class_names() == AFTER_SALES_CLASS_NAMES
    assert hit_after_sales_class_names() == AFTER_SALES_CLASS_NAMES
    assert "9-未分类" not in symptom_after_sales_class_names()
    assert "9-未分类" not in hit_after_sales_class_names()

    for path in _DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert DECIDED_AFTER_SALES in text
        assert "六个售后类名仍阻断" not in text
        assert "类名清单阻断" not in text
        assert "六个售后类名仍不编造" not in text
        assert "也不编造六个售后类名" not in text
