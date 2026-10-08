# 百度投放数据：独立查询功能

状态：**两个报表已使用本机后端配置完成真实接口联调**（2026-10-01）。浏览器和 Electron 共用此页面。认证状态只表示配置是否存在，当前请求是否成功以实际返回为准。

## 独立范围

“百度投放数据”包含两个页签：新兴趣报表（2521394，interestsName=一级兴趣）、地域报表（2324048，provinceName=省份）。两者固定timeUnit=DAY，其余列为date、userName、impression、click、cost、ctr、cpc、cpm。默认日期2026-05-01至2026-06-07，每页默认200条，可选择20或50。首次进入或切换页签后点击查询，不自动拉取广告数据。

原报表、知识问答、智能分析保持原数据源和行为；没有修改 Agent 的 query_report，没有入库、迁移、广告账户或预算写接口。

## 已确认的官方协议

2026-10-01 读取百度官方公开文档（页面动态加载，已核对其实际文档内容）：

- [新兴趣报告](https://dev2.baidu.com/content?sceneType=0&pageId=103892&nodeId=1062)：报告类型2521394，interestsName=**一级兴趣**，不是推广计划；CTR=点击率、CPC=平均点击价格、CPM=千次展现消费；最大区间731天；文档列出本次固定查询字段与请求地址。
- [地域报告](https://dev2.baidu.com/content?sceneType=0&pageId=103889&nodeId=1059)：报告类型2324048，provinceName=省级；与新兴趣报告使用相同完整调用地址，最大区间731天。
- [进行首个 API 调用](https://dev2.baidu.com/content?sceneType=0&pageId=100140&nodeId=18)：HTTP POST；header/body 是 JSON 内的自定义字段，认证信息放 HTTP 请求体。
- [请求格式](https://dev2.baidu.com/content?sceneType=0&pageId=100141&nodeId=254)：OAuth2.0 的 JSON header 包含 userName、accessToken。
- [返回格式](https://dev2.baidu.com/content?sceneType=0&pageId=100142&nodeId=255)：header.status=0 成功，非零包含部分失败、全部失败或系统错误；检查 failures。
- [信息流报告](https://dev2.baidu.com/content?sceneType=0&pageId=102631&nodeId=694)：startRow/rowCount 分页，响应 rowCount 为当前行数、totalRowCount 为全部符合条件的记录数。

固定调用地址：

```text
POST https://api.baidu.com/json/sms/service/OpenApiReportService/getReportData
Content-Type: application/json
```

外层请求：

```json
{
  "header": {"userName": "<后端配置的被操作账户名>", "accessToken": "<后端配置的应用授权令牌>"},
  "body": {
    "reportType": 2521394,
    "startDate": "2026-05-01",
    "endDate": "2026-06-07",
    "timeUnit": "DAY",
    "columns": ["date", "userName", "interestsName", "impression", "click", "cost", "ctr", "cpc", "cpm"],
    "sorts": [{"column":"date","sortRule":"ASC"},{"column":"interestsName","sortRule":"ASC"}], "filters": [], "startRow": 0, "rowCount": 200, "needSum": false
  }
}
```

不使用 Bearer、不调用网页调试代理、不接收前端传入的令牌或接口地址。响应按用户提供的成功结构提取 body.data 中唯一报告，检查行数、分页边界和字段类型；不接受部分失败数据，不把 body.data 当作明细行。

地域请求将reportType替换为2324048，columns和第二个排序字段替换为provinceName。官方信息流报告文档允许最多两个排序列，且排序列必须属于查询列。单账户按日期+维度升序，真实请求已接受此规则；不承诺上游实时变化时具备数据库快照一致性。

## 后端配置

在已有 `backend/.env` 末尾增加以下键，保留原配置，填好后重启后端。不要把 `.env.example` 覆盖到已有 `.env`。

```dotenv
BAIDU_MARKETING_ACCESS_TOKEN=
BAIDU_MARKETING_USER_NAME=
BAIDU_MARKETING_TIMEOUT_SECONDS=30
BAIDU_MARKETING_AMOUNT_UNIT=unknown
BAIDU_MARKETING_CTR_UNIT=unknown
```

前两个填写真实的应用授权令牌和被操作账户名，与千帆 CHAT/EMBEDDING 完全分开。配置状态接口只返回是否已配置，不返回认证值。报表中展示的“账户”来自百度业务数据行，不由认证配置回填。

**单位与精度**：两个报告的字段文档没有明确金额币种/元分，保持amount=unknown；页面金额只四舍五入展示两位小数，不加人民币符号或擅自换算。后端仍以Decimal解析并返回完整精度字符串。地域CTR已由用户非零样例及真实响应验证为小数，按乘100后两位小数显示；不受旧的新兴趣CTR配置影响。新兴趣真实记录CTR为零，保留原有unknown配置，尚不能仅凭零值确认其尺度。

确认本报告单位后才设置：

- AMOUNT_UNIT：yuan表示原始值为人民币元；fen表示原始值为人民币分，页面除100显示元；unknown不换算单位，仅展示两位小数。
- CTR_UNIT：仅用于新兴趣报告；ratio表示0.01对应1%；percent表示1对应1%；unknown保留原始值。地域固定ratio。

金额配置同时适用于 cost/cpc/cpm，只有确认三者同单位时才更改。不通过CTR是否大于1等数值猜单位。

目前完整地址、认证及真实查询均已验证。仍待确认金额币种/单位，以及新兴趣CTR尺度；这不阻塞查看原始数据。不需要重新填写地域认证配置，直接复用现有配置。

## 启动与查询

没有新增依赖。沿用现有项目工具链，在根目录两个终端分别执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action frontend
```

打开 http://127.0.0.1:5173，进入“百度投放数据”，选择“新兴趣报表”或“地域报表”，保留默认日期，点击“查询百度数据”。地域可点击下一页或末页。Electron沿用已有 `-Action electron`（先停止独立frontend，backend保留）。旧后端没有自动重载时须重启。

分页严格使用startRow=(page-1)*pageSize，总页数=向上取整(totalRowCount/pageSize)。非末页返回不足pageSize时拒绝异常响应，避免静默跳过记录。修改日期、每页条数或切换页签时立即清除旧结果、取消旧请求并重置第一页，之后点击查询；请求序号防止旧响应覆盖。重试沿用失败条件，修改条件后清除该次重试。失败不展示模拟数据，没有全量汇总卡片或各行比率平均。

## 新文件与接口

| 文件 | 职责 |
| --- | --- |
| backend/app/baidu_report_config.py | 独立认证配置、固定官方URL、安全错误 |
| backend/app/baidu_report_models.py | 日期和分页校验、响应行/数量校验 |
| backend/app/services/baidu_reports.py | POST请求封装、超时、HTTP/业务错误、单报告解析 |
| backend/app/routes/baidu_reports.py | GET /api/baidu-reports/status；POST /api/baidu-reports/query |
| frontend/src/components/BaiduReportPanel.vue | 日期、分页、状态、原始值/已确认单位展示 |
| frontend/src/api/baiduReports.ts | 调用自己的FastAPI，不直连百度 |
| frontend/src/types/baiduReports.ts | 页面数据类型 |
| backend/tests/test_baidu_reports.py | HTTP替身测试 |
| frontend/tests/baiduReports.spec.ts | 浏览器/Electron替身交互测试 |
| backend/app/verify_baidu_reports.py | 两种报告真实只读验收，仅保存计数和校验摘要 |

后端查询体为report（只允许interest/region，默认interest）、start_date、end_date、start_row（默认0）、page_size（默认200，最大200）。reportType、columns、排序和外部URL由后端白名单定义。日期最多731天；start_row须为page_size的整数倍。数值0正常显示，空维度/null显示“—”，金额保留原始精度供处理，仅页面显示两位小数。

错误响应只有安全的 code/message。上游错误正文、请求体和认证信息不记日志、不回传；业务失败统一提示在官方调试台核对认证/权限/参数，不擅自猜测未确认的错误码。HTTP 401/403、429、非2xx、超时、无效JSON和结构错误分别处理，不自动重试外部调用。

## 验证边界

本次实际结果：

- 后端pytest：102项通过（包含原有68项与百度功能34项）。
- 百度页面9项通过：7项交互/异常替身（含Electron dev/built），2项真实验收（Chrome两种报告及地域翻页、Electron built地域查询）。真实Chrome还核对了北京单日CTR/CPC显示。
- 原报表、知识问答、Agent页面回归中，9项直接通过；报表空结果断言曾两次在5秒时限内仍处于加载状态，单独将该测试等待时间与同用例其他真实查询统一为15秒后复验。仅调整测试等待时间，不改变页面或服务行为；模型相关异常交互使用替身，没有再次进行真实模型课堂验收。
- TypeScript检查、Vite构建通过。
- 真实新兴趣：默认日期范围返回1条；地域：总数763，共4页，第一页200条、第二页200条、末页163条。仅抽查这些页，未拉取第三页做全量汇总。
- 地域重复第一页内容一致，抽查页之间无重复键；2026-05-23单日30条，2026-05-01单日为空。均为实际响应。
- 北京2026-05-23：实际CTR显示2.42%，消耗13.25，CPC2.21，CPM53.43；后端保留原始精度。
- 上述计数是本次快照，不在页面或服务代码写死。证据：artifacts/baidu-reports-real-verification.json（无令牌、认证账户和明细）。重新验证：在backend执行 `.venv/Scripts/python.exe -m app.verify_baidu_reports`。
- 替身截图 artifacts/baidu-browser-mock.png、baidu-electron-dev-mock.png、baidu-electron-built-mock.png 仅用于UI验收，不是真实投放数据证据。

异常与交互替身覆盖成功、空数据、分页、零值、非法日期、HTTP认证/权限失败、业务失败、超时、错误响应不泄漏、重试及旧请求保护。真实验收与替身测试分别记录。前端真实测试需显式设置进程环境BAIDU_REPORT_LIVE=1；不会把凭据交给前端，仍由后端读取配置。

不实现全量拉取/汇总、图表、AI分析、自动刷新令牌或历史数据同步。
