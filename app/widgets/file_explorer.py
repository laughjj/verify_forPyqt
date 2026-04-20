from __future__ import annotations

import os
from typing import List

from PyQt5.QtCore import QDir, QModelIndex, Qt
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
    def __init__(self, initial_path: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.initial_path = initial_path or QDir.homePath()

        self.path_input = QLineEdit(self.initial_path)
        self.go_button = QPushButton("跳转")

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.path_input)
        top_bar.addWidget(self.go_button)

        self.model = QFileSystemModel(self)
        self.model.setRootPath(self.initial_path)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)

        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.initial_path))
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)

        for col in (2, 3):
            self.tree.hideColumn(col)

        layout = QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addWidget(self.tree)

        self.go_button.clicked.connect(self.change_path)
        self.path_input.returnPressed.connect(self.change_path)

    def change_path(self) -> None:
        target = os.path.expanduser(self.path_input.text().strip())
        if not os.path.exists(target):
            QMessageBox.warning(self, "路径错误", f"路径不存在:\n{target}")
            return
        model_index = self.model.index(target)
        self.tree.setRootIndex(model_index)

    def selected_files(self) -> List[str]:
        selected_paths: List[str] = []
        for idx in self.tree.selectionModel().selectedRows(0):
            path = self.model.filePath(idx)
            if os.path.isfile(path):
                selected_paths.append(path)
        return sorted(set(selected_paths))
