# verify_forPyqt

`verify_forPyqt` 已升级为 **可扩展的多功能 PyQt5 桌面应用框架**。

- `MainWindow` = Application Shell（菜单栏 + 左侧导航 + 中间多页面栈 + 状态栏）
- `TaskSubmitPage` = 任务提交与后端通信功能页
- 预留页面：`MouseTrackPage`、`SettingsPage`、`AboutPage`

## 后端契约（verifyfor_django / 20260227run）

### REST
- `POST /api/tasks/`
- `GET /api/tasks/<uuid>/`

### WebSocket
- `ws://<host>/ws/tasks/<task_id>/`

### 创建任务字段
- `script_key`
- `input_path`
- `params_json`

### 状态值
- `QUEUED`
- `STARTED`
- `PROGRESS`
- `SUCCESS`
- `FAILURE`

## 架构（长期扩展导向）

```text
app/
  main.py
  resources/ui/
    main_window.ui
    pages/
      task_submit_page.ui
      mouse_track_page.ui
      settings_page.ui
      about_page.ui
  views/
    main_window.py
    pages/
      task_submit_page.py
      mouse_track_page.py
      settings_page.py
      about_page.py
  controllers/
    task_controller.py
  widgets/
    file_explorer.py
    project_board.py
    project_card.py
    task_detail_panel.py
  services/
    backend_client.py
    ws_client.py
    payload_builder.py
    config_service.py
    file_mapping_service.py
    batch_history_service.py
  models/
    dto.py
    task_state.py
    ui_state.py
```

## MainWindow（应用壳）职责

- 仅负责：
  - 加载主窗口骨架 `.ui`
  - 管理菜单栏 `QAction`
  - 管理左侧导航
  - 管理 `QStackedWidget`
  - 页面注册 `register_page(page_key, page_widget, title)`
  - 页面切换 `switch_page(page_key)`
- 不承载任务提交业务细节

## TaskSubmitPage（独立业务页）职责

- 复用并承载：
  - `TaskController`
  - `FileExplorerWidget`
  - `ProjectBoardWidget`
  - `TaskDetailPanel`
- 功能：
  - backend URL / script_key / extra params
  - 左侧文件浏览器 + 右侧项目分组
  - Start Batch / Reconnect WS / Save Config
  - batch 进度、日志、子任务详情

## Batch 编排层（解决 UI 与后端模型矛盾）

UI 一次可组织多个项目和多文件；提交时按文件拆分为多个后端任务：

每个文件对应一个 payload：
- `script_key`: 来自 UI
- `input_path`: 文件绝对路径
- `params_json` 至少包含：
  - `project_name`
  - `client = "verify_forPyqt"`
  - `batch_id`
  - 额外 UI 参数

## 线程与通信策略

- 所有 REST 调用通过 `QThreadPool + QRunnable` 执行，不阻塞 GUI 线程
- 优先 WebSocket 实时更新
- WebSocket 异常时自动回落到 REST polling（fallback）

## 菜单栏说明

### 文件(File)
- 打开配置 / Open Config
- 保存配置 / Save Config
- 导出批次历史 / Export Batch History
- 退出 / Exit

### 页面(View)
- 切换到任务提交页
- 切换到鼠标轨迹页
- 切换到设置页
- 切换到关于页

### 工具(Tools)
- 重新连接 WebSocket
- 清理本地批次历史
- 打开配置目录

### 帮助(Help)
- 关于
- 使用说明

## 本地持久化

- `~/.verify_forpyqt/config.json`
  - backend URL
  - 最近目录
  - 最近 script key
  - 最近项目名
- `~/.verify_forpyqt/batch_history.json`
  - 本地批次历史（不依赖后端 records API）

## 如何新增新页面

1. 新建页面 `.ui`：`app/resources/ui/pages/<new_page>.ui`
2. 新建页面 view：`app/views/pages/<new_page>.py`
3. 在 `MainWindow.__init__` 中实例化并注册：
   - `register_page("new_key", new_page_widget, "新页面")`
4. 在导航和菜单中添加对应入口，统一调用 `switch_page("new_key")`

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```
