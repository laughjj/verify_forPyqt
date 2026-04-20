# verify_forPyqt

面向 `verifyfor_django` `20260227run` 分支的 PyQt5 桌面任务提交前端。

> 关键定位：UI 支持“多项目/多文件”组织，但后端任务模型是“单 task 对应单 input_path”。
> 本项目通过 **batch orchestration layer** 将一次 UI 提交拆解为多个后端 task，并在本地维护 batch 状态与历史。

## 真实后端契约（已适配）

### REST
- `POST /api/tasks/`
- `GET /api/tasks/<uuid>/`

### WebSocket
- `ws://<host>/ws/tasks/<task_id>/`

### 创建任务 payload 字段
- `script_key`
- `input_path`
- `params_json`

### 任务快照字段（前端解析）
- `id`
- `script_key`
- `input_path`
- `params_json`
- `status` (`QUEUED|STARTED|PROGRESS|SUCCESS|FAILURE`)
- `progress`
- `result_json`
- `error_message`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

## 架构说明（系统化 / 分层）

```text
app/
  main.py
  resources/ui/main_window.ui
  views/main_window.py
  controllers/task_controller.py
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

### View 层
- 从 `.ui` 加载主窗口骨架（不承载业务逻辑）
- 注入自定义 widgets（文件浏览器/项目看板/任务明细）
- 绑定按钮与 controller 信号
- 渲染 batch summary、日志、任务列表

### Controller 层
- 收集 UI 输入
- 做提交前校验（路径存在、是文件、去重、非空）
- 调用 payload builder 拆分子任务
- 异步提交任务（QThreadPool/QRunnable）
- 优先订阅 WebSocket 更新，REST 轮询兜底
- 维护本地 batch state（聚合进度、子任务状态）

### Service 层
- `backend_client`: 真实 REST 调用
- `ws_client`: WebSocket 抽象（可断线重连）
- `payload_builder`: UI 映射到后端 payload
- `file_mapping_service`: 输入校验和规范化
- `config_service`: 本地配置持久化
- `batch_history_service`: 本地 batch 历史持久化（不依赖后端 records）

## Batch 编排规则

一次“开始处理”会生成一个本地 `batch_id`，然后：
1. 遍历 project -> files
2. 对每个 file 生成一个后端任务 payload：
   - `script_key`: UI 选择
   - `input_path`: 文件绝对路径
   - `params_json`: 至少包含
     - `project_name`
     - `client = verify_forPyqt`
     - `batch_id`
     - 额外 UI 参数
3. 将后端返回的 `task_id` 绑定到 batch 子任务
4. 实时显示 batch 聚合进度与每个子任务状态

## WebSocket 与 fallback 说明

- 默认为每个 task 订阅：`/ws/tasks/<task_id>/`
- 若 WS 断开/异常/消息格式错误，不会导致 UI 崩溃
- Controller 会记录日志并继续使用 REST `GET /api/tasks/<uuid>/` 轮询兜底

## 本地持久化

- 配置文件：`~/.verify_forpyqt/config.json`
  - backend URL
  - 最近目录
  - 最近 script_key
  - 最近项目名
- 历史文件：`~/.verify_forpyqt/batch_history.json`
  - batch 基本信息
  - 聚合进度
  - 子任务最终快照

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## 关键设计决策

1. **UI 驱动 + 业务分层**：避免 `main.py`/`main_window.py` 巨石化。
2. **多项目 UI vs 单任务后端**：通过 batch 编排层解决结构矛盾。
3. **非阻塞网络**：所有 REST 调用在 worker 中执行，主线程只渲染。
4. **可靠性优先**：WS 优先，REST fallback；后端离线只报错不崩溃。
5. **可维护 objectName**：`.ui` 中关键组件均有稳定命名，便于后续自动化测试与维护。
