# 第一节课教师逐字讲稿（60 分钟）

## 使用说明

这份讲稿按 60 分钟连续组织，可以直接边讲、边打开文件、边操作。学员已有 Vue 3、TypeScript、Electron、WebSocket、ECharts、接口联调和基础 AI Agent 项目经验，因此前端语法快速带过，重点解释 Python、FastAPI、Pydantic、service 分层和 Decimal。

本课只讲通第一阶段的报表链路，不开发第二阶段。当前 `backend/app/services/reports.py` 是后续项目的重要基础：第三课会把这里的报表查询能力封装成 Agent 可调用的工具。先确保报表工具的输入、计算和返回可信，Agent 才能基于真实结果分析，而不是生成看似合理的数字。

本课主线：

```text
ReportFilters.vue / submit()
→ App.vue / query(filters)
→ api/reports.ts / fetchReports(filters, signal)
→ GET /api/reports/campaigns
→ routes/reports.py / campaigns() + parse_date()
→ services/reports.py / get_campaign_reports()
→ load_campaigns() + ratios()
→ ReportResponse
→ App.vue 更新页面状态
→ MetricCards.vue + ReportTable.vue
```

标记说明：

- **【必讲】** 必须在 60 分钟内讲完，用于建立完整请求链路。
- **【补充】** 时间充足时展开；时间不足只说结论，不打断主线。

课堂实操默认前提：学员已取得代码，依赖已安装，前后端可以运行。如果学员环境临时未就绪，由导师在自己的环境中完成演示，学员按讲稿记录修改位置，独立操作和验收放到课后完成。

---

## 课前 10 分钟准备（不计入课堂）

### 1. 启动后端

在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 `http://127.0.0.1:8000/api/reports/campaigns`，确认能够返回包含 `items`、`summary` 和 `total` 的 JSON。

### 2. 启动前端

在 `frontend` 目录运行：

```powershell
..\scripts\npm-local.cmd run dev
```

打开 `http://127.0.0.1:5173`，确认默认有 21 条记录。

### 3. 准备页面和文件

浏览器提前打开：

- 看板：`http://127.0.0.1:5173`
- Swagger：`http://127.0.0.1:8000/docs`
- DevTools Network，过滤词填 `campaigns`

编辑器按顺序打开：

1. `frontend/src/components/ReportFilters.vue`
2. `frontend/src/App.vue`
3. `frontend/src/api/reports.ts`
4. `frontend/src/types/reports.ts`
5. `backend/app/main.py`
6. `backend/app/routes/reports.py`
7. `backend/app/models.py`
8. `backend/app/services/reports.py`
9. `data/mock/campaigns.json`
10. `frontend/src/components/MetricCards.vue`
11. `frontend/src/components/ReportTable.vue`
12. `frontend/src/format.ts`

演示基准：默认日期为 `2026-09-01` 至 `2026-09-07`；3 个计划 × 7 天 = 21 条；汇总为 48,480 展现、1,131 点击、2,268.10 元消费、30 次转化。

---

## 0–8 分钟：【必讲】开场、项目关系和业务场景

### 0–3 分钟：开场话术

打开：浏览器看板首页，暂时不操作。

直接讲：

> “今天这一小时，我们先把百度营销智能运营 Agent 的数据底座讲清楚。最终项目会有知识库、RAG、Agent 工作流和报表工具调用，但 AI 不能直接凭语言模型生成投放数字。它必须调用一个输入明确、计算准确、错误可控的报表工具。”
>
> “所以第一节课先完成一件基础但非常关键的事：从 Vue 页面提交筛选条件，通过真实 HTTP 请求进入 FastAPI，后端读取数据、完成筛选和汇总，再把结果返回页面。第三课做 Agent 工具调用时，会直接复用今天 `backend/app/services/reports.py` 中的报表能力。”
>
> “你已经有 Vue、TypeScript、Electron、WebSocket 和接口联调经验，前端组件语法我们不会慢讲。今天重点放在 Python 后端如何分层，以及前后端如何通过一份稳定的接口契约协作。”

