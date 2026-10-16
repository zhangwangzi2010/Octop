"""RED contracts for the diagnosis run repo (WT-1 tasks 2.2–2.4).

The production module ``octop.infra.db.repos.diagnosis_runs`` is intentionally
absent. These tests fail on that missing behavior. They do not add the module,
migration SQL, or a stand-in that would pass.

Expected public surface once the module exists:

- ``DiagnosisRunsRepo.create_run`` / ``get_by_client_request_id``
- ``DiagnosisRunsRepo.list_runs_for_owner``
- ``DiagnosisRunsRepo.create_item`` / ``get_item`` / ``reset_orphan_items``
- ``DiagnosisRunsRepo.append_event`` / ``list_events``

Item status strings used by the crash case come from kickoff design context.
Feishu acceptance text was not readable, so they are not a frozen product enum.
"""

from __future__ import annotations

import importlib
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

import pytest
from tests.support.diagnosis_contract import (
    IN_FLIGHT_ITEM_STATUSES,
    RESUMABLE_ITEM_STATUS,
    TERMINAL_ITEM_STATUSES,
)

from octop.infra.db.migrate import run_migrations
from octop.infra.db.pool import SqlitePool
from octop.infra.db.repos.users import UserRepo


@pytest.fixture
def db(tmp_path: Path) -> SqlitePool:
    pool = SqlitePool(tmp_path / "octop.db")
    run_migrations(pool)
    return pool


def test_client_request_id_lookup_returns_the_same_run(db: SqlitePool) -> None:
    repo = _repo(db)
    owner_id = _user(db, "owner-lookup")
    created = _call(
        _method(repo, "create_run"),
        run_id="run-lookup",
        owner_user_id=owner_id,
        client_request_id="req-lookup",
    )
    found = _call(_method(repo, "get_by_client_request_id"), "req-lookup")
    assert found is not None
    assert _field(found, "run_id") == _field(created, "run_id") == "run-lookup"
    assert _field(found, "client_request_id") == "req-lookup"
    assert _field(found, "owner_user_id") == owner_id


def test_list_runs_filters_by_owner(db: SqlitePool) -> None:
    repo = _repo(db)
    owner_a = _user(db, "owner-a")
    owner_b = _user(db, "owner-b")
    _call(
        _method(repo, "create_run"),
        run_id="run-a",
        owner_user_id=owner_a,
        client_request_id="req-a",
    )
    _call(
        _method(repo, "create_run"),
        run_id="run-b",
        owner_user_id=owner_b,
        client_request_id="req-b",
    )
    visible = _call(_method(repo, "list_runs_for_owner"), owner_a)
    assert {_field(row, "run_id") for row in visible} == {"run-a"}
    assert all(_field(row, "owner_user_id") == owner_a for row in visible)


def test_reset_orphan_items_resumes_inflight_after_crash(db: SqlitePool) -> None:
    """In-flight items become resumable; terminal items stay put."""
    repo = _repo(db)
    owner_id = _user(db, "owner-crash")
    _call(
        _method(repo, "create_run"),
        run_id="run-crash",
        owner_user_id=owner_id,
        client_request_id="req-crash",
    )
    _call(
        _method(repo, "create_item"),
        item_id="item-preparing",
        run_id="run-crash",
        store_id="store-1",
        attempt=1,
        status="PREPARING",
    )
    _call(
        _method(repo, "create_item"),
        item_id="item-diagnosing",
        run_id="run-crash",
        store_id="store-2",
        attempt=1,
        status="DIAGNOSING",
    )
    for status in sorted(TERMINAL_ITEM_STATUSES):
        _call(
            _method(repo, "create_item"),
            item_id=f"item-{status.lower()}",
            run_id="run-crash",
            store_id=f"store-{status.lower()}",
            attempt=1,
            status=status,
        )

    _call(_method(repo, "reset_orphan_items"))

    for status in IN_FLIGHT_ITEM_STATUSES:
        item_id = "item-preparing" if status == "PREPARING" else "item-diagnosing"
        row = _call(_method(repo, "get_item"), item_id)
        assert row is not None
        assert _field(row, "status") == RESUMABLE_ITEM_STATUS
    for status in TERMINAL_ITEM_STATUSES:
        row = _call(_method(repo, "get_item"), f"item-{status.lower()}")
        assert row is not None
        assert _field(row, "status") == status


def test_append_node_event_round_trip(db: SqlitePool) -> None:
    repo = _repo(db)
    owner_id = _user(db, "owner-event")
    _call(
        _method(repo, "create_run"),
        run_id="run-event",
        owner_user_id=owner_id,
        client_request_id="req-event",
    )
    _call(
        _method(repo, "append_event"),
        run_id="run-event",
        item_id="item-event",
        node="analysis_run",
        event="started",
        detail="{}",
    )
    events = _call(_method(repo, "list_events"), "run-event")
    assert len(events) == 1
    assert _field(events[0], "run_id") == "run-event"
    assert _field(events[0], "item_id") == "item-event"
    assert _field(events[0], "node") == "analysis_run"
    assert _field(events[0], "event") == "started"
    assert _field(events[0], "detail") == "{}"


def _repo(db: SqlitePool) -> Any:
    try:
        module = importlib.import_module("octop.infra.db.repos.diagnosis_runs")
    except ImportError as exc:
        _fail_absent(f"octop.infra.db.repos.diagnosis_runs is absent ({exc})")
    repo_cls = getattr(module, "DiagnosisRunsRepo", None)
    if repo_cls is None:
        _fail_absent("DiagnosisRunsRepo is absent")
    return repo_cls(db)


def _user(db: SqlitePool, username: str) -> int:
    return UserRepo(db).create(username=username, password_hash="x", role="user")


def _method(repo: Any, name: str) -> Any:
    method = getattr(repo, name, None)
    if not callable(method):
        _fail_absent(f"DiagnosisRunsRepo.{name} is absent")
    return method


def _call(method: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return method(*args, **kwargs)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            _fail_absent(str(exc))
        raise


def _field(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row[name]
    return getattr(row, name)


def _fail_absent(detail: str) -> NoReturn:
    pytest.fail(f"diagnosis schema is not migrated yet: {detail}")
