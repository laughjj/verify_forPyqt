from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UiSubmissionState:
    backend_url: str
    script_key: str
    extra_params: dict
    project_files: Dict[str, List[str]] = field(default_factory=dict)
