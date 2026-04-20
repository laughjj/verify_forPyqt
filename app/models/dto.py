from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from app.models.task_state import TaskStatus


@dataclass
class BackendTaskSnapshot:
    id: str
    script_key: str
    input_path: str
    params_json: Dict[str, Any]
    status: TaskStatus
    progress: int
    result_json: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    finished_at: str = ""


@dataclass
class TaskBinding:
    project_name: str
    input_path: str
    task_id: str = ""


@dataclass
class BatchState:
    batch_id: str
    script_key: str
    created_at: str
    backend_url: str
    tasks: dict[str, TaskBinding] = field(default_factory=dict)
    snapshots: dict[str, BackendTaskSnapshot] = field(default_factory=dict)

    @classmethod
    def create(cls, batch_id: str, script_key: str, backend_url: str) -> "BatchState":
        return cls(
            batch_id=batch_id,
            script_key=script_key,
            created_at=datetime.utcnow().isoformat(),
            backend_url=backend_url,
        )

    def aggregate_progress(self) -> int:
        if not self.snapshots:
            return 0
        total = sum(max(0, min(100, s.progress)) for s in self.snapshots.values())
        return int(total / len(self.snapshots))
