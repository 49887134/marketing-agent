# 营销运营工作台：学员运行包

本运行包包含报表页面和知识问答，已经配置课程共用的远程数据库、Embedding 与 Chat 服务。无需安装 PostgreSQL 或 Docker，也不要执行数据库初始化、数据导入或知识入库。

本包内含课程共用服务凭据，仅供收到本包的学员运行课程项目。不要上传到公开仓库、网盘公开链接或聊天群公开文件区。

## 一、准备环境

请先安装：

- Windows 10 或 Windows 11
- Python 3.12，并包含 `py` 启动器
- Node.js 20.19 或更高版本，并包含 npm
- VS Code

打开 PowerShell，分别确认：

```powershell
py -3.12 --version
node --version
npm.cmd --version
```

## 二、解压并安装

1. 把 ZIP 解压到全新目录，例如 `D:\course\marketing-agent-student`。
2. 不要直接在 ZIP 压缩包中运行。
3. 使用 VS Code 打开解压后的 `marketing-agent` 目录。
4. 在 VS Code 中打开 PowerShell 终端，确认当前目录中能看到 `backend`、`frontend`、`.tools` 和 `scripts`。
5. 依次执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action install
```

`check` 检查本机软件、内置配置和网络要求，不显示密码或 API Key。`install` 会创建本机 Python 虚拟环境并安装前后端依赖，首次执行需要等待下载完成。

## 三、启动项目

打开两个 PowerShell 终端，两个终端都位于项目根目录。

终端 A 启动后端，并保持运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action backend
```

浏览器打开 `http://127.0.0.1:8000/docs`，可以查看后端接口。

终端 B 启动前端，并保持运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action frontend
```

浏览器打开 `http://127.0.0.1:5173`。报表页面连接共享数据库；点击左侧“知识问答”可使用已经入库的远程知识库。

当前知识库状态应显示约 10 份文档、4393 个片段。后续由维护者重新入库后，数量可能变化。

可以测试：

```text
2026/6/4 北京的展现是多少？
2026/6/22 创意ID 1441723930885 的点击是多少？
为什么汇总 CTR 不能直接平均各行 CTR？
```

日期、创意 ID、省份等具体记录适合知识检索。全表总和、最大值、排行和趋势需要结构化报表统计，知识问答不会遍历全部片段完成精确计算。

## 四、可选桌面窗口

先停止单独运行的前端终端，再执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action electron
```

后端终端仍需保持运行。`frontend` 和 `electron` 都占用 5173 端口，不要同时启动。

## 五、停止与再次启动

在运行后端或前端的终端按 `Ctrl+C` 停止。

首次安装完成后，再次使用只需要运行：

```powershell
# 终端 A
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action backend

# 终端 B
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/student.ps1 -Action frontend
```

## 六、常见问题

| 现象 | 处理方法 |
| --- | --- |
| 找不到 Python 3.12 | 安装 Python 3.12，重新打开 VS Code，再执行 `py -3.12 --version`。 |
| 找不到 Node 或 npm | 安装 Node.js 后重新打开 VS Code。 |
| 依赖下载失败 | 检查网络后重新执行 `-Action install`。 |
| 数据库连接失败 | 检查网络是否允许访问远程数据库，联系课程维护者确认共享服务状态。 |
| 模型超时或不可用 | 稍后重试，联系课程维护者检查服务额度和权限。 |
| 8000 或 5173 端口被占用 | 关闭重复运行的后端或前端终端，再启动一次。 |
| 知识问答显示依据不足 | 使用更具体的问题，尽量带日期、创意 ID、计划 ID或省份。 |
| 修改配置后没有生效 | 停止后端并重新执行 `-Action backend`。 |

