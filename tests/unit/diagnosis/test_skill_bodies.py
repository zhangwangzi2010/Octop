"""Skill bodies and the diagnosis expert are readable and injectable.

Bodies come from the locked constants. The routing table stays the
analysis_guide text. Threshold notes that are not acceptance constants,
SQL text, and external service addresses stay out.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from datetime import date
from typing import Any

import pytest

from octop.infra.agents.experts.catalog import (
    ExpertCatalog,
    build_create_spec_from_expert,
    default_library_root,
)
from octop.infra.diagnosis.flow_b import analysis_guide_body, soul_steps
from octop.infra.diagnosis.hit_weights import (
    after_sales_class_names,
    fulfillment_column_names,
    hit_rule,
    metric_ids,
    metric_name,
    metric_weight_percent,
    strategy_metric_names,
)
from octop.infra.diagnosis.l1_semantic import age_bands, yellow_metric_names
from octop.infra.diagnosis.promoted_contracts import detail_tables, q4_output_names
from octop.infra.diagnosis.snapshot_structure import q3_window, query_names
from octop.infra.diagnosis.symptom_engine import yellow_gap_mark

_SKILLS = ("metrics_catalog", "analysis_guide", "drilldown_playbook", "query_tasks")
_FORBIDDEN = (":8787", "≥2%", "SELECT ", "INSERT ", "access_key", "access_id")


def test_three_skill_bodies_use_locked_constants_and_reuse_the_guide() -> None:
    """metrics_catalog、drilldown、query_tasks 有正文。分流表不另写一套命中线。"""
    bodies = {name: _body(name) for name in _SKILLS}
    catalog = bodies["metrics_catalog"]
    playbook = bodies["drilldown_playbook"]
    tasks = bodies["query_tasks"]
    guide = analysis_guide_body()
    assert bodies["analysis_guide"] == guide
    assert guide in playbook
    assert "不另写命中线" in playbook
    for metric_id in metric_ids():
        line = (
            f"{metric_id} {metric_name(metric_id)} "
            f"权重 {metric_weight_percent(metric_id):g}% 命中 {hit_rule(metric_id)}"
        )
        assert line in catalog
        assert line in guide
    assert "≥10%" in catalog
    assert "唯一事实源" in catalog
    for name in yellow_metric_names():
        assert name in catalog
    assert yellow_gap_mark() in catalog
    assert "空" in catalog
    assert strategy_metric_names() == ()
    assert fulfillment_column_names() == ()
    for band in age_bands():
        assert band in catalog
    for label, table in detail_tables():
        assert label in playbook
        assert table in playbook
    for class_name in after_sales_class_names():
        assert class_name in playbook
    assert "9-未分类" in playbook
    for query in query_names():
        assert query in tasks
    assert len(q3_window(date(2026, 10, 19))) == 60
    assert "60" in tasks
    assert "不含今天" in tasks
    for short_name in q4_output_names():
        assert short_name in tasks
    assert "SQL" not in tasks or "不写 SQL" in tasks
    for body in bodies.values():
        for token in _FORBIDDEN:
            assert token not in body


def test_skill_files_match_the_renderer_and_the_catalog_can_read_them() -> None:
    """专家包里的 Skill 与加载结果相同，目录能读到 SOUL 和四份正文。"""
    module = _module()
    catalog = ExpertCatalog(default_library_root())
    catalog.refresh()
    expert = catalog.get("store-diagnosis")
    assert expert is not None
    contents = {
        item["name"]: item["content"] for item in catalog.read_file_contents("store-diagnosis")
    }
    soul = contents["SOUL.md"]
    assert soul == module.render_soul()
    cursor = -1
    for step in soul_steps():
        found = soul.find(step)
        assert found > cursor
        cursor = found
    for name in _SKILLS:
        rel = f"skills/{name}/SKILL.md"
        assert contents[rel] == module.render_skill_file(name)
        assert module.read_skill_body(name) == module.render_skill_body(name)
    spec = build_create_spec_from_expert(
        expert_id="store-diagnosis",
        expert=expert,
        user_id=1,
    )
    assert spec.template_name == "store-diagnosis"
    assert spec.name


def test_fake_llm_runs_the_interpretation_chain() -> None:
    """Callable 收到 SOUL 和四份 Skill，门禁通过。黄标仍不调用它。"""
    module = _module()
    seen: dict[str, Mapping[str, Any]] = {}

    def _fake(packet: Mapping[str, Any]) -> Mapping[str, Any]:
        seen["packet"] = packet
        return _conclusion("0.08")

    result = _mapping(
        module.diagnose_with_expert(
            run_id="run-skill",
            store_id="shop-a",
            attempt=1,
            slice_values=("0.08",),
            llm=_fake,
        )
    )
    packet = seen["packet"]
    assert packet["expert_id"] == "store-diagnosis"
    assert packet["steps"] == soul_steps()
    assert packet["soul"] == module.read_soul()
    loaded = tuple(packet["skills"])
    assert tuple(item["name"] for item in loaded) == _SKILLS
    assert result["result"] == "OK"
    assert result["status"] == "OK"
    assert result["llm_calls"] == 1
    assert result["stage1_llm_calls"] == 0
    assert result["threads"] == ("diag:run-skill:shop-a:a1",)
    skipped = _mapping(
        module.diagnose_with_expert(
            run_id="run-skill",
            store_id="shop-a",
            attempt=1,
            slice_values=("0.08",),
            metrics=yellow_metric_names(),
            llm=lambda _packet: pytest.fail("yellow metrics must not call the expert"),
        )
    )
    assert skipped["status"] == "SKIPPED"
    assert skipped["llm_calls"] == 0


def _body(name: str) -> str:
    module = _module()
    return str(module.render_skill_body(name))


def _conclusion(data_ref: str) -> dict[str, Any]:
    return {
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


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        pytest.fail("result did not return a mapping")
    return value


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.skill_bodies")
    except ImportError as exc:
        pytest.fail(f"skill_bodies is absent ({exc})")