### 3–6 分钟：业务场景话术

打开：`data/mock/campaigns.json`，展示同一天的 C001、C002、C003 三条记录。

直接讲：

> “这个系统面向投放运营人员。页面接收开始日期、结束日期和计划名称关键词，返回筛选范围内的汇总指标和每日计划明细。”
>
> “数据粒度是‘一个计划在一天内的数据’。当前有三个计划，覆盖连续七天，因此默认返回二十一条记录。`total` 表示日报记录数，不表示计划数。”
>
> “原始数据包含日期、计划 ID、计划名称、展现量、点击量、消费和转化数。点击率 CTR 和平均点击成本 CPC 没有写死在 JSON 中，而是由后端根据原始指标计算。这样计算口径集中在一处，未来数据源换成 PostgreSQL 或真实只读接口时，页面不需要复制计算逻辑。”

逐项指出：

```text
date              数据日期
campaign_id       计划 ID
campaign_name     计划名称
impressions       展现量
clicks            点击量
cost              消费金额，人民币元
conversions       转化数
```

### 6–8 分钟：本课目标话术

切回看板。

直接讲：

> “今天我们始终沿着同一条请求往下走：筛选组件发事件，App 管页面状态，请求模块拼 URL，FastAPI 路由接收和校验参数，service 读取并计算数据，Pydantic 约束响应结构，最后 Vue 更新卡片和表格。”
>
> “这一小时结束时，代码不是只做到‘能跑’，而是每一层为什么存在、负责什么、出错时从哪里排查，都能说清楚。”

如果开场超时，压缩 JSON 字段介绍，但保留“本课 service 将成为第三课 Agent 工具基础”这条关系。

---

## 8–15 分钟：【必讲】完整演示四种页面状态

### 8–10 分钟：默认结果

操作：刷新 `http://127.0.0.1:5173`。

直接讲：

> “页面首次加载时使用固定日期 2026 年 9 月 1 日到 9 月 7 日。这里没有使用今天的日期，因为本地数据范围是固定的，默认值必须与数据匹配，才能保证首屏有结果。”
>
> “顶部四张卡片对应展现量、点击量、消费金额和转化数；下方表格是一条计划一天的数据。右上角显示二十一条，这与三个计划乘七天一致。”
>
> “页面上的‘本地数据’说明当前数据来自本地报表服务。这个阶段没有连接真实百度推广账户。”

### 10–12 分钟：组合筛选与重置

操作：开始日期设为 `2026-09-02`，结束日期设为 `2026-09-04`，关键词输入“课程”，点击“查询”。

预期：返回 3 条“课程咨询推广”。

打开 Network 中最新的 campaigns 请求。

直接讲：

> “现在三个表单值被转换成 URL 查询参数：`start_date=2026-09-02`、`end_date=2026-09-04`、`keyword=课程`。开始和结束日期都包含当天，所以得到 2、3、4 日三条记录。”
>
> “点击重置以后，组件会恢复默认表单并立即再提交一次查询，因此输入和报表同时恢复，不需要再点击查询。”

操作：点击“重置”，确认恢复 21 条。

### 12–13 分钟：空结果

操作：关键词输入“不存在的计划”，点击查询。

直接讲：

> “这里显示暂无匹配数据，但 Network 中状态仍然是 HTTP 200。空结果表示请求成功、筛选后没有记录，响应是 `items: []` 和 `total: 0`。它不是接口故障。”

### 13–15 分钟：请求失败与重试

操作：先重置；DevTools Network 切换为 Offline；输入“品牌”并查询；恢复 Online；点击“重试”。

直接讲：

> “Offline 时浏览器无法取得 HTTP 响应，页面进入失败状态并显示重试按钮。查询开始时旧结果会被清空，因此不会把上一次报表误认为本次查询结果。”
>
> “恢复网络后点击重试，页面会使用最后一次提交的条件，也就是‘品牌’，所以返回七条品牌词计划数据，而不是默认二十一条。”
>
> “到这里已经看到四种状态：加载中、成功有数据、成功无数据、请求失败。后面看源码时，就围绕这四种状态理解 `loading`、`result` 和 `error`。”

