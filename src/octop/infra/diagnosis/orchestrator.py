"""In-process flow A orchestrator.

Stage names and timeout budgets are the ones written in the orchestration
spec and the WT-2 task list. Flow A does not call an LLM. Data readiness
and analysis go through an injected port or the WT-1 preload and conclusion
helpers. Symptom rules, hit lines, and thresholds stay in their own modules.
Startup resets orphan items, including a crash left in DIAGNOSING.
The contract gate records a conclusion-schema or data_refs failure as FAIL.
A preload miss is not that gate.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from octop.infra.diagnosis.snapshot_structure import preload_consumable, symptom_conclusion

_STAGE_NAMES: tuple[str, ...] = (
    "PREPARING",
    "ANALYZING",
    "DIAGNOSING",
    "COMPLETING",
    "终态",
)
_TERMINAL_STATES: tuple[str, ...] = ("COMPLETED", "PARTIAL", "FAILED", "CANCELLED")
_LEGAL: dict[str, frozenset[str]] = {
    "PREPARING": frozenset({"ANALYZING", "FAILED", "CANCELLED"}),
    "ANALYZING": frozenset({"DIAGNOSING", "COMPLETING", "FAILED", "CANCELLED"}),
    "DIAGNOSING": frozenset({"COMPLETING", "FAILED", "CANCELLED"}),
    "COMPLETING": frozenset({"COMPLETED", "PARTIAL", "FAILED", "CANCELLED"}),
}
_RETRY: dict[str, Mapping[str, int]] = {
    "ensure_data_ready": {"timeout_seconds": 30 * 60, "max_attempts": 3},
    "analysis_run": {"timeout_seconds": 900, "max_attempts": 2},
    "diagnose 段1": {"timeout_seconds": 60, "max_attempts": 2},
    "summarize": {"timeout_seconds": 600},
}

DataGate = Callable[[str, int], bool]
AnalysisPort = Callable[[str], str]
LlmPort = Callable[..., object]


def stage_names() -> tuple[str, ...]:
    """The five stage names written on the run state machine."""
    return _STAGE_NAMES


def terminal_states() -> tuple[str, ...]:
    """Members of 终态. The word 终态 itself is the fifth stage name."""
    return _TERMINAL_STATES


def move(current: str, target: str) -> dict[str, Any]:
    """Accept a written edge. Reject anything else and keep the current state."""
    if target in _LEGAL.get(current, frozenset()):
        return {"accepted": True, "state": target, "events": []}
    return {
        "accepted": False,
        "state": current,
        "events": [{"kind": "illegal_transition", "from": current, "to": target}],
    }


def retry_policy(node: str) -> Mapping[str, int]:
    """Timeout table from the WT-2 task list. summarize has no attempt count."""
    try:
        return _RETRY[node]
    except KeyError as exc:
        raise ValueError(f"unknown node: {node}") from exc


def contract_gate(
    *,
    conclusion_schema_ok: bool,
    cited_values: Sequence[object],
    slice_values: Sequence[object],
) -> dict[str, Any]:
    """Record FAIL when the conclusion schema or a data_ref does not match."""
    present = set(slice_values)
    schema_failed = not conclusion_schema_ok
    refs_failed = any(value not in present for value in cited_values)
    if not schema_failed and not refs_failed:
        return {"result": "OK", "events": []}
    return {
        "result": "FAIL",
        "events": [
            {
                "kind": "contract_gate",
                "result": "FAIL",
                "conclusion_schema": schema_failed,
                "data_refs": refs_failed,
            }
        ],
    }


def run_with_retry(node: str, action: Callable[[], object]) -> dict[str, Any]:
    """Retry TimeoutError up to the written attempt count, then mark FAILED."""
    max_attempts = int(retry_policy(node)["max_attempts"])
    events: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        try:
            action()
        except TimeoutError:
            events.append({"reason": "timeout", "attempt": attempt})
            continue
        return {"failed": False, "attempts": attempt, "state": None, "events": events}
    return {"failed": True, "state": "FAILED", "attempts": max_attempts, "events": events}


class DiagnosisOrchestrator:
    """Flow A spine: gate, zero LLM, idempotency, resume, and a caller-set limit."""

    def __init__(
        self,
        *,
        attribution_limit: int,
        data_gate: DataGate | None = None,
        analysis: AnalysisPort | None = None,
        llm: LlmPort | None = None,
        orphans: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self._limit = attribution_limit
        self._held = 0
        self._data_gate = preload_consumable if data_gate is None else data_gate
        self._analysis = symptom_conclusion if analysis is None else analysis
        self._llm = llm
        self._runs: dict[str, dict[str, Any]] = {}
        self._by_client: dict[str, str] = {}
        self._reset_calls = 0
        self.reset_orphan_items(orphans)

    @property
    def attribution_held(self) -> int:
        """How many attribution slots are currently taken."""
        return self._held

    @property
    def reset_orphan_calls(self) -> int:
        """How many times startup or a later pass called reset_orphan_items."""
        return self._reset_calls

    def reset_orphan_items(self, orphans: Sequence[Mapping[str, Any]] | None = None) -> None:
        """Reset crashed in-progress runs and continue them. A repeat is a no-op."""
        self._reset_calls += 1
        if not orphans:
            return
        for orphan in orphans:
            client_request_id = str(orphan["client_request_id"])
            if client_request_id in self._by_client:
                continue
            self._resume_orphan(orphan)

    def try_acquire_attribution(self) -> bool:
        """Take one attribution slot. Pure data work does not call this."""
        if self._held >= self._limit:
            return False
        self._held += 1
        return True

    def release_attribution(self) -> None:
        """Return one attribution slot after the caller stops using it."""
        if self._held > 0:
            self._held -= 1

    def run_data_node(self, name: str) -> None:
        """Run a data node without taking an attribution slot."""
        del name

    def submit(
        self,
        *,
        client_request_id: str,
        stores: Sequence[str],
        preload_status: str,
        row_count: int,
        snapshot_text: str,
        checkpoint: str | None = None,
    ) -> dict[str, Any]:
        """Start flow A, or return the run already stored for this request id."""
        existing = self._by_client.get(client_request_id)
        if existing is not None:
            return self._runs[existing]
        if checkpoint not in (None, "ANALYZING"):
            raise ValueError("submit checkpoint cannot resume this stage")

        run_id = f"run-{len(self._runs) + 1}"
        items = [{"store_id": store_id} for store_id in stores]
        if checkpoint == "ANALYZING":
            stages, state, conclusion = self._finish_from("ANALYZING", snapshot_text)
            analysis_called = True
            events: list[dict[str, Any]] = []
        elif self._ensure_data_ready(preload_status, row_count):
            stages, state, conclusion = self._finish_from("PREPARING", snapshot_text)
            analysis_called = True
            events = []
        else:
            stages = ["PREPARING"]
            state = "PREPARING"
            conclusion = ""
            analysis_called = False
            events = [{"kind": "preload", "accepted": False}]

        record = {
            "run_id": run_id,
            "state": state,
            "stages": stages,
            "items": items,
            "llm_calls": self._llm_calls(),
            "conclusion": conclusion,
            "analysis_called": analysis_called,
            "events": events,
        }
        self._runs[run_id] = record
        self._by_client[client_request_id] = run_id
        return record

    def _resume_orphan(self, orphan: Mapping[str, Any]) -> None:
        start = str(orphan["state"])
        snapshot_text = str(orphan.get("snapshot_text", ""))
        stages, state, conclusion = self._resume_stages(start, snapshot_text)
        items: list[dict[str, Any]] = []
        raw_items = orphan.get("items", ())
        if not isinstance(raw_items, (str, bytes)) and isinstance(raw_items, Sequence):
            for item in raw_items:
                if isinstance(item, Mapping):
                    items.append({"store_id": str(item["store_id"]), "state": "OK"})
        run_id = f"run-{len(self._runs) + 1}"
        record = {
            "run_id": run_id,
            "state": state,
            "stages": stages,
            "items": items,
            "llm_calls": self._llm_calls(),
            "conclusion": conclusion,
            "analysis_called": True,
            "events": [{"kind": "reset_orphan_items", "from": start}],
        }
        self._runs[run_id] = record
        self._by_client[str(orphan["client_request_id"])] = run_id

    def _resume_stages(self, start: str, snapshot_text: str) -> tuple[list[str], str, str]:
        forward = {
            "ANALYZING": ("COMPLETING", "COMPLETED"),
            "DIAGNOSING": ("COMPLETING", "COMPLETED"),
            "COMPLETING": ("COMPLETED",),
        }
        if start not in forward:
            raise ValueError("orphan stage is not a resumable run stage")
        state = start
        stages = [start]
        conclusion = self._analysis_run(snapshot_text)
        for target in forward[start]:
            state = self._step(state, target)
            stages.append(state)
        return stages, state, conclusion

    def _ensure_data_ready(self, status: str, row_count: int) -> bool:
        return bool(self._data_gate(status, row_count))

    def _finish_from(self, start: str, snapshot_text: str) -> tuple[list[str], str, str]:
        state = start
        stages = [start]
        if start == "PREPARING":
            state = self._step(state, "ANALYZING")
            stages.append(state)
        conclusion = self._analysis_run(snapshot_text)
        state = self._step(state, "COMPLETING")
        stages.append(state)
        state = self._step(state, "COMPLETED")
        stages.append(state)
        return stages, state, conclusion

    def _analysis_run(self, snapshot_text: str) -> str:
        return str(self._analysis(snapshot_text))

    def _llm_calls(self) -> int:
        """Flow A never invokes the LLM port."""
        _ = self._llm
        return 0

    def _step(self, current: str, target: str) -> str:
        result = move(current, target)
        if result["accepted"] is not True:
            raise RuntimeError(f"illegal transition {current} -> {target}")
        return str(result["state"])
