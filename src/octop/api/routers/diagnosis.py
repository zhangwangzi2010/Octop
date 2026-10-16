"""Diagnosis run routes. Ownership stays here; flow A stays in the orchestrator."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from octop.api.deps import current_user, get_server
from octop.infra.db.repos.diagnosis_runs import DiagnosisRunRow, DiagnosisRunsRepo
from octop.infra.diagnosis.orchestrator import DiagnosisOrchestrator
from octop.infra.errors import ErrorCode, OctopError
from octop.infra.server import OctopServer
from octop.infra.users.identity import User
from octop.infra.utils.ulid import new_ulid

router = APIRouter()

_TERMINAL_RUN_STATUSES = frozenset({"COMPLETED", "PARTIAL", "FAILED", "CANCELLED"})
_ORCHESTRATORS: dict[int, DiagnosisOrchestrator] = {}


class DiagnosisRunCreate(BaseModel):
    client_request_id: str = Field(min_length=1)
    stores: list[str] = Field(min_length=1)
    window_start: str = Field(min_length=1)
    window_end: str = Field(min_length=1)
    preload_status: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    snapshot_text: str


class DiagnosisItemOut(BaseModel):
    store_id: str
    status: str


class DiagnosisRunOut(BaseModel):
    run_id: str
    stage: str
    failure_reason: str | None
    items: list[DiagnosisItemOut]
    stages: list[str]
    llm_calls: int
    conclusion: str


def _orchestrator(server: OctopServer) -> DiagnosisOrchestrator:
    found = _ORCHESTRATORS.get(id(server))
    if found is None:
        found = DiagnosisOrchestrator(attribution_limit=3)
        _ORCHESTRATORS[id(server)] = found
    return found


def _repo(server: OctopServer) -> DiagnosisRunsRepo:
    assert server.services is not None
    return server.services.diagnosis_runs_repo


def _view(repo: DiagnosisRunsRepo, row: DiagnosisRunRow) -> DiagnosisRunOut:
    items = [
        DiagnosisItemOut(store_id=item.store_id, status=item.status)
        for item in repo.list_items(row.run_id)
    ]
    stages: list[str] = []
    failure_reason: str | None = None
    conclusion = ""
    for event in repo.list_events(row.run_id):
        if event.event == "stage":
            stages.append(event.node)
        elif event.node == "conclusion" and event.detail:
            conclusion = event.detail
        elif event.node == "flow_a" and failure_reason is None:
            failure_reason = event.event
    if row.status == "COMPLETED":
        failure_reason = None
    return DiagnosisRunOut(
        run_id=row.run_id,
        stage=row.status,
        failure_reason=failure_reason,
        items=items,
        stages=stages,
        llm_calls=0,
        conclusion=conclusion,
    )


def _require_run(repo: DiagnosisRunsRepo, run_id: str, user: User) -> DiagnosisRunRow:
    row = repo.get_run(run_id)
    if row is None:
        raise OctopError(ErrorCode.NOT_FOUND, "diagnosis run not found")
    if not user.is_admin and row.owner_user_id != user.id:
        raise OctopError(ErrorCode.FORBIDDEN, "diagnosis run is not accessible")
    return row


@router.post("/diagnosis/runs", summary="Create a diagnosis run", response_model=DiagnosisRunOut)
async def create_diagnosis_run(
    body: DiagnosisRunCreate,
    user: User = Depends(current_user),
    server: OctopServer = Depends(get_server),
) -> DiagnosisRunOut:
    """Create a flow A run, or return the caller's existing client_request_id."""
    repo = _repo(server)
    existing = repo.get_by_client_request_id(
        body.client_request_id,
        owner_user_id=None if user.is_admin else user.id,
    )
    if existing is not None:
        return _view(repo, existing)

    result = _orchestrator(server).submit(
        client_request_id=body.client_request_id,
        stores=body.stores,
        preload_status=body.preload_status,
        row_count=body.row_count,
        snapshot_text=body.snapshot_text,
    )
    run_id = new_ulid()
    repo.create_run(
        run_id=run_id,
        owner_user_id=user.id,
        client_request_id=body.client_request_id,
        status=str(result["state"]),
    )
    for item in result["items"]:
        item_status = str(item.get("state") or "")
        if not item_status:
            item_status = "OK" if result["state"] == "COMPLETED" else "PENDING"
        repo.create_item(
            item_id=new_ulid(),
            run_id=run_id,
            store_id=str(item["store_id"]),
            attempt=1,
            status=item_status,
        )
    for stage in result["stages"]:
        repo.append_event(run_id=run_id, item_id=None, node=str(stage), event="stage")
    for event in result["events"]:
        repo.append_event(
            run_id=run_id,
            item_id=None,
            node="flow_a",
            event=str(event.get("kind") or "event"),
        )
    if body.snapshot_text:
        repo.append_event(
            run_id=run_id,
            item_id=None,
            node="conclusion",
            event="echo",
            detail=body.snapshot_text,
        )
    stored = repo.get_run(run_id)
    if stored is None:
        raise OctopError(ErrorCode.NOT_FOUND, "diagnosis run not found")
    viewed = _view(repo, stored)
    return viewed.model_copy(update={"llm_calls": int(result["llm_calls"])})


@router.get(
    "/diagnosis/runs",
    summary="List diagnosis runs",
    response_model=list[DiagnosisRunOut],
)
async def list_diagnosis_runs(
    user: User = Depends(current_user),
    server: OctopServer = Depends(get_server),
) -> list[DiagnosisRunOut]:
    """List the caller's runs. An admin sees every run."""
    repo = _repo(server)
    rows = repo.list_runs() if user.is_admin else repo.list_runs_for_owner(user.id)
    return [_view(repo, row) for row in rows]


@router.get(
    "/diagnosis/runs/{run_id}",
    summary="Get a diagnosis run",
    response_model=DiagnosisRunOut,
)
async def get_diagnosis_run(
    run_id: str,
    user: User = Depends(current_user),
    server: OctopServer = Depends(get_server),
) -> DiagnosisRunOut:
    """Return one run when the caller owns it or is an admin."""
    repo = _repo(server)
    return _view(repo, _require_run(repo, run_id, user))


@router.post(
    "/diagnosis/runs/{run_id}/cancel",
    summary="Cancel a diagnosis run",
    response_model=DiagnosisRunOut,
)
async def cancel_diagnosis_run(
    run_id: str,
    user: User = Depends(current_user),
    server: OctopServer = Depends(get_server),
) -> DiagnosisRunOut:
    """Cancel a non-terminal run and release an attribution slot."""
    repo = _repo(server)
    row = _require_run(repo, run_id, user)
    if row.status in _TERMINAL_RUN_STATUSES:
        if row.status == "CANCELLED":
            return _view(repo, row)
        raise OctopError(ErrorCode.FORBIDDEN, "diagnosis run is not running")
    repo.update_run_status(run_id, "CANCELLED")
    repo.cancel_unfinished_items(run_id)
    _orchestrator(server).release_attribution()
    updated = repo.get_run(run_id)
    if updated is None:
        raise OctopError(ErrorCode.NOT_FOUND, "diagnosis run not found")
    return _view(repo, updated)
