from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ConfigService:
    """Persists user-level config in local filesystem."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".verify_forpyqt" / "config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {
                "backend_url": "http://127.0.0.1:8000",
                "last_dir": str(Path.home()),
                "last_script_key": "fish2",
                "recent_projects": ["fish2", "TianELake"],
            }
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self, config: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
