from __future__ import annotations

from typing import Any, Dict

import requests

from app.models.dto import BackendTaskSnapshot
from app.models.task_state import TaskStatus


class BackendClient:
    """HTTP client aligned with verifyfor_django 20260227run contract."""

    def __init__(self, base_url: str, timeout: int = 12) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def create_task(self, payload: Dict[str, Any]) -> BackendTaskSnapshot:
        response = requests.post(f"{self.base_url}/api/tasks/", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return self.parse_snapshot(response.json())

    def get_task(self, task_id: str) -> BackendTaskSnapshot:
        response = requests.get(f"{self.base_url}/api/tasks/{task_id}/", timeout=self.timeout)
        response.raise_for_status()
        return self.parse_snapshot(response.json())

    def parse_snapshot(self, data: Dict[str, Any]) -> BackendTaskSnapshot:
        status_raw = str(data.get("status", "QUEUED")).upper()
        try:
            status = TaskStatus(status_raw)
        except ValueError:
            status = TaskStatus.QUEUED

        def ensure_dict(value: Any) -> Dict[str, Any]:
            return value if isinstance(value, dict) else {}

        return BackendTaskSnapshot(
            id=str(data.get("id", "")),
            script_key=str(data.get("script_key", "")),
            input_path=str(data.get("input_path", "")),
            params_json=ensure_dict(data.get("params_json")),
            status=status,
            progress=int(data.get("progress", 0) or 0),
            result_json=ensure_dict(data.get("result_json")),
            error_message=str(data.get("error_message", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            updated_at=str(data.get("updated_at", "") or ""),
            started_at=str(data.get("started_at", "") or ""),
            finished_at=str(data.get("finished_at", "") or ""),
        )