时间不足时不演示慢网加载动画，但保留空结果与失败重试，两者最容易在业务中混淆。

---

## 15–25 分钟：【必讲】目录结构、模块职责和接口契约

### 15–18 分钟：项目目录

在编辑器资源管理器中展示仓库根目录。

直接讲：

> “项目按职责分为四块。`frontend` 是 Vue、TypeScript、Vite 和 Electron 客户端；`backend` 是 FastAPI 服务；`data/mock` 存放当前报表数据；`docs` 存放接口和课程文档。”
>
> “前端和 Electron 不是两套页面。Electron 创建桌面窗口，开发时加载 Vite 地址，构建后加载同一个 `dist` 页面。后端本阶段独立启动，两种客户端都通过 HTTP 访问它。”

模块职责：

```text
frontend/src/components/ReportFilters.vue   收集筛选条件、发出 query 事件
frontend/src/App.vue                        页面级状态和查询流程
frontend/src/api/reports.ts                 HTTP 请求封装
frontend/src/types/reports.ts               前端接口类型
frontend/src/components/MetricCards.vue     汇总指标展示
frontend/src/components/ReportTable.vue     明细表格展示
frontend/src/format.ts                      数字、金额、百分比格式化

backend/app/main.py                         FastAPI 应用初始化和 CORS
backend/app/routes/reports.py               HTTP 路由和查询参数校验
backend/app/models.py                       Pydantic 数据模型
backend/app/services/reports.py             数据读取、筛选、计算和汇总
data/mock/campaigns.json                    原始报表数据
```

### 18–21 分钟：接口契约

打开：`frontend/src/types/reports.ts`，随后打开 Swagger `/docs`。

直接讲：

> “前后端通过接口契约协作。`Filters` 描述三个查询条件；`Metrics` 描述共同指标；`CampaignReport` 在指标上增加日期和计划信息；`ReportResponse` 固定返回 `items`、`summary` 和 `total`。”
>
> “`cost` 是字符串，`cpc` 是字符串或 null；`ctr` 是 number 或 null。金额用字符串传输是为了保留十进制精度；比率分母为零时返回 null，前端显示破折号。”

在 Swagger 执行一次 9 月 2–4 日 + “课程”，展示 Request URL 和响应。再输入倒置日期，展示 422。

继续讲：

> “200 且 items 非空是成功有数据；200 且 items 为空是成功无数据；422 表示请求已经到达后端，但参数不满足契约；网络失败则是没有取得有效 HTTP 响应。”
>
> “Swagger 绕过 Vue 直接调用后端。排错时先在 Swagger 验证接口，可以快速判断问题在页面还是服务。”

### 21–24 分钟：FastAPI 与 Node.js 心智模型

打开：`backend/app/main.py`、`backend/app/routes/reports.py`、`backend/app/models.py`。

直接讲：

> “可以把 `app = FastAPI()` 类比为 `express()` 或 `new Koa()`。`app.include_router(router)` 类似挂载 Router；`APIRouter(prefix='/api/reports')` 提供统一前缀；`@router.get('/campaigns')` 类似 `router.get('/campaigns', handler)`。”
>
> “Python 的 `start_date: str | None` 表示参数可以是字符串或 None，`-> ReportResponse` 表示函数预期返回的类型。不同于普通 TypeScript interface，Pydantic `BaseModel` 会在运行时参与解析、校验和序列化。”
>
> “例如 `CampaignSource` 声明 `date: date` 和 `cost: Decimal`。JSON 中原本是字符串，经过 Pydantic 后会变成真正的 Python date 和 Decimal。`Field(ge=0)` 还会拒绝负数。`response_model=ReportResponse` 会校验响应并生成 OpenAPI 文档。”

