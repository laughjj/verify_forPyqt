from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QDir, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileSystemModel,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class FileExplorerWidget(QWidget):
    directory_changed = pyqtSignal(str)

    def __init__(self, initial_path: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.initial_path = initial_path or QDir.homePath()

        self.path_input = QLineEdit(self.initial_path)
        self.path_input.setObjectName("explorerPathLineEdit")
        self.go_button = QPushButton("Go")
        self.go_button.setObjectName("explorerGoButton")

        top = QHBoxLayout()
        top.addWidget(self.path_input)
        top.addWidget(self.go_button)

        self.model = QFileSystemModel(self)
        self.model.setRootPath(self.initial_path)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)

        self.tree = QTreeView(self)
        self.tree.setObjectName("explorerTreeView")
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.initial_path))
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (2, 3):
            self.tree.hideColumn(col)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.tree)

        self.go_button.clicked.connect(self.change_path)
        self.path_input.returnPressed.connect(self.change_path)

    def set_initial_dir(self, directory: str) -> None:
        self.path_input.setText(directory)
        self.change_path()

    def change_path(self) -> None:
        target = os.path.expanduser(self.path_input.text().strip())
        if not os.path.isdir(target):
            QMessageBox.warning(self, "路径错误", f"目录不存在:\n{target}")
            return
        idx = self.model.index(target)
        self.tree.setRootIndex(idx)
        self.directory_changed.emit(target)

    def selected_files(self) -> list[str]:
        files: set[str] = set()
        for idx in self.tree.selectionModel().selectedRows(0):
            p = Path(self.model.filePath(idx))
            if p.is_file():
                files.add(str(p.resolve()))
        return sorted(files)
