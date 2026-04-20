from __future__ import annotations

import json
import threading
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from websocket import WebSocketApp


class TaskWsClient(QObject):
    """Thin WebSocket wrapper for ws://<host>/ws/tasks/<task_id>/ updates."""

    message_received = pyqtSignal(str, dict)
    disconnected = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._apps: dict[str, WebSocketApp] = {}
        self._threads: dict[str, threading.Thread] = {}

    @staticmethod
    def to_ws_url(base_url: str, task_id: str) -> str:
        url = base_url.rstrip("/")
        if url.startswith("https://"):
            ws_base = "wss://" + url[len("https://") :]
        elif url.startswith("http://"):
            ws_base = "ws://" + url[len("http://") :]
        else:
            ws_base = "ws://" + url
        return f"{ws_base}/ws/tasks/{task_id}/"

    def subscribe(self, base_url: str, task_id: str) -> None:
        if task_id in self._apps:
            return

        url = self.to_ws_url(base_url, task_id)

        def on_message(_: WebSocketApp, message: str) -> None:
            try:
                payload = json.loads(message)
            except Exception:
                self.disconnected.emit(task_id, "Malformed websocket message")
                return
            self.message_received.emit(task_id, payload)

        def on_error(_: WebSocketApp, error: Exception) -> None:
            self.disconnected.emit(task_id, f"WS error: {error}")

        def on_close(_: WebSocketApp, status_code: int, msg: str) -> None:
            self.disconnected.emit(task_id, f"WS closed ({status_code}): {msg}")

        app = WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
        thread = threading.Thread(target=app.run_forever, daemon=True)
        self._apps[task_id] = app
        self._threads[task_id] = thread
        thread.start()

    def unsubscribe_all(self) -> None:
        for app in self._apps.values():
            try:
                app.close()
            except Exception:
                pass
        self._apps.clear()
        self._threads.clear()
