# Light OJ

Light OJ 是一个使用 FastAPI、SQLite 和原生 HTML/CSS/JavaScript 实现的轻量级 Online Judge。系统提供学生、教师和管理员三类角色，支持题目管理、Python 代码提交、异步评测、按测试点计分、分角色日志展示、用户管理以及数据备份与恢复。

## 环境要求

- Python 3.10 或以上（当前开发与测试环境为 Python 3.14.0）

## 安装与启动

建议在虚拟环境中运行：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Linux/macOS：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问：

- 前端首页：<http://127.0.0.1:8000/>
- Swagger API 文档：<http://127.0.0.1:8000/docs>
- OpenAPI 定义：<http://127.0.0.1:8000/openapi.json>

前端源码位于 `frontend/` ,由 FastAPI 作为静态文件挂载到根路径，因此不需要单独启动前端。

## 初始账号

首次启动时，系统会在数据库中自动创建以下演示账号：

| 角色 | 用户名 | 初始密码 |
| --- | --- | --- |
| 管理员 | `admin` | `admin12345` |
| 教师 | `teacher` | `teacher123` |

普通学生可在前端注册，注册后的角色固定为 `student`。

## 数据与备份

- SQLite 数据库：`data/oj.db`
- 备份目录：`data/backups/<backup_id>/`
- 每份备份包含：`oj.db` 和 `manifest.json`
- 测试临时数据：`temp/`（已由 `.gitignore` 排除）

数据库和备份不会提交到 Git。删除本地 `data/oj.db` 后再次启动可初始化一个新数据库和初始账号，但会丢失原有本地数据。

恢复备份前，系统会先释放当前数据库连接，并将当前 `oj.db` 复制为 `.rollback` 回滚副本；选定的备份先复制到 `.restore` 临时文件，再原子替换主数据库。若恢复过程中发生异常，系统会用 `.rollback` 还原原数据库；恢复成功或回滚完成后会删除回滚副本，并始终清理 `.restore`，避免恢复失败破坏现有数据或遗留临时文件。

## 运行测试

安装依赖后，在项目根目录执行：

```bash
pytest
```

当前测试结果为 `35 passed`，覆盖认证与权限、题目 CRUD 和字段校验、隐藏测试点、提交所有权、重新评测、AC/WA/RE/TLE、输出规范化、SPJ、日志脱敏与截断、SQLite 持久化存储、备份创建与恢复、备份文件缺失保护、恢复异常回滚及临时文件清理。其中新增测试会在主数据库已经被替换后模拟异常，确认系统能恢复原数据，并删除 `.restore` 和 `.rollback` 临时文件。

## 主要 API

所有业务接口均以 `/api` 开头，统一返回 `code`、`message` 和 `data`。主要接口如下：

| 模块 | 接口 |
| --- | --- |
| 认证 | `POST /api/auth/register`、`POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me` |
| 用户 | `GET /api/users`、`GET /api/users/{user_id}`、`PUT /api/users/{user_id}` |
| 题目 | `GET/POST /api/problems`、`GET/PUT/DELETE /api/problems/{problem_id}` |
| 提交 | `POST/GET /api/submissions`、`GET /api/submissions/{id}`、`POST /api/submissions/{id}/rejudge` |
| 日志 | `GET /api/submissions/{id}/logs`、`GET /api/logs`、`GET /api/logs/audit-logs` |
| 备份 | `POST/GET /api/admin/backups`、`POST /api/admin/backups/{backup_id}/restore` |

完整参数和响应模型可在服务启动后查看文档。

## 项目结构

```text
app/
  judge/          # 子进程执行、输出比较和 SPJ
  models/         # Pydantic 请求模型与校验
  repositories/   # SQLAlchemy 配置、ORM 表和示例题目
  routers/        # FastAPI 路由
  services/       # 认证、异步评测、日志等业务逻辑
  utils/          # 其他模块使用的方法
frontend/         # 原生前端
tests/            # pytest 自动化测试
report/report.md  # 实验报告
scripts/          # 方便测试的脚本
data/             # 运行时数据库和备份
temp/             # 测试临时文件
```

## 已知限制

- 基础评测只支持 Python，未实现内存限制、网络隔离和文件系统沙箱。
- 后台评测使用进程内 `asyncio.create_task()`，不具备分布式队列能力；服务重启时处于 `pending/running` 的提交会被标记为 `failed/SE`。
- 目前项目在恢复备份时尚未校验备份数据库的完整性（仅检查存在性），但在复制过程出错后会进行回滚
- 在演示中，Session 密钥没有随机生成，为固定字符串

完整介绍见 [实验报告](report/report.md)。
