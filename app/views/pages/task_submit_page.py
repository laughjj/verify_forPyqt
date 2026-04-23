from __future__ import annotations

import json
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QWidget

from app.controllers.task_controller import TaskController
from app.models.dto import BackendTaskSnapshot, BatchState
from app.models.ui_state import UiSubmissionState
from app.services.batch_history_service import BatchHistoryService
from app.services.config_service import ConfigService
from app.widgets.file_explorer import FileExplorerWidget
from app.widgets.project_board import ProjectBoardWidget
from app.widgets.task_detail_panel import TaskDetailPanel


class TaskSubmitPage(QWidget):
    """Independent feature page for task submission and progress tracking."""

    def __init__(
        self,
        controller: TaskController,
        config_service: ConfigService,
        history_service: BatchHistoryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parents[2] / "resources" / "ui" / "pages" / "task_submit_page.ui"
        uic.loadUi(str(ui_path), self)

        self.controller = controller
        self.config_service = config_service
        self.history_service = history_service

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
        idx = self.scriptKeyComboBox.findText(config.get("last_script_key", "fish2"))
        if idx >= 0:
            self.scriptKeyComboBox.setCurrentIndex(idx)
        if config.get("last_extra_params"):
            self.extraParamsLineEdit.setText(json.dumps(config["last_extra_params"], ensure_ascii=False))

        self._bind_signals()

    def _inject_widget(self, host: QWidget, widget: QWidget) -> None:
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def _bind_signals(self) -> None:
        self.assignSelectedButton.clicked.connect(self.assign_selected_files)
        self.startBatchButton.clicked.connect(self.start_batch)
        self.reconnectWsButton.clicked.connect(self.reconnect_ws)
        self.saveConfigButton.clicked.connect(self.save_config)

        self.file_explorer.directory_changed.connect(self.on_directory_changed)

        self.controller.log.connect(self.append_log)
        self.controller.validation_error.connect(self.on_validation_error)
        self.controller.batch_changed.connect(self.render_batch)
        self.controller.task_snapshot_changed.connect(self.on_snapshot_changed)

    def assign_selected_files(self) -> None:
        files = self.file_explorer.selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先在左侧选择至少一个文件")
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
        progress = batch.aggregate_progress()
        self.batchProgressBar.setValue(progress)
        total = len(batch.snapshots)
        done = sum(1 for x in batch.snapshots.values() if x.status.value in {"SUCCESS", "FAILURE"})
        self.batchSummaryLabel.setText(
            f"Batch {batch.batch_id} | script={batch.script_key} | tasks={total} | done={done} | progress={progress}%"
        )
        self.task_detail.render_batch(batch)

    def on_snapshot_changed(self, snapshot: BackendTaskSnapshot) -> None:
        self.task_detail.upsert_snapshot(snapshot, snapshot.params_json.get("project_name", ""))
        if snapshot.status.value == "FAILURE":
            self.append_log(f"任务失败 {snapshot.id}: {snapshot.error_message}")

    def on_validation_error(self, message: str) -> None:
        QMessageBox.warning(self, "提交校验失败", message)
        self.append_log("提交校验失败\n" + message)

    def on_directory_changed(self, directory: str) -> None:
        config = self.config_service.load()
        config["last_dir"] = directory
        self.config_service.save(config)

    def append_log(self, message: str) -> None:
        self.logTextEdit.append(message)

    def save_config(self) -> None:
        try:
            extra = json.loads(self.extraParamsLineEdit.text() or "{}")
            if not isinstance(extra, dict):
                raise ValueError
        except Exception:
            extra = {}
        config = {
            "backend_url": self.backendUrlLineEdit.text().strip(),
            "last_script_key": self.scriptKeyComboBox.currentText().strip(),
            "recent_projects": list(self.project_board.cards.keys()),
            "last_dir": self.file_explorer.path_input.text().strip(),
            "last_extra_params": extra,
        }
        self.config_service.save(config)
        self.append_log("配置已保存")

    def reconnect_ws(self) -> None:
        self.controller.reconnect_ws()

    def open_config_file(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config_service.path)))

    def export_batch_history(self) -> None:
        out_file, _ = QFileDialog.getSaveFileName(self, "导出批次历史", str(Path.home() / "batch_history_export.json"), "JSON (*.json)")
        if not out_file:
            return
        self.history_service.export_to(Path(out_file))
        self.append_log(f"批次历史已导出：{out_file}")

    def clear_batch_history(self) -> None:
        self.history_service.clear()
        self.append_log("本地批次历史已清空")
