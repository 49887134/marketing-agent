# 第一阶段实际验证记录

验证日期：2026-09-28。环境：Windows 11 x64，系统 Node 20.19.0/npm 10.8.2，项目 Node 22.22.0，Python 3.12.10，Electron 44.4.5。本记录只描述已实际执行的检查。

## 结果

| 检查 | 实际结果 |
| --- | --- |
| 仓库初始检查 | 初始只有 README，Git 工作区干净，未发现 AGENTS.md 项目约定 |
| Python 安装 | 安装到 backend/.venv；pip freeze 生成 requirements.lock；未使用全局 pip |
| 后端测试 | `backend/.venv/Scripts/python.exe -m pytest -q`（backend 目录使用 `.venv/Scripts/python.exe`）：14 passed |
| Python 依赖一致性 | `python -m pip check`（虚拟环境解释器）：No broken requirements found |
| 前端类型与构建 | `scripts/npm-local.cmd run build`（frontend 目录使用 `../scripts/`）：vue-tsc 和 Vite 均通过；生成 dist |
| 前端依赖审计 | 最终 npm install 审计 125 个包，0 vulnerabilities；工具链安装审计也为 0 |
| 服务就绪检查 | Uvicorn 监听 127.0.0.1:8000，通过计划报表接口确认服务和数据均可访问；`/health` 路由已移除 |
| 真实报表接口 | 默认返回 21 条；日期 9 月 2–4 日 + “课程”返回 3 条；不存在关键词返回空数组与零汇总 |
| 真实参数错误 | 不存在的日期 2026-02-30、开始晚于结束，均返回 HTTP 422 |
| 真实零分母 | 9 月 5 日“新客”返回一条记录，行 CTR/CPC 均为 null |
| 真实汇总一致性 | 对上述成功响应逐项累计返回记录，核对展现、点击、转化、Decimal 金额，均一致 |
| 浏览器自动化 | 本机 Google Chrome：真实查询、组合筛选、重置、空状态、零分母、加载、失败重试、反向日期、连续查询防覆盖通过 |
| Electron 开发模式 | 实际启动窗口，加载 Vite 页面并从真实后端取得 21 条记录 |
| Electron 构建模式 | 实际启动窗口，加载 app://dashboard/index.html，并从真实后端取得 21 条记录 |
| Electron 配置 | 两种模式均断言 contextIsolation=true、nodeIntegration=false、sandbox=true；页面 require 为 undefined |
| UI 测试总结果 | `test:ui` 最终完整执行：5 passed（8.2s）；截图已生成 |

后端 14 个用例包含参数化测试，覆盖包含日期边界、单边日期、关键词空白处理、空结果、非法日期格式、超长关键词、两类零分母、总比率重算和允许/拒绝的 CORS 来源。

浏览器失败与慢请求通过 Playwright 拦截来确定性复现；成功查询都使用真实 FastAPI 数据。桌面验证是实际启动 Electron 的自动化测试，不是仅检查代码。

## 下载与环境问题的处理

最初尝试兼容 Node 20 的 Electron 41.4.0，npm 审计发现 2 项高危依赖问题，最终没有保留这一版本。改为仓库内 Node 22.22.0 与 Electron 44.4.5，更新前端锁文件后审计为 0，不修改全局 Node。

Electron 44 首次自动下载停滞，首次 UI 测试在浏览器 3 项通过后被中止，该次执行不计为完整通过。官方 GitHub 下载也很慢，随后执行 `scripts/install-electron.ps1 -UseMirror`。下载镜像文件的 SHA-256 与已锁定 Electron 包附带值一致：

```text
11c395820a5aaa8ebcc0686b476d0ac98a730274ebfbdc8cf5538a7c2815cb5d
```

完成校验与安装后重新运行全部 5 项 UI 测试，全部通过。下载脚本和故障处理方式已写入 README，镜像仅用作二进制传输来源，不跳过校验。

## 非失败提示

- Starlette 的 TestClient 对 httpx 适配输出一条弃用警告，提示未来迁移到 httpx2；测试通过，当前教学版保留锁定组合。
- 测试运行器的 NO_COLOR/FORCE_COLOR 环境变量产生颜色提示，不影响断言。

## 截图与仍需人工确认的部分

本机截图保存在根目录 `artifacts/browser-dashboard.png`、`artifacts/electron-dev.png`、`artifacts/electron-built.png`。已查看浏览器和 Electron 构建版截图，中文、模拟标识、指标及表格正常。这些属于本地验证产物，不进入 Git。

尚未验证：macOS/Linux、其他浏览器、其他 Python 版本、高 DPI/多显示器下的长期桌面体验、全新机器从零下载依赖、脱网环境。授课前请人工确认本机窗口缩放、日期控件操作和投屏可读性。没有执行桌面安装包、Docker 或后续 AI 功能验证，这些功能本阶段未实现。

测试使用的临时服务与窗口在结束后关闭；按 README 启动自己的后端和前端即可。未提交、推送、创建教学标签或修改远程仓库地址。
## 第二课验证入口

第二课独立验证记录见 [lesson-2-verification.md](lesson-2-verification.md)。区分隔离测试、真实本地 HTTP、远程数据库/模型和学生包检查；上文为第一课历史验证记录。
