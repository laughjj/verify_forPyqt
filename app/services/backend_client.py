from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class TaskStatus:
    task_id: str
    status: str
    progress: int
    message: str = ""


class BackendClient:
    """HTTP client for verifyfor_django task APIs."""

    def __init__(self, base_url: str, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def submit_task(self, payload: Dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/api/tasks/submit",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            raise ValueError("Backend response missing task_id")
        return task_id

    def fetch_status(self, task_id: str) -> TaskStatus:
        response = requests.get(
            f"{self.base_url}/api/tasks/{task_id}/status",
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return TaskStatus(
            task_id=data.get("task_id", task_id),
            status=data.get("status", "unknown"),
            progress=int(data.get("progress", 0)),
            message=data.get("message", ""),
        )

    def fetch_records(self) -> List[Dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/api/tasks/records",
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return list(data.get("records", []))