### 24–25 分钟：【补充】CORS 与 Electron 安全边界

打开：`backend/app/main.py` 的 `CORSMiddleware` 和 `frontend/electron/main.cjs` 的 `createWindow()`。

直接讲：

> “CORS 只允许明确的本地浏览器来源和 `app://dashboard` 读取响应，没有使用通配来源。Electron 开启 `contextIsolation` 和 sandbox，关闭 `nodeIntegration`，页面不能直接调用 Node 文件或命令能力。”
>
> “这部分今天只记安全边界。自定义协议如何加载 dist、CORS 各响应头如何工作，不影响本课查询主线，放到课后阅读。”

---

## 25–45 分钟：【必讲】沿一次查询追踪全部关键代码

本段始终使用“9 月 2–4 日 + 课程”这次查询。

### 25–28 分钟：筛选组件发出事件

打开：`frontend/src/components/ReportFilters.vue`。

直接讲：

> “`ReportFilters.vue` 只负责输入，不负责请求。`defineProps` 接收父组件传来的默认筛选条件，`reactive({ ...props.defaults })` 创建本地表单状态。”
>
> “`defineEmits` 声明一个名为 query 的事件。`submit()` 执行 `emit('query', { ...form })`，把当前表单复制成普通对象交给父组件。复制的目的，是不把组件内部的响应式对象直接传出去。”
>
> “模板使用 `@submit.prevent`，既能通过按钮或 Enter 提交，又阻止浏览器原生表单刷新。`reset()` 先恢复 defaults，再调用 submit，所以重置会自动查询。”
>
> “这个组件保持单一职责。请求影响汇总卡片、表格、加载和错误多个区域，因此页面级组件统一管理请求状态。”

### 28–32 分钟：App 查询入口和页面状态

打开：`frontend/src/App.vue`，先定位 `<ReportFilters :defaults="defaults" @query="query" />`，再定位 `query(filters)`。

直接讲：

> “子组件发出的 query 事件绑定到 `App.vue` 的 `query()`。App 是这个页面的流程控制层，它不计算报表，但负责一次查询从开始到结束的状态变化。”
>
> “`lastQuery` 保存最后一次提交条件，供失败重试使用；`loading`、`error`、`result` 决定页面当前展示什么；`applied` 保存最近一次成功查询的条件，所以页面标题不会随着尚未提交的输入变化。”
>
> “每次查询先清空 error 和 result，再检查开始日期是否晚于结束日期。合法后把 loading 设为 true，调用 `fetchReports()`；成功写入 result 和 applied，失败写入 error，finally 关闭 loading。15 秒没有完成会主动中断并提示超时。”

【补充】指向以下代码，但不展开执行时序：

> “这里还用 AbortController 取消上一次请求，并用 `requestId` 做第二层保护。即使旧异步流程稍后才进入 catch 或 finally，也不能覆盖新结果或提前关闭新请求的 loading。主线只需记住：连续查询时旧结果不会覆盖新结果。”

### 32–34 分钟：请求封装

打开：`frontend/src/api/reports.ts`。

直接讲：

> “`fetchReports()` 把 Filters 翻译成 HTTP。请求地址来自 `VITE_API_BASE_URL`，未配置时使用 `http://127.0.0.1:8000`，因此环境地址没有散落在组件中。”
>
> “`URLSearchParams` 遍历筛选字段，trim 后为空的值不发送。最后请求 `/api/reports/campaigns`，并把 AbortSignal 交给 fetch。”
>
> “fetch 遇到网络断开会 reject，但收到 HTTP 422 时仍然算取得了响应，所以代码还要检查 `response.ok`。422 尽量显示后端 detail，其他状态显示统一错误。成功后把 JSON 作为 `ReportResponse` 返回。”
>
> “这里的 TypeScript 返回类型帮助开发期检查，但类型断言本身不做运行时校验。真正的运行时响应约束主要由后端 Pydantic 提供。”

### 34–37 分钟：FastAPI 路由和参数校验

