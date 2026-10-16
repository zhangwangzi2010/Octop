"""WT-3 contracts for /api/diagnosis/runs.

Routes are absent. These tests fail because create, list, detail, and cancel
are not mounted. Kickoff tasks §4 does not name a retry route. The tests do
not invent one, and they do not require a new diagnosis table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from tests.support.app import octop_client
from tests.support.auth import TEST_PASSWORD, auth_header, bootstrap_admin, create_user

from octop.infra.db.migrate import run_migrations
from octop.infra.db.pool import SqlitePool
from octop.infra.db.repos.diagnosis_runs import DiagnosisRunsRepo
from octop.infra.db.repos.users import UserRepo
from octop.infra.errors import ErrorCode, OctopError

_CREATE = "/api/diagnosis/runs"


@pytest.fixture
async def diagnosis_http(
    tmp_octop_home: Path,
) -> Any:
    async with octop_client(tmp_octop_home) as (client, _srv):
        await bootstrap_admin(client, tmp_octop_home)
        admin = await auth_header(client)
        user_a = await create_user(client, admin, username="ada", password=TEST_PASSWORD)
        user_b = await create_user(client, admin, username="bea", password=TEST_PASSWORD)
        yield client, admin, user_a, user_b


def test_client_request_lookup_rejects_a_different_owner(tmp_path: Path) -> None:
    """get_by_client_request_id 跨 owner 时拒绝，且不带回别人的 run。"""
    pool = SqlitePool(tmp_path / "octop.db")
    run_migrations(pool)
    repo = DiagnosisRunsRepo(pool)
    owner_a = UserRepo(pool).create(username="ada", password_hash="x", role="user")
    owner_b = UserRepo(pool).create(username="bea", password_hash="x", role="user")
    repo.create_run(run_id="run-a", owner_user_id=owner_a, client_request_id="req-a")
    with pytest.raises(OctopError) as caught:
        repo.get_by_client_request_id("req-a", owner_user_id=owner_b)
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert "run-a" not in caught.value.message
    own = repo.get_by_client_request_id("req-a", owner_user_id=owner_a)
    assert own is not None
    assert own.run_id == "run-a"


async def test_create_is_idempotent_and_reaches_flow_a(diagnosis_http: Any) -> None:
    """相同 client_request_id 返回同一个 run，并走到零 LLM 的流程 A。"""
    client, _admin, user_a, _user_b = diagnosis_http
    first = await _create(client, user_a, client_request_id="flow-a", stores=["s1"])
    assert first.status_code == 200
    body = first.json()
    assert body["stages"] == ["PREPARING", "ANALYZING", "COMPLETING", "COMPLETED"]
    assert body["stage"] == "COMPLETED"
    assert body["llm_calls"] == 0
    assert body["conclusion"] == "快照原文"
    assert body["failure_reason"] is None
    assert body["items"] == [{"store_id": "s1", "status": "OK"}]
    second = await _create(
        client,
        user_a,
        client_request_id="flow-a",
        stores=["s1", "s2"],
    )
    assert second.status_code == 200
    again = second.json()
    assert again["run_id"] == body["run_id"]
    assert [item["store_id"] for item in again["items"]] == ["s1"]


async def test_other_owner_cannot_reuse_client_request_id(diagnosis_http: Any) -> None:
    """别人的 client_request_id 返回 403，响应里没有对方的 run。"""
    client, _admin, user_a, user_b = diagnosis_http
    created = await _create(client, user_a, client_request_id="owned", stores=["s1"])
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    denied = await _create(client, user_b, client_request_id="owned", stores=["s9"])
    assert denied.status_code == 403
    assert run_id not in denied.text
    assert "快照原文" not in denied.text


async def test_list_detail_and_cancel_are_owner_scoped(diagnosis_http: Any) -> None:
    """列表、详情、取消按 owner 隔离；管理员可以查看全部。取消后终态是 CANCELLED。"""
    client, admin, user_a, user_b = diagnosis_http
    created = await _create(
        client,
        user_a,
        client_request_id="to-cancel",
        stores=["s1"],
        preload_status="RUNNING",
        row_count=4,
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert created.json()["stage"] == "PREPARING"

    listed = await client.get(_CREATE, headers=user_a)
    assert listed.status_code == 200
    assert [row["run_id"] for row in listed.json()] == [run_id]
    hidden = await client.get(_CREATE, headers=user_b)
    assert hidden.status_code == 200
    assert hidden.json() == []
    admin_list = await client.get(_CREATE, headers=admin)
    assert admin_list.status_code == 200
    assert run_id in [row["run_id"] for row in admin_list.json()]

    detail = await client.get(f"{_CREATE}/{run_id}", headers=user_b)
    assert detail.status_code == 403
    assert "快照原文" not in detail.text
    admin_detail = await client.get(f"{_CREATE}/{run_id}", headers=admin)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["run_id"] == run_id

    denied = await client.post(f"{_CREATE}/{run_id}/cancel", headers=user_b)
    assert denied.status_code == 403
    still = await client.get(f"{_CREATE}/{run_id}", headers=user_a)
    assert still.status_code == 200
    assert still.json()["stage"] == "PREPARING"

    cancelled = await client.post(f"{_CREATE}/{run_id}/cancel", headers=user_a)
    assert cancelled.status_code == 200
    assert cancelled.json()["stage"] == "CANCELLED"
    assert cancelled.json()["items"] == [{"store_id": "s1", "status": "CANCELLED"}]


async def test_openapi_routes_are_typed_and_have_no_retry(diagnosis_http: Any) -> None:
    """四条路由有 summary 和类型化响应。任务第 4 节没有重试路由。"""
    client, _admin, _user_a, _user_b = diagnosis_http
    schema = client._octop_app.openapi()
    paths = schema["paths"]
    for path, method in (
        ("/api/diagnosis/runs", "post"),
        ("/api/diagnosis/runs", "get"),
        ("/api/diagnosis/runs/{run_id}", "get"),
        ("/api/diagnosis/runs/{run_id}/cancel", "post"),
    ):
        operation = paths[path][method]
        assert operation["summary"]
        content = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert content
    model = schema["components"]["schemas"]["DiagnosisRunOut"]
    assert {
        "run_id",
        "stage",
        "items",
        "failure_reason",
        "llm_calls",
        "conclusion",
    } <= set(model["properties"])
    assert "/api/diagnosis/runs/{run_id}/retry" not in paths


async def _create(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    client_request_id: str,
    stores: list[str],
    preload_status: str = "COMPLETED",
    row_count: int = 1,
) -> httpx.Response:
    return await client.post(
        _CREATE,
        headers=headers,
        json={
            "client_request_id": client_request_id,
            "stores": stores,
            "window_start": "2026-10-09",
            "window_end": "2026-10-15",
            "preload_status": preload_status,
            "row_count": row_count,
            "snapshot_text": "快照原文",
        },
    )
