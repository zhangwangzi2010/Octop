"""Diagnosis run, item, and node-event table access."""

from __future__ import annotations

from dataclasses import dataclass

from octop.infra.db.pool import DatabasePool
from octop.infra.db.repos._base import DbRow, map_rows, now_ts, sql_in_placeholders
from octop.infra.errors import ErrorCode, OctopError

_IN_FLIGHT_ITEM_STATUSES = ("PREPARING", "DIAGNOSING")
_RESUMABLE_ITEM_STATUS = "PENDING"


@dataclass(frozen=True)
class DiagnosisRunRow:
    id: int
    run_id: str
    owner_user_id: int
    client_request_id: str
    status: str
    report_ref: str | None

    @classmethod
    def from_row(cls, row: DbRow) -> DiagnosisRunRow:
        report_ref = row["report_ref"]
        return cls(
            id=int(row["id"]),
            run_id=str(row["run_id"]),
            owner_user_id=int(row["owner_user_id"]),
            client_request_id=str(row["client_request_id"]),
            status=str(row["status"]),
            report_ref=str(report_ref) if report_ref else None,
        )


@dataclass(frozen=True)
class DiagnosisRunItemRow:
    id: int
    item_id: str
    run_id: str
    store_id: str
    attempt: int
    status: str
    slice_ref: str | None

    @classmethod
    def from_row(cls, row: DbRow) -> DiagnosisRunItemRow:
        slice_ref = row["slice_ref"]
        return cls(
            id=int(row["id"]),
            item_id=str(row["item_id"]),
            run_id=str(row["run_id"]),
            store_id=str(row["store_id"]),
            attempt=int(row["attempt"]),
            status=str(row["status"]),
            slice_ref=str(slice_ref) if slice_ref else None,
        )


@dataclass(frozen=True)
class DiagnosisNodeEventRow:
    id: int
    run_id: str
    item_id: str | None
    node: str
    event: str
    detail: str | None
    ts: int

    @classmethod
    def from_row(cls, row: DbRow) -> DiagnosisNodeEventRow:
        item_id = row["item_id"]
        detail = row["detail"]
        return cls(
            id=int(row["id"]),
            run_id=str(row["run_id"]),
            item_id=str(item_id) if item_id else None,
            node=str(row["node"]),
            event=str(row["event"]),
            detail=str(detail) if detail is not None else None,
            ts=int(row["ts"]),
        )


class DiagnosisRunsRepo:
    def __init__(self, db: DatabasePool) -> None:
        self._db = db

    def create_run(
        self,
        *,
        run_id: str,
        owner_user_id: int,
        client_request_id: str,
        status: str = "PREPARING",
        report_ref: str | None = None,
    ) -> DiagnosisRunRow:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO diag_runs("
                "run_id, owner_user_id, client_request_id, status, report_ref"
                ") VALUES (?, ?, ?, ?, ?)",
                (run_id, owner_user_id, client_request_id, status, report_ref),
            )
        found = self.get_by_client_request_id(client_request_id)
        if found is None:
            raise RuntimeError("inserted diagnosis run was not readable")
        return found

    def get_by_client_request_id(
        self,
        client_request_id: str,
        *,
        owner_user_id: int | None = None,
    ) -> DiagnosisRunRow | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM diag_runs WHERE client_request_id = ?",
                (client_request_id,),
            ).fetchone()
        if row is None:
            return None
        found = DiagnosisRunRow.from_row(row)
        if owner_user_id is not None and found.owner_user_id != owner_user_id:
            raise OctopError(ErrorCode.FORBIDDEN, "diagnosis run is not accessible")
        return found

    def get_run(self, run_id: str) -> DiagnosisRunRow | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM diag_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return DiagnosisRunRow.from_row(row) if row is not None else None

    def list_runs(self) -> list[DiagnosisRunRow]:
        with self._db.connect() as conn:
            rows = conn.execute("SELECT * FROM diag_runs ORDER BY id").fetchall()
        return map_rows(rows, DiagnosisRunRow)

    def list_items(self, run_id: str) -> list[DiagnosisRunItemRow]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM diag_run_items WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return map_rows(rows, DiagnosisRunItemRow)

    def update_run_status(self, run_id: str, status: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE diag_runs SET status = ? WHERE run_id = ?",
                (status, run_id),
            )

    def cancel_unfinished_items(self, run_id: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE diag_run_items SET status = ? "
                "WHERE run_id = ? AND status NOT IN ('OK', 'FAILED', 'SKIPPED', 'CANCELLED')",
                ("CANCELLED", run_id),
            )

    def list_runs_for_owner(self, owner_user_id: int) -> list[DiagnosisRunRow]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM diag_runs WHERE owner_user_id = ? ORDER BY id",
                (owner_user_id,),
            ).fetchall()
        return map_rows(rows, DiagnosisRunRow)

    def create_item(
        self,
        *,
        item_id: str,
        run_id: str,
        store_id: str,
        attempt: int,
        status: str,
        slice_ref: str | None = None,
    ) -> DiagnosisRunItemRow:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO diag_run_items("
                "item_id, run_id, store_id, attempt, status, slice_ref"
                ") VALUES (?, ?, ?, ?, ?, ?)",
                (item_id, run_id, store_id, attempt, status, slice_ref),
            )
        found = self.get_item(item_id)
        if found is None:
            raise RuntimeError("inserted diagnosis item was not readable")
        return found

    def update_item(self, item_id: str, *, status: str, attempt: int) -> None:
        """Persist the status and attempt already produced for one item."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE diag_run_items SET status = ?, attempt = ? WHERE item_id = ?",
                (status, attempt, item_id),
            )

    def get_item(self, item_id: str) -> DiagnosisRunItemRow | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM diag_run_items WHERE item_id = ?",
                (item_id,),
            ).fetchone()
        return DiagnosisRunItemRow.from_row(row) if row is not None else None

    def reset_orphan_items(self) -> int:
        """Return in-flight items to a resumable status. Terminal rows stay put."""
        placeholders = sql_in_placeholders(len(_IN_FLIGHT_ITEM_STATUSES))
        with self._db.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE diag_run_items SET status = ? WHERE status IN ({placeholders})",
                (_RESUMABLE_ITEM_STATUS, *_IN_FLIGHT_ITEM_STATUSES),
            )
        return int(cursor.rowcount)

    def append_event(
        self,
        *,
        run_id: str,
        item_id: str | None,
        node: str,
        event: str,
        detail: str | None = None,
    ) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO diag_node_events(run_id, item_id, node, event, detail, ts) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, item_id, node, event, detail, now_ts()),
            )

    def list_events(self, run_id: str) -> list[DiagnosisNodeEventRow]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM diag_node_events WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return map_rows(rows, DiagnosisNodeEventRow)