打开：`backend/app/main.py`，指向 `app.include_router(router)`；再打开 `backend/app/routes/reports.py`。

直接讲：

> “`main.py` 创建应用、挂载 CORS 并注册 router。具体报表接口放在 routes 中，避免所有 handler 都堆在入口文件。”
>
> “router 的 prefix 是 `/api/reports`，装饰器路径是 `/campaigns`，合起来就是前端请求的 `/api/reports/campaigns`。FastAPI 根据 `campaigns()` 的函数签名，把 query string 注入 `start_date`、`end_date` 和 `keyword`。”
>
> “日期没有直接声明成 date，而是先保留字符串。`parse_date()` 先用正则严格检查 `YYYY-MM-DD` 的外形，再用 `date.fromisoformat()` 检查日期真实性，因此 `2026-9-1` 和 `2026-02-30` 都会被拒绝。”
>
> “`Annotated[str, Query(max_length=100)]` 表示 keyword 仍是字符串，同时附加最大长度约束。两个日期解析成功后再检查开始不能晚于结束。非法时抛 `HTTPException(422)`；合法时才进入 `get_campaign_reports()`。”
>
> “前端虽然也检查倒置日期，但后端不能依赖前端。Swagger、Electron、脚本和未来 Agent 工具都能直接调用接口，所以服务端必须守住最终边界。”

### 37–40 分钟：Pydantic 模型与数据读取

打开：`backend/app/models.py`，再看 `backend/app/services/reports.py` 的 `load_campaigns()`。

直接讲：

> “models 文件描述系统里的四种数据形态。`CampaignSource` 是原始数据；`CampaignReport` 继承原始字段并增加 ctr 和 cpc；`ReportSummary` 是汇总；`ReportResponse` 是接口最外层结构。”
>
> “`load_campaigns()` 打开 `data/mock/campaigns.json`。`DATA_PATH` 从当前源码文件的绝对路径向上定位仓库根目录，因此不依赖终端从哪个目录启动。”
>
> “JSON 读出来的是 Python 字典。`CampaignSource.model_validate(row)` 把字典交给 Pydantic：日期字符串转成 date，金额字符串转成 Decimal，计数字段检查非负。这一步相当于把不可信的外部数据变成 service 可以放心使用的领域对象。”
>
> “列表推导式 `[CampaignSource.model_validate(row) for row in json.load(source)]` 可以按普通循环理解：遍历每条 JSON，校验后放入新列表。”

### 40–43 分钟：筛选、比率和汇总

仍在：`backend/app/services/reports.py`，定位 `ratios()` 和 `get_campaign_reports()`。

直接讲：

> “`get_campaign_reports()` 是本阶段核心业务函数。它不关心 HTTP，也不关心 Vue，只接收已经解析好的日期和关键词，返回 `ReportResponse`。第三课封装 Agent 工具时，可以复用这层，而不需要模拟浏览器请求。”
>
> “关键词先 `strip().casefold()`，去掉两端空白并统一大小写比较。筛选条件用列表推导式组合：开始日期为空就不限下界，否则要求大于等于；结束日期为空就不限上界，否则要求小于等于；名称包含关键词。之后按 date 和 campaign_id 排序。”
>
> “每一行通过 `ratios()` 计算 CTR 和 CPC。CTR 是点击量除以展现量，接口返回小数；CPC 是消费除以点击量，单位是人民币元。分母为零时返回 None，最终 JSON 是 null，页面显示破折号。”
>
> “金额使用 Decimal，不使用 float。二进制浮点无法精确表示很多十进制金额，累加后可能出现尾差。CPC 用 `quantize(Decimal('0.01'), ROUND_HALF_UP)` 按常见四舍五入规则保留两位。”
>
> “汇总指标先分别加总 impressions、clicks、cost、conversions，再用总点击除以总展现计算汇总 CTR，用总消费除以总点击计算汇总 CPC。不能平均每行比率，因为每行分母不同。”

在屏幕旁写：

