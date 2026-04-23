from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from functools import partial
from typing import Any, Callable

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal

from app.models.dto import BackendTaskSnapshot, BatchState, TaskBinding
from app.models.task_state import TaskStatus
from app.models.ui_state import UiSubmissionState
from app.services.backend_client import BackendClient
from app.services.batch_history_service import BatchHistoryService
from app.services.file_mapping_service import FileMappingService
from app.services.payload_builder import build_task_payloads
from app.services.ws_client import TaskWsClient


class _WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)


class _ApiRunnable(QRunnable):
    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            data = self.func(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
            return
        self.signals.result.emit(data)


class TaskController(QObject):
    log = pyqtSignal(str)
    validation_error = pyqtSignal(str)
    batch_changed = pyqtSignal(object)
    task_snapshot_changed = pyqtSignal(object)

    def __init__(
        self,
        backend_client: BackendClient,
        ws_client: TaskWsClient,
        file_mapping_service: FileMappingService,
        history_service: BatchHistoryService,
    ) -> None:
        super().__init__()
        self.backend_client = backend_client
        self.ws_client = ws_client
        self.file_mapping_service = file_mapping_service
        self.history_service = history_service

        self.pool = QThreadPool.globalInstance()
        self.current_batch: BatchState | None = None
        self.pending_create_requests = 0

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(2200)
        self.poll_timer.timeout.connect(self.poll_all_active_tasks)

        self.ws_client.message_received.connect(self.on_ws_message)
        self.ws_client.disconnected.connect(self.on_ws_disconnected)

    def submit_batch(self, ui_state: UiSubmissionState) -> None:
        self.backend_client.set_base_url(ui_state.backend_url)

        normalized, errors = self.file_mapping_service.validate(ui_state.project_files)
        if errors:
            self.validation_error.emit("\n".join(errors))
            return

        batch_id = str(uuid.uuid4())
        self.current_batch = BatchState.create(batch_id=batch_id, script_key=ui_state.script_key, backend_url=ui_state.backend_url)
        self.log.emit(f"创建批次 {batch_id}，准备提交 {sum(len(v) for v in normalized.values())} 个子任务")
        self.batch_changed.emit(self.current_batch)
        self.pending_create_requests = sum(len(v) for v in normalized.values())

        for project_name, file_path, payload in build_task_payloads(
            script_key=ui_state.script_key,
            batch_id=batch_id,
            project_files=normalized,
            extra_params=ui_state.extra_params,
        ):
            self.current_batch.tasks[file_path] = TaskBinding(project_name=project_name, input_path=file_path)
            runnable = _ApiRunnable(self.backend_client.create_task, payload)
            runnable.signals.result.connect(partial(self.on_task_created, file_path))
            runnable.signals.error.connect(partial(self.on_create_failed, file_path))
            self.pool.start(runnable)

        self.poll_timer.start()

    def on_task_created(self, file_path: str, snapshot: BackendTaskSnapshot) -> None:
        if not self.current_batch:
            return
        self.pending_create_requests = max(0, self.pending_create_requests - 1)
        self.current_batch.tasks[file_path].task_id = snapshot.id
        self.current_batch.snapshots[snapshot.id] = snapshot
        self.log.emit(f"任务已创建: {snapshot.id} ({file_path})")
        self.task_snapshot_changed.emit(snapshot)
        self.batch_changed.emit(self.current_batch)
        self.ws_client.subscribe(self.current_batch.backend_url, snapshot.id)

    def on_create_failed(self, file_path: str, message: str) -> None:
        self.pending_create_requests = max(0, self.pending_create_requests - 1)
        self.on_http_error(f"创建任务失败 {file_path}", message)
        if self.pending_create_requests == 0 and self.current_batch and not self.current_batch.snapshots:
            self.finalize_batch()

    def poll_all_active_tasks(self) -> None:
        if not self.current_batch:
            return
        active_ids = [
            task_id
            for task_id, snapshot in self.current_batch.snapshots.items()
            if snapshot.status not in TaskStatus.terminal()
        ]
        if not active_ids and self.current_batch.snapshots:
            self.finalize_batch()
            return
        for task_id in active_ids:
            runnable = _ApiRunnable(self.backend_client.get_task, task_id)
            runnable.signals.result.connect(self.on_task_snapshot)
            runnable.signals.error.connect(partial(self.on_http_error, f"轮询失败 {task_id}"))
            self.pool.start(runnable)

    def on_task_snapshot(self, snapshot: BackendTaskSnapshot) -> None:
        if not self.current_batch:
            return
        self.current_batch.snapshots[snapshot.id] = snapshot
        self.task_snapshot_changed.emit(snapshot)
        self.batch_changed.emit(self.current_batch)

    def on_ws_message(self, task_id: str, payload: dict) -> None:
        if not self.current_batch:
            return
        if payload.get("id") != task_id:
            payload = {**payload, "id": task_id}
        try:
            snapshot = self.backend_client.parse_snapshot(payload)
        except Exception as exc:  # noqa: BLE001
            self.log.emit(f"WS 消息解析失败({task_id}): {exc}")
            return
        self.current_batch.snapshots[task_id] = snapshot
        self.task_snapshot_changed.emit(snapshot)
        self.batch_changed.emit(self.current_batch)

    def on_ws_disconnected(self, task_id: str, reason: str) -> None:
        self.log.emit(f"WebSocket 断开 {task_id}: {reason}，将继续 REST 轮询兜底")

    def on_http_error(self, prefix: str, message: str) -> None:
        self.log.emit(f"{prefix}: {message}")

    def reconnect_ws(self) -> None:
        if not self.current_batch:
            return
        self.ws_client.unsubscribe_all()
        for task_id in self.current_batch.snapshots:
            self.ws_client.subscribe(self.current_batch.backend_url, task_id)
        self.log.emit("已触发 WebSocket 重新连接")

    def finalize_batch(self) -> None:
        if not self.current_batch:
            return
        self.poll_timer.stop()
        self.ws_client.unsubscribe_all()
        history_payload = {
            "batch_id": self.current_batch.batch_id,
            "created_at": self.current_batch.created_at,
            "script_key": self.current_batch.script_key,
            "backend_url": self.current_batch.backend_url,
            "aggregate_progress": self.current_batch.aggregate_progress(),
            "tasks": [asdict(s) for s in self.current_batch.snapshots.values()],
        }
        self.history_service.append(history_payload)
        success = sum(1 for s in self.current_batch.snapshots.values() if s.status == TaskStatus.SUCCESS)
        failed = sum(1 for s in self.current_batch.snapshots.values() if s.status == TaskStatus.FAILURE)
        self.log.emit(f"批次结束：成功 {success}，失败 {failed}")
        self.batch_changed.emit(self.current_batch)

    @staticmethod
    def parse_extra_params(raw: str) -> dict:
        if not raw.strip():
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Extra Params 必须是 JSON 对象")
        return parsed
