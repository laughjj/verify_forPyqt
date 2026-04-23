from __future__ import annotations

from typing import Dict, Iterable, List


def build_task_payloads(
    *,
    script_key: str,
    batch_id: str,
    project_files: Dict[str, List[str]],
    extra_params: dict,
) -> Iterable[tuple[str, str, dict]]:
    """Yield (project_name, input_path, payload) for backend task creation."""
    for project_name, files in project_files.items():
        for file_path in files:
            params_json = {
                "project_name": project_name,
                "client": "verify_forPyqt",
                "batch_id": batch_id,
                **extra_params,
            }
            yield project_name, file_path, {
                "script_key": script_key,
                "input_path": file_path,
                "params_json": params_json,
            }
