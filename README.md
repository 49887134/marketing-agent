# 百度营销智能运营 Agent

第一节课的**教师参考完成版**：可在浏览器与 Electron 中运行的中文投放数据看板。所有数据都是**教学模拟数据**，没有连接真实百度推广账户，不执行真实调价。本课帮助学员把已有 Vue / TypeScript / Electron 基础与 Python HTTP 服务连接起来。

已实现：日期和计划名称筛选、查询/重置、四项汇总、每日明细、加载/空数据/失败/重试、重复请求防覆盖、参数校验、Decimal 金额计算及自动化验证。未实现：RAG、大模型、PostgreSQL/pgvector、LangGraph、权限系统、Docker、桌面安装包、后端自动打包、微调、OCR/VLM。后续规划见 [项目路线图](docs/project-roadmap.md)。

## 技术栈与目录

Vue 3 Composition API + TypeScript + Vite，使用原生 HTML/CSS 实现轻量管理后台；Electron 复用同一套页面；Python + FastAPI + Pydantic 提供只读模拟报表。

```text
.tools/                 仓库内 Node 22 工具链及锁文件
scripts/npm-local.cmd   用项目 Node 运行本机 npm 的 Windows 入口
frontend/
  electron/main.cjs     桌面窗口、安全设置、静态资源协议
  src/api/             HTTP 请求封装
  src/components/      筛选、指标和表格
  src/App.vue          查询流程和页面状态
  tests/               浏览器及 Electron 联调测试
backend/
  app/main.py          应用初始化和 CORS
  app/routes/          参数校验和路由
  app/models.py        数据模型和接口字段
  app/services/        读取、筛选、计算、汇总
  tests/               后端测试
data/mock/             固定 JSON 样本及可重复生成脚本
data/knowledge/        后续课程文档占位目录
docs/                  接口、授课指南、作业、后续规划
```

## 环境与版本选择

实际检查环境：Windows 11（系统内核 10.0.26200）、PowerShell、系统 Node.js **20.19.0**、npm **10.8.2**、Python **3.12.10**。下文命令均用于 Windows PowerShell，并注明执行目录。不要全局 pip 安装，也无需激活虚拟环境。

Vite 7 支持系统 Node 20.19，但当前 Electron 44 安装工具要求 Node >=22.12。试用兼容 Node 20 的旧 Electron 时，npm audit 报告了已知高危漏洞，因此最终选择 **Electron 44.4.5 + 仓库内 Node 22.22.0**。项目 Node 只装在 `.tools/node_modules`，`scripts/npm-local.cmd` 仅为子进程设置 PATH，不改变系统 Node、注册表或全局安装。脚本使用本机既有 npm CLI，本机验证版本为 10.8.2。

前端完整版本由 `frontend/package-lock.json` 固定；Node 工具链由 `.tools/package-lock.json` 固定；后端版本由 `backend/requirements.lock` 固定，Python 3.12 为已验证版本。`requirements.in` 仅描述更新时的直接依赖范围，日常安装使用 lock。不要通过 `npm audit fix --force` 盲目更新教学工具链。

