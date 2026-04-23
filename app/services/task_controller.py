from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from app.services.backend_client import BackendClient, TaskStatus


class TaskController(QObject):
    submitted = pyqtSignal(str)
    status_updated = pyqtSignal(object)
    records_updated = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, backend_client: BackendClient, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.backend_client = backend_client
        self.current_task_id: Optional[str] = None

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(2000)
        self.poll_timer.timeout.connect(self.poll_status)

    def submit(self, project_files: Dict[str, list[str]], options: Dict[str, Any]) -> None:
        payload = {
            "project_files": project_files,
            "options": options,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            task_id = self.backend_client.submit_task(payload)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"任务提交失败: {exc}")
            return

        self.current_task_id = task_id
        self.submitted.emit(task_id)
        self.poll_timer.start()

    def poll_status(self) -> None:
        if not self.current_task_id:
            return
        try:
            status: TaskStatus = self.backend_client.fetch_status(self.current_task_id)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"状态轮询失败: {exc}")
            self.poll_timer.stop()
            return

        self.status_updated.emit(status)
        if status.status.lower() in {"success", "failed", "done", "completed"}:
            self.poll_timer.stop()
            self.refresh_records()

    def refresh_records(self) -> None:
        try:
            records = self.backend_client.fetch_records()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"读取处理记录失败: {exc}")
            return
        self.records_updated.emit(records)
