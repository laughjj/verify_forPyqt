from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.backend_client import BackendClient, TaskStatus
from app.services.task_controller import TaskController
from app.widgets.file_explorer import FileExplorerWidget
from app.widgets.project_board import ProjectBoardWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VerifyFor 前端（PyQt5 初代）")
        self.resize(1400, 850)

        self.file_explorer = FileExplorerWidget()
        self.project_board = ProjectBoardWidget(["fish2", "TianELake"])

        self.backend_url_input = QLineEdit("http://localhost:8000")
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["standard", "fast", "strict"])

        self.add_to_project_btn = QPushButton("将选中文件加入项目")
        self.submit_btn = QPushButton("提交任务")
        self.export_json_btn = QPushButton("导出任务 JSON")
        self.refresh_records_btn = QPushButton("刷新处理记录")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("状态：等待提交")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.records_list = QListWidget()

        self.backend_client = BackendClient(self.backend_url_input.text())
        self.task_controller = TaskController(self.backend_client)
        self._bind_signals()

        self._setup_layout()

    def _setup_layout(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.file_explorer)
        splitter.addWidget(self.project_board)
        splitter.setSizes([500, 900])

        controls_group = QGroupBox("任务参数")
        controls_form = QFormLayout(controls_group)
        controls_form.addRow("后端地址", self.backend_url_input)
        controls_form.addRow("处理模式", self.mode_selector)

        action_bar = QHBoxLayout()
        action_bar.addWidget(self.add_to_project_btn)
        action_bar.addWidget(self.export_json_btn)
        action_bar.addWidget(self.submit_btn)
        action_bar.addWidget(self.refresh_records_btn)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(splitter)
        panel_layout.addWidget(controls_group)
        panel_layout.addLayout(action_bar)
        panel_layout.addWidget(self.status_label)
        panel_layout.addWidget(self.progress_bar)
        panel_layout.addWidget(QLabel("日志"))
        panel_layout.addWidget(self.log_output, stretch=2)
        panel_layout.addWidget(QLabel("处理记录"))
        panel_layout.addWidget(self.records_list, stretch=1)

        self.setCentralWidget(panel)

    def _bind_signals(self) -> None:
        self.add_to_project_btn.clicked.connect(self.on_add_files)
        self.export_json_btn.clicked.connect(self.export_task_json)
        self.submit_btn.clicked.connect(self.submit_task)
        self.refresh_records_btn.clicked.connect(self.task_controller.refresh_records)
        self.backend_url_input.editingFinished.connect(self.on_backend_url_updated)

        self.task_controller.submitted.connect(self.on_task_submitted)
        self.task_controller.status_updated.connect(self.on_status_updated)
        self.task_controller.records_updated.connect(self.on_records_updated)
        self.task_controller.error.connect(self.on_error)

    def on_backend_url_updated(self) -> None:
        self.backend_client.set_base_url(self.backend_url_input.text().strip())

    def on_add_files(self) -> None:
        files = self.file_explorer.selected_files()
        if not files:
            QMessageBox.information(self, "提示", "请先在左侧文件树中选中至少一个文件。")
            return

        default_project = self.project_board.first_project_name()
        self.project_board.add_files_to_project(default_project, files)
        self.append_log(f"已将 {len(files)} 个文件加入项目 {default_project}")

    def _build_payload(self) -> dict:
        project_files = self.project_board.get_project_files()
        options = {
            "mode": self.mode_selector.currentText(),
            "client": "verify_forPyqt",
        }
        return {
            "project_files": project_files,
            "options": options,
        }

    def export_task_json(self) -> None:
        payload = self._build_payload()
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出任务 JSON",
            str(Path.home() / "task_payload.json"),
            "JSON Files (*.json)",
        )
        if not filepath:
            return

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        self.append_log(f"已导出任务 JSON: {filepath}")

    def submit_task(self) -> None:
        payload = self._build_payload()
        total_files = sum(len(v) for v in payload["project_files"].values())
        if total_files == 0:
            QMessageBox.warning(self, "无法提交", "项目中没有可处理文件。")
            return

        self.on_backend_url_updated()
        self.progress_bar.setValue(0)
        self.status_label.setText("状态：提交中...")
        self.task_controller.submit(
            project_files=payload["project_files"],
            options=payload["options"],
        )

    def on_task_submitted(self, task_id: str) -> None:
        self.status_label.setText(f"状态：任务已提交（{task_id}）")
        self.append_log(f"任务提交成功，task_id={task_id}")

    def on_status_updated(self, status: TaskStatus) -> None:
        self.progress_bar.setValue(max(0, min(100, status.progress)))
        self.status_label.setText(f"状态：{status.status} ({status.progress}%)")
        if status.message:
            self.append_log(f"[{status.task_id}] {status.message}")

    def on_records_updated(self, records: list[dict]) -> None:
        self.records_list.clear()
        for row in records:
            task_id = row.get("task_id", "-")
            status = row.get("status", "unknown")
            finished_at = row.get("finished_at", "")
            self.records_list.addItem(f"{task_id} | {status} | {finished_at}")
        self.append_log(f"已刷新处理记录，共 {len(records)} 条")

    def on_error(self, message: str) -> None:
        self.append_log(message)
        QMessageBox.warning(self, "后端通信异常", message)

    def append_log(self, message: str) -> None:
        self.log_output.append(message)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