```text
summary.ctr = sum(clicks) / sum(impressions)
summary.cpc = sum(cost) / sum(clicks)
```

继续讲：

> “最后 `ReportSummary` 形成汇总，`CampaignReport` 列表形成明细，`total=len(items)` 形成记录数，共同构造 `ReportResponse`。service 到这里完成全部业务职责。”

### 43–45 分钟：响应返回与 Vue 展示

依次打开：`frontend/src/App.vue` 模板、`MetricCards.vue`、`ReportTable.vue`、`format.ts`。

直接讲：

> “ReportResponse 经 Pydantic 序列化成 JSON。`fetchReports()` 解析后，`query()` 写入 `result`，Vue 的响应式系统驱动界面更新。”
>
> “模板先判断 loading，再判断 error；有 result 后渲染 MetricCards。`items` 为空显示空状态，否则渲染 ReportTable。成功空数组与请求失败因此有完全不同的界面。”
>
> “MetricCards 只接收 summary，ReportTable 只接收 items。它们都是展示组件，不发请求、不计算业务汇总。`format.ts` 统一处理千分位、金额和百分比。”
>
> “格式化函数使用 `value === null`，不能用 `if (!value)`。数值 0 是合法结果，例如有展现但零点击时 CTR 是 0.00%；null 表示分母为零，无法计算，才显示破折号。”

---

## 45–53 分钟：【必讲】课堂修改——增加汇总点击率卡片

本段由导师先说明，再让学员跟着修改；环境未就绪时由导师演示，学员课后独立复现。

### 45–47 分钟：说明改动

打开：`frontend/src/components/MetricCards.vue`、`frontend/src/format.ts`、`frontend/src/types/reports.ts`。

直接讲：

> “接口的 `summary` 已经包含 `ctr`，TypeScript 的 `Metrics` 也已经声明 `ctr: number | null`，所以增加汇总点击率不需要修改后端，不需要遍历表格，只需要扩展示组件。”
>
> “我们复用 `percent()`。它负责乘以 100、保留两位小数，并把 null 显示为破折号。”

### 47–50 分钟：完成代码

在 `MetricCards.vue` 修改 import：

```ts
import { integer, money, percent } from '../format'
```

在 `<section class="metrics">` 中增加：

```vue
<article class="panel metric">
  <span>汇总点击率</span>
  <strong>{{ percent(summary.ctr) }}</strong>
  <small>点击量 / 展现量</small>
</article>
```

直接讲：

> “数据直接来自 `summary.ctr`。不要写 `summary.ctr || '—'`，因为数值 0 会被当成 false；不要直接拼百分号，因为接口返回 0.0233，页面应展示 2.33%；也不要平均每一行 CTR，汇总口径已经由后端正确计算。”
>
> “第五张卡片会换行，这不影响本次功能验收。布局优化可以课后再做，今天不因为 CSS 打断数据链路。”

### 50–53 分钟：三组验收

操作一：点击重置。

直接讲：

> “原始三个计划默认汇总 CTR 约为 2.33%，它来自 1,131 次点击除以 48,480 次展现。”

操作二：日期设为 `2026-09-02` 至 `2026-09-02`，关键词“新客”。

直接讲：

> “这一天有展现但零点击，CTR 是合法的 0，所以显示 0.00%；CPC 的分母是点击量，因点击为零显示破折号。”

操作三：日期设为 `2026-09-05` 至 `2026-09-05`，关键词“新客”。

直接讲：

> “这一天展现和点击都是零，CTR 和 CPC 的分母都为零，接口返回 null，两项都显示破折号。”

出现偏差时按固定顺序检查：Network 的 `response.summary.ctr` → `MetricCards` 收到的 `summary` → `percent()` → 模板绑定。先确认数据在哪一层出错，再改代码。

---

## 53–60 分钟：【必讲】串联总结、验收和作业

### 53–56 分钟：完整复述请求链路

切回主线文件标签，直接讲：

