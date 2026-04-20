from __future__ import annotations

from collections import OrderedDict

from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.widgets.project_card import ProjectCardWidget


class ProjectBoardWidget(QWidget):
    def __init__(self, project_names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards: "OrderedDict[str, ProjectCardWidget]" = OrderedDict()

        self.scroll_widget = QWidget(self)
        self.cards_layout = QHBoxLayout(self.scroll_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_widget)

        self.add_project_btn = QPushButton("+ Add Project")
        self.add_project_btn.clicked.connect(self.add_project)

        root = QVBoxLayout(self)
        root.addWidget(self.scroll)
        root.addWidget(self.add_project_btn)

        for name in project_names:
            self.add_project(name)

    def add_project(self, project_name: str | None = None) -> None:
        name = (project_name or "new_project").strip()
        if not name:
            name = "new_project"
        if name in self.cards:
            i = 1
            while f"{name}_{i}" in self.cards:
                i += 1
            name = f"{name}_{i}"

        card = ProjectCardWidget(name, self)
        card.rename_requested.connect(self.rename_project)
        card.remove_requested.connect(self.remove_project)
        self.cards[name] = card
        self.cards_layout.addWidget(card)

    def rename_project(self, old_name: str, new_name: str) -> None:
        if new_name in self.cards:
            QMessageBox.warning(self, "命名冲突", f"项目 {new_name} 已存在")
            self.cards[old_name].title_edit.setText(old_name)
            return
        card = self.cards.pop(old_name)
        card.project_name = new_name
        self.cards[new_name] = card

    def remove_project(self, project_name: str) -> None:
        card = self.cards.get(project_name)
        if not card:
            return
        if card.files():
            QMessageBox.warning(self, "禁止删除", "只能删除空项目。")
            return
        self.cards.pop(project_name)
        card.setParent(None)
        card.deleteLater()

    def add_files_to_first_project(self, files: list[str]) -> None:
        if not self.cards:
            self.add_project("default")
        first = next(iter(self.cards.values()))
        first.add_files(files)

    def get_mapping(self) -> dict[str, list[str]]:
        return {name: card.files() for name, card in self.cards.items()}
