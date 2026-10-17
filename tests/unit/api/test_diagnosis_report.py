"""RED contract for reading a diagnosis report without changing existing paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.support.app import octop_client
from tests.support.auth import TEST_PASSWORD, auth_header, bootstrap_admin, create_user

from octop.infra.diagnosis.snapshot_store import build_snapshot, write_snapshot
from octop.infra.diagnosis.symptom_engine import score_band

_CREATE = "/api/diagnosis/runs"


@pytest.fixture
async def diagnosis_http(tmp_octop_home: Path) -> Any:
    async with octop_client(tmp_octop_home) as (client, _srv):
        await bootstrap_admin(client, tmp_octop_home)
        admin = await auth_header(client)
        user_a = await create_user(client, admin, username="ada", password=TEST_PASSWORD)
        yield client, user_a


async def test_report_route_keeps_existing_paths(diagnosis_http: Any) -> None:
    """新增读取报告的路径。创建、列表、详情、取消的路径还在。"""
    client, _user_a = diagnosis_http
    paths = client._octop_app.openapi()["paths"]
    assert "/api/diagnosis/runs/{run_id}/report" in paths
    operation = paths["/api/diagnosis/runs/{run_id}/report"]["get"]
    assert operation["summary"]
    for path, method in (
        ("/api/diagnosis/runs", "post"),
        ("/api/diagnosis/runs", "get"),
        ("/api/diagnosis/runs/{run_id}", "get"),
        ("/api/diagnosis/runs/{run_id}/cancel", "post"),
    ):
        assert paths[path][method]["summary"]


async def test_background_run_reads_snapshot_files(diagnosis_http: Any, tmp_path: Path) -> None:
    """创建请求立刻返回。快照从文件读取，流程 A 的 llm_calls 仍是 0。"""
    client, user_a = diagnosis_http
    data_dir = tmp_path / "snaps"
    document = build_snapshot(
        shop="healthy",
        subject="主体",
        owner="负责人",
        mall_check_score=4.5,
        perf_score=4.5,
        score_level=score_band(4.5),
        rows=(
            {"performance_indicator": "用户评价分", "indicator_data_detail": 4.5},
            {"performance_indicator": "延迟发货率", "indicator_data_detail": 0.01},
        ),
    )
    write_snapshot(str(data_dir), "healthy", document)
    created = await client.post(
        _CREATE,
        headers=user_a,
        json={
            "client_request_id": "fixture-bg",
            "stores": ["healthy"],
            "window_start": "2026-10-09",
            "window_end": "2026-10-15",
            "preload_status": "COMPLETED",
            "row_count": 1,
            "snapshot_text": "",
            "data_dir": str(data_dir),
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["stage"] == "PREPARING"
    assert body["llm_calls"] == 0
    assert body["conclusion"] == ""
    from octop.infra.diagnosis import fixture_run

    await fixture_run.wait_fixture(body["run_id"])
    report = await client.get(f"{_CREATE}/{body['run_id']}/report", headers=user_a)
    assert report.status_code == 200
    payload = report.json()
    assert payload["llm_calls"] == 0
    assert payload["numbers"]
    assert set(payload["numbers"]) <= {4.5, 0.01}
