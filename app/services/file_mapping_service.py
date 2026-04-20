from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple


class FileMappingService:
    """Validate and normalize project->files mapping."""

    def validate(self, mapping: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], list[str]]:
        errors: list[str] = []
        normalized: Dict[str, List[str]] = {}
        seen_files: set[str] = set()

        for project, paths in mapping.items():
            if not paths:
                continue
            clean: list[str] = []
            for raw in paths:
                p = str(Path(raw).expanduser().resolve())
                if p in seen_files:
                    errors.append(f"重复文件（跨项目不允许）: {p}")
                    continue
                if not Path(p).exists():
                    errors.append(f"路径不存在: {p}")
                    continue
                if not Path(p).is_file():
                    errors.append(f"不是文件: {p}")
                    continue
                seen_files.add(p)
                clean.append(p)
            if clean:
                normalized[project] = clean

        if not normalized:
            errors.append("不能空提交：当前没有可处理文件。")
        return normalized, errors
