# verify_forPyqt

一个用于对接 `verifyfor_django` 的 PyQt5 初代桌面前端。

## 已实现能力

- 左侧文件浏览器（地址栏 + 文件树 + 多选）
- 右侧项目分类区（默认含 `fish2`、`TianELake`，支持拖拽跨项目移动）
- 任务提交：将项目文件映射和参数组合为 JSON payload 提交后端
- 进度联动：轮询任务状态并显示进度、状态日志
- 记录联动：读取后端处理记录并展示

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## 后端 API 约定（可按你的 Django 代码调整）

默认后端地址：`http://localhost:8000`

- `POST /api/tasks/submit`
  - 请求体：
    - `project_files`: `{项目名: [文件绝对路径...]}`
    - `options`: 处理参数
    - `submitted_at`: ISO 时间
  - 响应体示例：`{"task_id": "task-001"}`

- `GET /api/tasks/{task_id}/status`
  - 响应体示例：
    - `{"task_id":"task-001","status":"running","progress":42,"message":"处理中"}`

- `GET /api/tasks/records`
  - 响应体示例：
    - `{"records":[{"task_id":"task-001","status":"success","finished_at":"..."}]}`

## 代码结构

- `app/main.py`：主窗口和 UI 逻辑
- `app/widgets/file_explorer.py`：左侧文件浏览器
- `app/widgets/project_board.py`：右侧项目拖拽看板
- `app/services/backend_client.py`：后端通信封装
- `app/services/task_controller.py`：提交/轮询/记录逻辑

后续你可以在 `task_controller.py` 中扩展 WebSocket 或 SSE 实时通信。
