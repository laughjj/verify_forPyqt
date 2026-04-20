from __future__ import annotations

import json
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget

from app.controllers.task_controller import TaskController
from app.models.dto import BatchState, BackendTaskSnapshot
from app.models.ui_state import UiSubmissionState
from app.services.config_service import ConfigService
from app.widgets.file_explorer import FileExplorerWidget
from app.widgets.project_board import ProjectBoardWidget
from app.widgets.task_detail_panel import TaskDetailPanel


class MainWindow(QMainWindow):
    def __init__(self, controller: TaskController, config_service: ConfigService) -> None:
        super().__init__()
        ui_path = Path(__file__).resolve().parent.parent / "resources" / "ui" / "main_window.ui"
        uic.loadUi(str(ui_path), self)

        self.controller = controller
        self.config_service = config_service

        config = self.config_service.load()
        default_projects = config.get("recent_projects") or ["fish2", "TianELake"]

        self.file_explorer = FileExplorerWidget(config.get("last_dir"))
        self.project_board = ProjectBoardWidget(default_projects)
        self.task_detail = TaskDetailPanel()

        self._inject_widget(self.leftHostWidget, self.file_explorer)
        self._inject_widget(self.rightHostWidget, self.project_board)
        self._inject_widget(self.taskDetailHostWidget, self.task_detail)

        self.backendUrlLineEdit.setText(config.get("backend_url", "http://127.0.0.1:8000"))
        self.scriptKeyComboBox.addItems(["fish2", "TianELake", "default_script"])
        last_key = config.get("last_script_key", "fish2")
        idx = self.scriptKeyComboBox.findText(last_key)
        if idx >= 0:
            self.scriptKeyComboBox.setCurrentIndex(idx)

        self._bind_signals()
        self.append_log("前端就绪：支持 WebSocket + REST fallback 的批次任务处理")

    def _inject_widget(self, host: QWidget, widget: QWidget) -> None:
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def _bind_signals(self) -> None:
        self.assignSelectedButton.clicked.connect(self.assign_selected_files)
        self.startBatchButton.clicked.connect(self.start_batch)
        self.saveConfigButton.clicked.connect(self.save_config)
        self.cancelWsButton.clicked.connect(self.controller.reconnect_ws)

        self.file_explorer.directory_changed.connect(self.on_directory_changed)

        self.controller.log.connect(self.append_log)
        self.controller.validation_error.connect(self.on_validation_error)
        self.controller.batch_changed.connect(self.render_batch)
        self.controller.task_snapshot_changed.connect(self.on_snapshot_changed)

    def on_directory_changed(self, directory: str) -> None:
        config = self.config_service.load()
        config["last_dir"] = directory
        self.config_service.save(config)

    def assign_selected_files(self) -> None:
        files = self.file_explorer.selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先选择至少一个文件")
            return
        self.project_board.add_files_to_first_project(files)
        self.append_log(f"已加入 {len(files)} 个文件")

    def start_batch(self) -> None:
        try:
            extra_params = self.controller.parse_extra_params(self.extraParamsLineEdit.text())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "参数错误", str(exc))
            return

        ui_state = UiSubmissionState(
            backend_url=self.backendUrlLineEdit.text().strip(),
            script_key=self.scriptKeyComboBox.currentText().strip(),
            extra_params=extra_params,
            project_files=self.project_board.get_mapping(),
        )
        self.controller.submit_batch(ui_state)

    def render_batch(self, batch: BatchState) -> None:
        self.batchProgressBar.setValue(batch.aggregate_progress())
        total = len(batch.snapshots)
        done = len([x for x in batch.snapshots.values() if x.status.value in {"SUCCESS", "FAILURE"}])
        self.batchSummaryLabel.setText(
            f"Batch {batch.batch_id} | script={batch.script_key} | tasks={total} | done={done} | progress={batch.aggregate_progress()}%"
        )
        self.task_detail.render_batch(batch)

    def on_snapshot_changed(self, snapshot: BackendTaskSnapshot) -> None:
        self.task_detail.upsert_snapshot(snapshot, snapshot.params_json.get("project_name", ""))
        if snapshot.status.value == "FAILURE":
            self.append_log(f"任务失败 {snapshot.id}: {snapshot.error_message}")

    def on_validation_error(self, message: str) -> None:
        QMessageBox.warning(self, "提交校验失败", message)
        self.append_log("提交校验失败\n" + message)

    def append_log(self, message: str) -> None:
        self.logTextEdit.append(message)

    def save_config(self) -> None:
        try:
            parsed = json.loads(self.extraParamsLineEdit.text() or "{}")
            if not isinstance(parsed, dict):
                raise ValueError
        except Exception:
            parsed = {}
        config = {
            "backend_url": self.backendUrlLineEdit.text().strip(),
            "last_script_key": self.scriptKeyComboBox.currentText().strip(),
            "recent_projects": list(self.project_board.cards.keys()),
            "last_dir": self.file_explorer.path_input.text().strip(),
            "last_extra_params": parsed,
        }
        self.config_service.save(config)
        self.append_log("配置已保存")