> “最后把整条请求再串一次。用户提交表单，`ReportFilters.submit()` 发出 query 事件；`App.query()` 管理校验、加载、错误和结果；`fetchReports()` 拼查询参数并发送 GET；FastAPI 的 `campaigns()` 接收参数，`parse_date()` 校验日期；`get_campaign_reports()` 调用 `load_campaigns()` 读取 Pydantic 对象，再筛选、计算和汇总；`ReportResponse` 序列化返回；App 写入 result，卡片和表格随响应式状态更新。”
>
> “这条链路里，组件负责交互和展示，请求模块负责 HTTP，route 负责协议边界，model 负责运行时数据约束，service 负责业务规则，JSON 只是当前数据源。每层职责清楚以后，排错就能沿链路定位，而不是到处改代码。”

### 56–58 分钟：与最终项目衔接

打开：`backend/app/services/reports.py` 的 `get_campaign_reports()`。

直接讲：

> “第三课接入 LangGraph 或 Agent 工具调用时，工具节点需要接收开始日期、结束日期和关键词，再获得结构化报表结果。今天的 `get_campaign_reports()` 已经提供核心能力。工具层只需要负责把模型参数转换成函数参数、处理异常并把结构化结果交回工作流。”
>
> “RAG 负责回答投放知识，报表 service 负责精确数字。知识文档不能替代实时数据，语言模型也不能自己计算一份不存在的投放报表。这个职责边界是整个 AI 项目的可信基础。”

### 58–60 分钟：作业话术

打开：`docs/lesson-1-homework.md`。

直接讲：

> “课后先保留或补全今天的汇总 CTR 卡片，再增加汇总 CPC 卡片。CPC 必须使用 `summary.cpc`，不能平均每行 CPC。”
>
> “然后在生成脚本中增加第四个计划，覆盖同样七天，并同步调整测试。新增计划后默认 CTR 不再固定为 2.33%，必须使用筛选范围总点击除以总展现，并与接口 `summary.ctr` 核对。”
>
> “最后记录一次真实排错过程，包括复现、证据、根因、修复和复测。下一节进入知识库和 RAG 之前，要先确保今天这条 HTTP 和 service 链路能够独立说明、独立运行。”

结束语：

> “第一节课到这里完成。今天建立的是可靠的数据链路；后面的知识库、Agent 工作流和工具调用，都会建立在这条链路上。”

---

## 时间不足时的裁剪顺序

按以下顺序裁剪，保证主线完整：

1. 不展开 Electron 自定义协议和 CORS 响应头，只保留安全结论。
2. 不展开 AbortController 与 `requestId` 的竞态细节，只说明旧结果不会覆盖新结果。
3. Swagger 只执行一次成功请求，422 用口述说明。
4. 课堂修改只完成 import 和卡片模板，三组验收可课后补做。
5. 不压缩 25–45 分钟的完整查询链路，也不省略 53–58 分钟的职责总结和 Agent 衔接。

## 常见演示故障及快速恢复

1. 页面连接失败：先打开 `/docs` 或 `/api/reports/campaigns`；若失败，在 backend 目录重启 Uvicorn，恢复后点“重试”。
2. Offline 后一直失败：Network 切回 Online/No throttling，再点重试。
3. 5173 或 8000 被占用：复用已有本项目服务，停止自己重复启动的终端，不临时换端口。
4. CORS 报错：统一使用 `http://127.0.0.1:5173`，检查 `CORS_ORIGINS` 是否被环境变量覆盖。
5. 默认页面无数据：点击重置，确认日期回到 2026 年 9 月 1–7 日。
6. 倒置日期没有网络请求：这是 `App.query()` 的前端校验；后端 422 使用 Swagger 演示。
7. CTR 的 0 显示成破折号：检查是否错误使用 falsy 判断；应调用 `percent()` 并用 `value === null`。
8. 代码修改未热更新：先看 Vite 编译错误和浏览器控制台，再检查 import 与 Vue 标签闭合。
9. Electron 环境异常：本课立即切回浏览器，桌面环境课后处理，不占主线时间。
