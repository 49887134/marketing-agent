# 百度营销智能运营 Agent

项目包含投放报表、知识检索与 RAG 问答，支持浏览器和 Electron 桌面窗口。前端使用 Vue 3、TypeScript 和 Vite；后端使用 FastAPI、PostgreSQL、pgvector，并通过独立的 Embedding 与 Chat 服务完成问答。

当前报表为示例记录，不代表真实账户业绩。知识资料为项目内部整理内容，不代表百度官方投放规则。当前版本不接入真实广告账户，也不会执行调价。

## 运行条件

- Windows 10/11、PowerShell、VS Code。
- Python 3.12，并包含 Windows `py` 启动器。
- Node.js 20.19 或更高版本及 npm。
- 网络可以访问 npm、PyPI、远程 Supabase、Embedding 和 Chat 服务。
- 项目维护者单独提供的 `backend/.env`。

无需安装本地 PostgreSQL 或 Docker。不要复制其他电脑生成的 `.venv`、`node_modules` 或 `.tools/node_modules`。

## 首次安装

将 ZIP 解压到新目录，例如 `D:\projects\marketing-agent`，用 VS Code 打开包含 `backend`、`frontend`、`.tools` 和 `scripts` 的项目根目录。

把单独取得的 `.env` 放到 `backend/.env`。确认文件名不是 `.env.txt`，也不要将其中的值放到前端 `VITE_*` 环境变量。

在项目根目录的 PowerShell 中执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action install
```

`check` 只检查基础环境和配置文件是否存在，不会输出凭据。`install` 会创建 `backend/.venv`、按锁文件安装 Python 依赖、准备项目 Node 并安装前端依赖。

## 启动

终端 A 在项目根目录启动后端，并保持运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action backend
```

浏览器打开 `http://127.0.0.1:8000/docs` 可以查看接口文档。

终端 B 在项目根目录启动浏览器前端：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action frontend
```

浏览器打开 `http://127.0.0.1:5173`。默认报表范围应显示 21 条记录；切换到“知识问答”后，状态应显示知识库已就绪，并可查看答案、引用来源和检索片段。

如需桌面窗口，停止单独运行的 frontend，再执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action electron
```

后端仍需保持运行。停止服务使用对应终端的 `Ctrl+C`。

## 只读状态检查

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action report-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action db-check
```

正常报表状态为 61 条记录、3 个计划，日期范围 2026-09-01 至 2026-09-21。正常知识库状态为 4 份文档、17 个片段。普通运行不需要执行建表、种子写入或知识入库。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `No suitable Python runtime found` | 安装 Python 3.12，重启 VS Code，再执行 `py -3.12 --version`。 |
| Python 指向其他电脑的路径 | 删除当前目录的 `backend/.venv`，重新执行 install。 |
| `npm.cmd` 找不到 | 安装 Node.js/npm 后重新打开终端。 |
| `Local Node is missing` | 在项目根目录重新执行 install。 |
| 依赖下载失败 | 检查网络后重试 install，不要删除锁文件或强制升级依赖。 |
| `configuration_missing` | 检查 `backend/.env` 的位置和文件后缀，随后重启后端。 |
| `database_unavailable` | 检查网络是否允许访问远程 Supabase 5432 端口。 |
| `knowledge_not_ready` | 联系项目维护者检查远程知识索引。 |
| `embedding_mismatch` | 恢复与索引一致的 Embedding 模型和维度配置。 |
| `model_unavailable` / `model_timeout` | 检查模型服务额度、权限与网络后重试。 |
| 8000 或 5173 被占用 | 停止重复启动的服务后重试。 |
| Electron 下载失败 | 先使用浏览器版本，或运行 `scripts/install-electron.ps1`。 |

接口字段见 [报表接口契约](docs/api-contract.md) 和 [知识接口契约](docs/knowledge-api.md)。
