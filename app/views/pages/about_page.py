from __future__ import annotations

from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QWidget


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parents[2] / "resources" / "ui" / "pages" / "about_page.ui"
        uic.loadUi(str(ui_path), self)
