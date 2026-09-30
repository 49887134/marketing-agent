# 报表接口契约

本接口返回项目示例报表数据。默认地址 `http://127.0.0.1:8000`；Swagger 页面为 `/docs`。当前版本不接入百度推广 API。

## 计划日报

`GET /api/reports/campaigns`

| 参数 | 类型 | 规则 |
| --- | --- | --- |
| start_date | 可选字符串 | 严格有效的 YYYY-MM-DD，包含当天；省略表示不限下界 |
| end_date | 可选字符串 | 严格有效的 YYYY-MM-DD，包含当天；省略表示不限上界 |
| keyword | 可选字符串 | 最多 100 字符；去除两端空白后匹配计划名称子串，英文不区分大小写；默认为空 |

两个日期均提供时，开始日期不得晚于结束日期。显式传空日期字符串是非法参数；前端清空日期后会省略该参数。无参数时返回全部样本。结果按日期、计划 ID 升序排列，本阶段不分页。

示例请求：`/api/reports/campaigns?start_date=2026-09-01&end_date=2026-09-01&keyword=品牌`

```json
{
  "items": [{
    "date": "2026-09-01",
    "campaign_id": "C001",
    "campaign_name": "品牌词推广",
    "impressions": 1120,
    "clicks": 28,
    "cost": "44.80",
    "conversions": 0,
    "ctr": 0.025,
    "cpc": "1.60"
  }],
  "summary": {
    "impressions": 1120,
    "clicks": 28,
    "cost": "44.80",
    "conversions": 0,
    "ctr": 0.025,
    "cpc": "1.60"
  },
  "total": 1
}
```

| 字段 | JSON 类型 | 含义与单位 |
| --- | --- | --- |
| items | array | 筛选后的全部记录；一条对应一个计划一天 |
| total | integer | 记录数，不是计划数 |
| date | string | 数据所属日期，不携带时区 |
| campaign_id / campaign_name | string | 计划 ID / 计划名称 |
| impressions / clicks / conversions | integer | 展现次数 / 点击次数 / 转化次数，均非负 |
| cost | string | 人民币元，固定两位小数，例如 `"44.80"` |
| ctr | number 或 null | 点击量 / 展现量，小数比率；`0.025` 展示为 `2.50%` |
| cpc | string 或 null | 消费 / 点击量，人民币元，按 ROUND_HALF_UP 四舍五入到两位小数 |
| summary | object | 筛选后全部记录的指标合计；ctr、cpc 用汇总分子和分母重算 |

金额由 PostgreSQL `numeric(14,2)` 读取为 Python Decimal 后计算，Pydantic 将 Decimal 序列化为字符串，避免金额以二进制浮点数累加。前端只将金额转换成数字做展示，不负责业务计算。点击率是近似 JSON 小数，由前端格式化为百分比。任何比率分母为 0 时返回 `null`，页面显示“—”；`0` 仍应展示 `0.00%`，不能误当成 null。

## 空数据与错误

空结果 HTTP 200：

```json
{"items":[],"summary":{"impressions":0,"clicks":0,"cost":"0.00","conversions":0,"ctr":null,"cpc":null},"total":0}
```

非法日期或日期倒置 HTTP 422：

```json
{"detail":"start_date 必须是有效的 YYYY-MM-DD 日期"}
```

```json
{"detail":"开始日期不能晚于结束日期"}
```

关键词超长由 FastAPI/Pydantic 返回 HTTP 422，`detail` 是错误数组（包含 `loc`、`msg`、`type` 等字段），前端同时兼容字符串与数组。后端不可用是网络错误；服务内部错误可能返回 HTTP 500，不伪装成空数据。页面显示错误与重试按钮，超时阈值为 15 秒，重试使用最后提交的筛选条件。

## 示例数据、数据库与跨域

运行时数据位于远程 Supabase 的 `marketing_agent.campaign_daily_reports`，当前为 61 条示例记录，范围 `2026-09-01` 至 `2026-09-21`。`data/seed/campaigns.json` 只用于管理员手动、幂等入库；接口不会在请求时读取 JSON。无参数时返回全部 61 条。筛选 `2026-09-01` 至 `2026-09-07` 时汇总：展现 48480、点击 1131、消费 `"2268.10"`、转化 30、cpc `"2.01"`。

`2026-09-02` 的“新客拓展计划”有展现但零点击：ctr 为 0，cpc 为 null。`2026-09-05` 同计划零展现、零点击：两个比率均为 null。

默认允许来源：`http://127.0.0.1:5173`、`http://localhost:5173`、`http://127.0.0.1:4173`、`http://localhost:4173`、`app://dashboard`。允许 GET、POST，不携带凭证，不允许通配来源或 `null` 来源。`CORS_ORIGINS` 环境变量可覆盖此列表。CORS 是浏览器来源限制，不等于身份认证。

## 知识问答接口

知识库状态、检索及问答接口见 [知识接口契约](knowledge-api.md)。知识问答不替代报表数据查询。
