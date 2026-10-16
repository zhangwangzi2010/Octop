"""Unreleased store-diagnosis schema contract (migration 021, watermark v21).

Shipped databases stay at v20 until this pair exists. 022 and 023 are not
expected: unreleased diagnosis DDL folds into the single next version below.
"""

from __future__ import annotations

import sqlite3

from octop.infra.db.migrate import _discover
from octop.infra.db.pool import SqlitePool

# The only diagnosis watermark. Change this one name if the unreleased number moves.
DIAGNOSIS_SCHEMA_VERSION = 21

DIAG_RUNS_COLUMNS = frozenset(
    {
        "id",
        "run_id",
        "owner_user_id",
        "client_request_id",
        "status",
        "report_ref",
    }
)
DIAG_RUN_ITEMS_COLUMNS = frozenset(
    {
        "id",
        "item_id",
        "run_id",
        "store_id",
        "attempt",
        "status",
        "slice_ref",
    }
)
DIAG_NODE_EVENTS_COLUMNS = frozenset(
    {
        "run_id",
        "item_id",
        "node",
        "event",
        "detail",
        "ts",
    }
)

# Kickoff design context (Feishu body was unread). Not a frozen acceptance enum.
IN_FLIGHT_ITEM_STATUSES = frozenset({"PREPARING", "DIAGNOSING"})
RESUMABLE_ITEM_STATUS = "PENDING"
TERMINAL_ITEM_STATUSES = frozenset({"OK", "FAILED", "SKIPPED"})


def diagnosis_schema_gaps(db: SqlitePool) -> list[str]:
    """Return why the migrated SQLite schema is not the diagnosis contract yet."""
    gaps: list[str] = []
    version_label = f"{DIAGNOSIS_SCHEMA_VERSION:03d}"
    sqlite_files = [
        path.name for version, path in _discover("sqlite") if version == DIAGNOSIS_SCHEMA_VERSION
    ]
    pg_files = [
        path.name
        for version, path in _discover("postgresql")
        if version == DIAGNOSIS_SCHEMA_VERSION
    ]
    if len(sqlite_files) != 1 or len(pg_files) != 1:
        gaps.append(
            "missing unreleased migration pair "
            f"{version_label}_*.sql and {version_label}_*.pg.sql "
            f"(found sqlite={sqlite_files or 'none'}, postgresql={pg_files or 'none'})"
        )
    with db.connect() as conn:
        version = int(conn.execute("SELECT version FROM _schema_version").fetchone()[0])
        if version != DIAGNOSIS_SCHEMA_VERSION:
            gaps.append(f"schema version is {version}, expected {DIAGNOSIS_SCHEMA_VERSION}")
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        _require_table(conn, tables, "diag_runs", DIAG_RUNS_COLUMNS, gaps)
        _require_table(conn, tables, "diag_run_items", DIAG_RUN_ITEMS_COLUMNS, gaps)
        _require_table(conn, tables, "diag_node_events", DIAG_NODE_EVENTS_COLUMNS, gaps)
        if "diag_runs" in tables and not _has_unique_covering(
            conn, "diag_runs", frozenset({"client_request_id"})
        ):
            gaps.append("diag_runs has no unique index covering client_request_id")
        if "diag_runs" in tables and not _has_unique_covering(
            conn, "diag_runs", frozenset({"run_id"})
        ):
            gaps.append("diag_runs has no unique index covering run_id")
        if "diag_run_items" in tables and not _has_unique_covering(
            conn, "diag_run_items", frozenset({"item_id"})
        ):
            gaps.append("diag_run_items has no unique index covering item_id")
        if "diag_run_items" in tables and not _has_unique_covering(
            conn,
            "diag_run_items",
            frozenset({"run_id", "store_id", "attempt"}),
        ):
            gaps.append("diag_run_items has no unique index covering (run_id, store_id, attempt)")
    return gaps


def _require_table(
    conn: sqlite3.Connection,
    tables: set[str],
    name: str,
    required: frozenset[str],
    gaps: list[str],
) -> None:
    if name not in tables:
        gaps.append(f"table {name} is absent")
        return
    present = _columns(conn, name)
    missing = sorted(required - present)
    if missing:
        gaps.append(f"{name} is missing columns {missing}")


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({_ident(table)})").fetchall()
    return {row["name"] for row in rows}


def _has_unique_covering(conn: sqlite3.Connection, table: str, required: frozenset[str]) -> bool:
    indexes = conn.execute(f"PRAGMA index_list({_ident(table)})").fetchall()
    for index in indexes:
        if not index["unique"]:
            continue
        info = conn.execute(f"PRAGMA index_info({_ident(index['name'])})").fetchall()
        columns = frozenset(row["name"] for row in info)
        if required <= columns:
            return True
    return False


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"unsafe SQL identifier: {name}")
    return name
