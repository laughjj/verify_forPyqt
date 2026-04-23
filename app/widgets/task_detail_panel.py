from __future__ import annotations

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.models.dto import BatchState, BackendTaskSnapshot


class TaskDetailPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Task ID", "Project", "File", "Status", "Progress", "Error"])

        root = QVBoxLayout(self)
        root.addWidget(self.table)

    def render_batch(self, batch: BatchState | None) -> None:
        self.table.setRowCount(0)
        if not batch:
            return

        file_to_project = {bind.input_path: bind.project_name for bind in batch.tasks.values()}
        for snapshot in batch.snapshots.values():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(snapshot.id))
            self.table.setItem(row, 1, QTableWidgetItem(file_to_project.get(snapshot.input_path, "")))
            self.table.setItem(row, 2, QTableWidgetItem(snapshot.input_path))
            self.table.setItem(row, 3, QTableWidgetItem(snapshot.status.value))
            self.table.setItem(row, 4, QTableWidgetItem(str(snapshot.progress)))
            self.table.setItem(row, 5, QTableWidgetItem(snapshot.error_message))

    def upsert_snapshot(self, snapshot: BackendTaskSnapshot, project_name: str = "") -> None:
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == snapshot.id:
                self.table.setItem(row, 3, QTableWidgetItem(snapshot.status.value))
                self.table.setItem(row, 4, QTableWidgetItem(str(snapshot.progress)))
                self.table.setItem(row, 5, QTableWidgetItem(snapshot.error_message))
                return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(snapshot.id))
        self.table.setItem(row, 1, QTableWidgetItem(project_name))
        self.table.setItem(row, 2, QTableWidgetItem(snapshot.input_path))
        self.table.setItem(row, 3, QTableWidgetItem(snapshot.status.value))
        self.table.setItem(row, 4, QTableWidgetItem(str(snapshot.progress)))
        self.table.setItem(row, 5, QTableWidgetItem(snapshot.error_message))
