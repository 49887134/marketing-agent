# 营销运营工作台：报表与知识问答

本项目包含 Vue 3 + TypeScript 前端、FastAPI 后端和 Electron 窗口。课程样本报表和知识文档都存储于教师与学员共用的远程 Supabase PostgreSQL；知识片段通过 pgvector 检索，再由独立配置的生成模型回答。报表仍是课程样本，知识文档是教学整理资料，都不代表真实百度推广账户或官方规则。

本代码包不包含真实 `.env`、密钥、依赖目录和虚拟环境。真实后端 `.env` 由教师单独发送。无需安装本地 PostgreSQL 或 Docker，也无需再次初始化报表表、导入报表种子或入库知识文档。

## 课前需要准备

1. Windows 10/11、VS Code、PowerShell（终端显示 `PS`，不要选择 Git Bash）。
2. Python **3.12**，安装时包含 Windows `py` 启动器。检查 `py -3.12 --version`。
3. Node.js **20.19 或更高版本**及 npm，检查 `node --version`、`npm.cmd --version`。安装脚本会在项目 `.tools` 目录安装锁定的 Node **22.22.0**，不改全局 Node。
4. 网络可访问 npm、PyPI、远程 Supabase 的 TCP 5432，以及教师配置的 Embedding 和 Chat HTTPS 服务；Electron 首次运行还需要下载运行时。
5. 从教师收到本项目后端 `.env`。其中数据库、Embedding、Chat 都必须配置有效。模型调用可能产生服务费用，使用约定的教学服务。

请课前确认基础软件和网络。课堂的十五分钟用于解压、安装项目依赖与启动；首次下载速度不可保证。如遇网络慢，应提前拿到代码包执行安装，不要把安装基础软件留到课堂。

## 课堂启动：按顺序执行

把 ZIP 解压到一个**全新目录**，例如 `D:\course\marketing-agent-lesson2`。在 VS Code 打开包含 `backend`、`frontend`、`.tools`、`scripts` 的项目根目录。不要在 ZIP 内运行，不要复制其他电脑的 `.venv` 或 `node_modules`。

把教师单独发来的 `.env` 放到 `backend/.env`。检查资源管理器是否隐藏扩展名，避免误命名为 `.env.txt`。不要把后端密钥放到 `frontend/.env.local` 或任何 `VITE_*` 变量中。

以下命令均在**项目根目录的 PowerShell**执行。路径可有空格，`Set-Location` 时加引号。

```powershell
Set-Location 'D:\course\marketing-agent-lesson2'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action install
```

`check` 检查基础命令和 `.env` 文件是否存在，不输出密钥，也不代表已连接远程服务。`install` 创建本机 Python 虚拟环境、安装锁定依赖、准备项目 Node、安装前端依赖；不会覆盖已有 `.env`。

**终端 A：启动后端，保持运行。**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action backend
```

打开 `http://127.0.0.1:8000/docs`。展开 `GET /api/knowledge/status`，点击 **Try it out → Execute**，查看 `ready`、`document_count`、`chunk_count`。当前千帆配置的初始资料为 **4 份、17 段**。未就绪时先按返回的 `message` 排查。

**终端 B：启动浏览器前端，保持运行。**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action frontend
```

打开 `http://127.0.0.1:5173`，点击左侧“知识问答”。先点“刷新状态”，再用第一个示例问题点击“提问”。正常时看到回答、引用依据和检索片段。展开片段可查看来源、原文和相似度。

**可选：Electron。** 已有浏览器开发服务运行时，新终端执行：

```powershell
Set-Location frontend
..\scripts\npm-local.cmd exec -- electron . --dev
```

若没有运行浏览器开发服务，可在项目根目录执行下面命令，它会启动 Vite 和桌面窗口：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action electron
```

不要同时运行 `-Action frontend` 和 `-Action electron`，它们都需要 5173 端口。后端始终独立运行。停止服务使用对应终端的 Ctrl+C。

## 验证与观察

- “为什么汇总 CTR 不能直接平均各行 CTR？”：查看回答是否使用总点击/总展现，并引用汇总计算资料。
- “把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？”：换一种说法，观察是否检索到同一主题。
- “百度推广账户退款需要哪些材料、几个工作日到账？”：资料没有该政策，应提示依据不足。
- 对第一个问题把 `top_k` 从 1 改为 3，分别点击“仅检索”；观察片段数量、顺序和主题，不保证更多片段一定更好。

这些是验收目标，实际结果取决于所配置模型与索引。相似度不是答案可信度。引用校验保证引用 ID 来自本次检索，但仍需对照原文判断回答是否准确。

## 常见错误

| 现象 | 处理 |
| --- | --- |
| `No suitable Python runtime found` | 安装 Python 3.12，关闭后重新打开 VS Code，执行 `py -3.12 --version`。 |
| 指向他人电脑的 Python 路径 | 解压到全新目录并运行 install，不要使用复制来的 `.venv`。 |
| `npm.cmd` 找不到 | 安装 Node.js/npm 后重开终端。 |
| `Local Node is missing` | 在根目录重新执行 install；包内 `.tools/package-lock.json` 会安装 Node，不依赖教师电脑目录。 |
| 前端安装网络失败 | 恢复网络后重试 install；保留错误信息，不要删除锁文件或强制升级依赖。 |
| `configuration_missing` | 检查 `backend/.env` 位置和后缀；修改后重启后端。不要公开展示文件内容。 |
| `database_unavailable` | 检查网络能否访问 Supabase 5432，联系教师检查项目是否暂停、密码和 SSL。 |
| `knowledge_not_ready` | 教师检查入库；学员不执行 init/ingest，避免改动共用资料。 |
| `embedding_mismatch` | 使用教师同一份模型与维度配置，不要自行切换 Embedding 模型；需要切换时由教师统一重建。 |
| `embedding_input_too_long` | 当前 embedding-v1 问题输入采用 360 UTF-8 字节保护；缩短问题，服务不会静默截断。 |
| `model_unavailable` / `model_timeout` | 教师检查模型服务地址、模型权限、额度和网络；稍后重试。 |
| `invalid_model_answer` | 模型未按 JSON/引用约定返回，重试并由教师检查模型兼容性；不会展示未通过校验的回答。 |
| 8000/5173 被占用 | 关闭自己重复启动的服务，再启动一次。 |
| PowerShell 禁止脚本运行 | 使用上文 `powershell.exe ... -ExecutionPolicy Bypass -File ...`，仅对本次进程生效。 |
| Electron 下载失败 | 可先用浏览器；课前按 `scripts/install-electron.ps1` 下载运行时。 |

技术说明见 [第二课运行与配置](docs/lesson-2-run.md) 和 [知识接口](docs/knowledge-api.md)。本包保留必要源码、锁文件、知识资料及技术说明，不包含教师授课指南。
