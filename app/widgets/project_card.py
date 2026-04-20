from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FileDropListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        md = event.mimeData()
        if md.hasUrls():
            for url in md.urls():
                path = Path(url.toLocalFile())
                if path.is_file() and not self._has_item(str(path.resolve())):
                    self.addItem(QListWidgetItem(str(path.resolve())))
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _has_item(self, text: str) -> bool:
        return any(self.item(i).text() == text for i in range(self.count()))


class ProjectCardWidget(QWidget):
    rename_requested = pyqtSignal(str, str)
    remove_requested = pyqtSignal(str)
    files_changed = pyqtSignal()

    def __init__(self, project_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_name = project_name
        self._rename_origin = project_name

        self.title_edit = QLineEdit(project_name)
        self.title_edit.setReadOnly(True)
        self.title_edit.setObjectName("projectNameLineEdit")

        self.rename_btn = QPushButton("Rename")
        self.remove_btn = QPushButton("Delete")

        header = QHBoxLayout()
        header.addWidget(QLabel("Project:"))
        header.addWidget(self.title_edit, stretch=1)
        header.addWidget(self.rename_btn)
        header.addWidget(self.remove_btn)

        self.file_list = FileDropListWidget(self)

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(self.file_list)

        self.rename_btn.clicked.connect(self._rename)
        self.remove_btn.clicked.connect(self._remove)
        self.title_edit.editingFinished.connect(self._finish_rename)
        model = self.file_list.model()
        model.rowsInserted.connect(lambda *_: self.files_changed.emit())
        model.rowsRemoved.connect(lambda *_: self.files_changed.emit())

    def _rename(self) -> None:
        self._rename_origin = self.project_name
        self.title_edit.setReadOnly(False)
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def _finish_rename(self) -> None:
        if self.title_edit.isReadOnly():
            return
        new_name = self.title_edit.text().strip()
        old_name = self._rename_origin
        self.title_edit.setReadOnly(True)
        if new_name and new_name != old_name:
            self.project_name = new_name
            self.rename_requested.emit(old_name, new_name)
        else:
            self.title_edit.setText(old_name)

    def _remove(self) -> None:
        self.remove_requested.emit(self.project_name)

    def add_files(self, file_paths: list[str]) -> None:
        existing = {self.file_list.item(i).text() for i in range(self.file_list.count())}
        for path in file_paths:
            if path in existing:
                continue
            self.file_list.addItem(path)
        self.files_changed.emit()

    def files(self) -> list[str]:
        return [self.file_list.item(i).text() for i in range(self.file_list.count())]
