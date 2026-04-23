from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from app.controllers.task_controller import TaskController
from app.services.backend_client import BackendClient
from app.services.batch_history_service import BatchHistoryService
from app.services.config_service import ConfigService
from app.services.file_mapping_service import FileMappingService
from app.services.ws_client import TaskWsClient
from app.views.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    config_service = ConfigService()
    history_service = BatchHistoryService()
    config = config_service.load()

    backend_client = BackendClient(config.get("backend_url", "http://127.0.0.1:8000"))
    ws_client = TaskWsClient()
    controller = TaskController(
        backend_client=backend_client,
        ws_client=ws_client,
        file_mapping_service=FileMappingService(),
        history_service=history_service,
    )

    window = MainWindow(controller=controller, config_service=config_service, history_service=history_service)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