参考：[Vite 环境要求](https://vite.dev/guide/)、[Electron 安全设置](https://www.electronjs.org/docs/latest/tutorial/security)。

## 首次安装

以下以当前仓库路径为例；其他机器替换仓库路径即可。

```powershell
# 仓库根目录：先安装项目局部 Node，使用现有系统 npm 即可
Set-Location D:\marketing-agent\marketing-agent
Set-Location .tools
npm.cmd ci
Set-Location ..

# 仓库根目录：创建项目 Python 虚拟环境并按锁文件安装
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock

# frontend 目录：用局部 Node 安装前端依赖
Set-Location frontend
..\scripts\npm-local.cmd ci
Copy-Item .env.example .env.local
```

`.env.local` 中的 `VITE_API_BASE_URL=http://127.0.0.1:8000` 是报表请求地址。未配置时同样使用该本地默认值；修改后重启 Vite，构建版需要重新构建。前端环境变量会进入客户端，不要放密钥。

## 启动和查看

**终端 A：后端（backend 目录）**

```powershell
Set-Location D:\marketing-agent\marketing-agent\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

接口文档：`http://127.0.0.1:8000/docs`。可通过计划报表接口 `http://127.0.0.1:8000/api/reports/campaigns` 确认服务和数据均可访问。本地服务默认只监听回环地址。

**终端 B：以下选择一种前端运行方式（frontend 目录）**

```powershell
Set-Location D:\marketing-agent\marketing-agent\frontend

# 浏览器开发：打开 http://127.0.0.1:5173
..\scripts\npm-local.cmd run dev
```

```powershell
# Electron 开发：自动启动 Vite，等待就绪后打开桌面窗口
# 执行目录：frontend。不要同时运行另一份占用 5173 的 dev 服务。
..\scripts\npm-local.cmd run electron:dev
```

```powershell
# 前端类型检查和构建；只产出 frontend/dist，不生成桌面安装包
# 执行目录：frontend
..\scripts\npm-local.cmd run build

# 使用构建产物启动 Electron，不需要 Vite；终端 A 的后端仍须运行
..\scripts\npm-local.cmd run electron:start
```

```powershell
# 可选：在浏览器预览构建产物，打开 http://127.0.0.1:4173
# 执行目录：frontend，先执行 build
..\scripts\npm-local.cmd run preview
```

若已启动 Vite，另一个 frontend 终端可以用 `..\scripts\npm-local.cmd exec -- electron . --dev` 直接打开开发窗口。`electron:dev` 中关闭桌面窗口会结束它自己启动的 Vite；其他前台服务用 Ctrl+C 停止。

默认日期为 **2026-09-01 至 2026-09-07**，包含 3 个计划、21 条记录；完整汇总为展现 **48,480**、点击 **1,131**、消费 **¥2,268.10**、转化 **30**。重置会恢复这一范围，不会跳到当前日期。

Mock 数据共 **61 条**，已追加 **2026-09-08 至 2026-09-21** 的 40 条记录。将结束日期改为 **2026-09-21** 并查询即可查看全部数据；运行 `python data/mock/generate.py` 可重新生成。

## 架构与教学要点

Vue 只提交筛选并展示结果，后端从 `data/mock/campaigns.json` 读取记录，再筛选、计算、汇总。金额以字符串存储，Python Decimal 计算；接口金额仍是字符串，点击率为小数，零分母为 null。汇总比率使用汇总分子/分母重新计算。

`App.vue` 使用 AbortController 取消上一个查询，并用请求序号保护结果、错误和 loading 状态；失败或加载期间隐藏旧结果，防止把旧数据误认为新查询结果。请求超时 15 秒，重试使用最后提交的条件。

Electron 开启 `contextIsolation`、`sandbox`，关闭 `nodeIntegration`，没有 preload、任意文件或命令执行 IPC。构建版通过受限的 `app://dashboard` 协议访问 dist；Vite `base: './'` 使用相对资源路径。本阶段单页面没有前端路由器；以后增加路由时可采用 hash 路由。

后端 CORS 显式允许本机 5173/4173 浏览器来源及 `app://dashboard`，不开放 `*` 或 `null`。自定义端口时，在 backend 终端启动前配置完整白名单，例如：

```powershell
$env:CORS_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173,app://dashboard'
```

## 验证方法

```powershell
# backend 目录：筛选、计算、参数校验和 CORS
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

```powershell
# frontend 目录：构建会先执行类型检查
..\scripts\npm-local.cmd run typecheck
..\scripts\npm-local.cmd run build
..\scripts\npm-local.cmd run test:ui
```

UI 测试配置使用本机 Google Chrome（无需下载 Playwright 浏览器），并自动启动后端与 Vite，也可以复用已运行的本项目服务。需先安装 Python 依赖、前端依赖并构建 dist；执行时会打开 Electron 窗口并自动关闭。没有 Chrome 时可安装 Chrome，或把 `playwright.config.ts` 的 channel 改为本机 `msedge`；本次不代表已验证其他浏览器。截图位于根目录 `artifacts/`，失败产物位于 `frontend/test-results/`，均不提交 Git。

Electron 44 首次启动会下载对应桌面运行时，需要可用网络；可课前在 frontend 目录执行 `..\scripts\npm-local.cmd exec -- install-electron` 提前下载，再开始演示或 UI 测试。

如果自动下载长时间停滞，仓库提供 Windows x64 备用下载脚本（从根目录执行），下载后必须匹配已锁定 Electron 包内的 SHA-256 才会解压：

```powershell
# 仓库根目录；默认从 GitHub 官方发布下载
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install-electron.ps1
# GitHub 下载过慢时，可选择镜像；仍使用同一个官方包校验值
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install-electron.ps1 -UseMirror
```

该执行策略仅作用于本次脚本进程，不修改系统策略。文件只写入仓库 `artifacts` 与 `frontend/node_modules/electron`。当前机器首次下载遇到停滞，使用了这一备用方式。

```powershell
# 任意目录：后端启动后执行真实 HTTP 验证
Invoke-RestMethod http://127.0.0.1:8000/api/reports/campaigns
Invoke-RestMethod 'http://127.0.0.1:8000/api/reports/campaigns?start_date=2026-09-02&end_date=2026-09-04&keyword=%E8%AF%BE%E7%A8%8B'
```

手工验收：默认 21 条；“课程”与 9 月 2–4 日返回 3 条；不存在关键词显示空数据；开始晚于结束显示错误；关闭后端后查询显示连接失败，重启后重试恢复。查看 9 月 2 日新客计划（CTR 为 0、CPC 为“—”）与 9 月 5 日新客计划（两个比率均为“—”）。

具体已执行结果、限制见 [验证记录](docs/verification.md)。

## 常见问题

- **Electron 安装时 Node 不兼容**：不要在 frontend 直接用系统 Node 20 执行 npm install。先在 `.tools` 执行 `npm.cmd ci`，随后使用 `scripts/npm-local.cmd`；无需升级全局 Node。安装失败重试同一 ci 命令，网络需能访问 npm registry 和 Electron 二进制下载源。
- **PowerShell 禁止运行 npm.ps1**：文档显式使用 `.cmd`，不需要改变执行策略。Python 直接运行虚拟环境解释器，不需要 Activate.ps1。
- **页面连接失败**：先访问 `/docs` 或 `/api/reports/campaigns`，再查 Network；核对 8000 端口、`.env.local` 及 CORS 来源。修改前端环境配置后必须重启或重新构建。`localhost` 与 `127.0.0.1` 是不同来源。
- **端口被占用**：Vite 设置 strictPort，避免自动换端口后 CORS 失配；停止自己重复启动的服务。不要随意结束不认识的进程。
- **Electron 白屏**：构建模式须先 build，并用 electron:start 加载 `app://dashboard`，不要双击 dist/index.html。后端未启动应显示错误状态，不应白屏。
- **日期没有数据**：样本固定在 2026 年 9 月，点击重置；清空日期可查询不限日期范围。
- **中文乱码**：源文件使用 UTF-8；若旧 PowerShell 显示异常，用编辑器查看 UTF-8 文件，浏览器接口和页面也使用 UTF-8。
- **测试提示 httpx 弃用警告**：当前 Starlette 对 TestClient 的 httpx 适配提示未来迁移到 httpx2；现有测试仍可运行，此提示不影响运行服务。升级教学依赖时统一评估并更新锁文件。

## 教学文档

- [接口契约](docs/api-contract.md)：参数、单位、响应与错误。
- [导师 60 分钟授课指南](docs/lesson-1-guide.md)：每段时间打开的文件及演示动作。
- [学员课后任务](docs/lesson-1-homework.md)：提交要求及验收标准。
- [后续项目规划](docs/project-roadmap.md)：尚未实现的 RAG、LangGraph、评测和 Docker。

没有创建教学标签、自动提交或推送 Git，也没有提供删减版或 TODO 练习版。
