from __future__ import annotations

from pathlib import Path

from PyQt5 import uic
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QAction, QListWidgetItem, QMainWindow, QMessageBox, QWidget

from app.controllers.task_controller import TaskController
from app.services.batch_history_service import BatchHistoryService
from app.services.config_service import ConfigService
from app.views.pages.about_page import AboutPage
from app.views.pages.mouse_track_page import MouseTrackPage
from app.views.pages.settings_page import SettingsPage
from app.views.pages.task_submit_page import TaskSubmitPage


class MainWindow(QMainWindow):
    """Application shell: menu, navigation, page registration and switching."""

    def __init__(self, controller: TaskController, config_service: ConfigService, history_service: BatchHistoryService) -> None:
        super().__init__()
        ui_path = Path(__file__).resolve().parent.parent / "resources" / "ui" / "main_window.ui"
        uic.loadUi(str(ui_path), self)
        self.mainSplitter.setSizes([260, 1300])

        self.controller = controller
        self.config_service = config_service
        self.history_service = history_service

        self.page_indexes: dict[str, int] = {}
        self.page_titles: dict[str, str] = {}
        self.pages: dict[str, QWidget] = {}

        self.task_submit_page = TaskSubmitPage(controller, config_service, history_service, self)
        self.mouse_track_page = MouseTrackPage(self)
        self.settings_page = SettingsPage(self)
        self.about_page = AboutPage(self)

        self.register_page("task_submit", self.task_submit_page, "任务提交")
        self.register_page("mouse_track", self.mouse_track_page, "鼠标轨迹")
        self.register_page("settings", self.settings_page, "设置")
        self.register_page("about", self.about_page, "关于")

        self._setup_navigation()
        self._setup_menu_bar()
        self.switch_page("task_submit")

    def register_page(self, page_key: str, page_widget: QWidget, title: str) -> None:
        if page_key in self.page_indexes:
            raise ValueError(f"Duplicate page key: {page_key}")
        index = self.contentStackedWidget.addWidget(page_widget)
        self.page_indexes[page_key] = index
        self.page_titles[page_key] = title
        self.pages[page_key] = page_widget

    def switch_page(self, page_key: str) -> None:
        if page_key not in self.page_indexes:
            QMessageBox.warning(self, "页面不存在", f"未注册页面: {page_key}")
            return
        self.contentStackedWidget.setCurrentIndex(self.page_indexes[page_key])
        self.statusbar.showMessage(f"当前页面: {self.page_titles[page_key]}", 2000)
        self._sync_navigation(page_key)

    def _setup_navigation(self) -> None:
        for key, title in self.page_titles.items():
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, key)
            self.navigationListWidget.addItem(item)
        self.navigationListWidget.currentItemChanged.connect(self._on_nav_changed)

    def _sync_navigation(self, page_key: str) -> None:
        for row in range(self.navigationListWidget.count()):
            item = self.navigationListWidget.item(row)
            if item.data(Qt.UserRole) == page_key:
                self.navigationListWidget.blockSignals(True)
                self.navigationListWidget.setCurrentRow(row)
                self.navigationListWidget.blockSignals(False)
                break

    def _on_nav_changed(self, current: QListWidgetItem, _previous: QListWidgetItem) -> None:
        if current is None:
            return
        key = current.data(Qt.UserRole)
        if isinstance(key, str):
            self.switch_page(key)

    def _setup_menu_bar(self) -> None:
        file_menu = self.menubar.addMenu("文件(File)")
        view_menu = self.menubar.addMenu("页面(View)")
        tools_menu = self.menubar.addMenu("工具(Tools)")
        help_menu = self.menubar.addMenu("帮助(Help)")

        self.action_open_config = QAction("打开配置 / Open Config", self)
        self.action_save_config = QAction("保存配置 / Save Config", self)
        self.action_export_history = QAction("导出批次历史 / Export Batch History", self)
        self.action_exit = QAction("退出 / Exit", self)

        self.action_open_config.triggered.connect(self.task_submit_page.open_config_file)
        self.action_save_config.triggered.connect(self.task_submit_page.save_config)
        self.action_export_history.triggered.connect(self.task_submit_page.export_batch_history)
        self.action_exit.triggered.connect(self.close)

        file_menu.addActions([self.action_open_config, self.action_save_config, self.action_export_history, self.action_exit])

        self.action_view_task = QAction("切换到任务提交页", self)
        self.action_view_mouse = QAction("切换到鼠标轨迹页", self)
        self.action_view_settings = QAction("切换到设置页", self)
        self.action_view_about = QAction("切换到关于页", self)

        self.action_view_task.triggered.connect(lambda: self.switch_page("task_submit"))
        self.action_view_mouse.triggered.connect(lambda: self.switch_page("mouse_track"))
        self.action_view_settings.triggered.connect(lambda: self.switch_page("settings"))
        self.action_view_about.triggered.connect(lambda: self.switch_page("about"))

        view_menu.addActions([self.action_view_task, self.action_view_mouse, self.action_view_settings, self.action_view_about])

        self.action_reconnect_ws = QAction("重新连接 WebSocket", self)
        self.action_clear_history = QAction("清理本地批次历史", self)
        self.action_open_config_dir = QAction("打开配置目录", self)

        self.action_reconnect_ws.triggered.connect(self.task_submit_page.reconnect_ws)
        self.action_clear_history.triggered.connect(self.task_submit_page.clear_batch_history)
        self.action_open_config_dir.triggered.connect(self.open_config_directory)

        tools_menu.addActions([self.action_reconnect_ws, self.action_clear_history, self.action_open_config_dir])

        self.action_help_about = QAction("关于", self)
        self.action_help_usage = QAction("使用说明", self)
        self.action_help_about.triggered.connect(lambda: self.switch_page("about"))
        self.action_help_usage.triggered.connect(self.show_usage_help)
        help_menu.addActions([self.action_help_about, self.action_help_usage])

    def open_config_directory(self) -> None:
        cfg_dir = self.config_service.path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(cfg_dir)))

    def show_usage_help(self) -> None:
        QMessageBox.information(
            self,
            "使用说明",
            "请在“任务提交”页选择文件并分配项目，点击 Start Processing 后观察下方进度和任务明细。",
        )
