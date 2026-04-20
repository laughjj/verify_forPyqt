from __future__ import annotations

from typing import Dict, Iterable, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProjectFileListWidget(QListWidget):
    def __init__(self, project_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_name = project_name
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def add_files(self, file_paths: Iterable[str]) -> None:
        existing = {self.item(i).text() for i in range(self.count())}
        for path in file_paths:
            if path in existing:
                continue
            self.addItem(QListWidgetItem(path))

    def get_files(self) -> List[str]:
        return [self.item(i).text() for i in range(self.count())]


class ProjectBoardWidget(QWidget):
    def __init__(self, projects: List[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.projects = projects or ["fish2", "TianELake"]
        self.columns: Dict[str, ProjectFileListWidget] = {}

        self.column_container = QHBoxLayout()
        for project in self.projects:
            self._add_project_column(project)

        self.new_project_btn = QPushButton("+ 新项目")
        self.new_project_btn.clicked.connect(self._create_project_column)

        root = QVBoxLayout(self)
        root.addLayout(self.column_container)
        root.addWidget(self.new_project_btn)

    def _add_project_column(self, project_name: str) -> None:
        card = QWidget(self)
        card_layout = QVBoxLayout(card)
        title = QLabel(project_name)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        file_list = ProjectFileListWidget(project_name, card)
        self.columns[project_name] = file_list
        card_layout.addWidget(file_list)

        self.column_container.addWidget(card)

    def _create_project_column(self) -> None:
        base = "new_project"
        idx = 1
        while f"{base}_{idx}" in self.columns:
            idx += 1
        self._add_project_column(f"{base}_{idx}")

    def add_files_to_project(self, project_name: str, file_paths: Iterable[str]) -> None:
        if project_name not in self.columns:
            self._add_project_column(project_name)
        self.columns[project_name].add_files(file_paths)

    def get_project_files(self) -> Dict[str, List[str]]:
        return {name: widget.get_files() for name, widget in self.columns.items()}

    def first_project_name(self) -> str:
        return next(iter(self.columns))
