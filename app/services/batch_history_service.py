from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class BatchHistoryService:
    """Persist local batch history; no dependency on backend records API."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".verify_forpyqt" / "batch_history.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def append(self, snapshot: Dict[str, Any]) -> None:
        history = self.load()
        history.insert(0, snapshot)
        self.path.write_text(json.dumps(history[:100], ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self.path.write_text("[]", encoding="utf-8")

    def export_to(self, export_path: Path) -> None:
        data = self.path.read_text(encoding="utf-8") if self.path.exists() else "[]"
        export_path.write_text(data, encoding="utf-8")
