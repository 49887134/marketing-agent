# 第二课实际验证记录

更新：2026-09-30。当前记录已替代早期“缺少 .env，真实服务未验证”的结论。以下真实服务检查全部使用本地 backend/.env 配置的千帆和 Supabase，没有 Mock 回退。凭据未打印、未写入文档或学生包。

## 真实服务与模型限制

| 检查 | 实际结果 |
| --- | --- |
| Embedding 最小调用 | embedding-v1 成功返回 1 个 384 维向量；服务报告输入 9 tokens |
| Chat 最小调用 | ernie-4.5-turbo-20260402 成功回复“连接成功” |
| 单条/批量限制核对 | 官方资料说明 embedding-v1 单条最多 384 tokens 且 1000 字符、每批最多 16 条；输出 384 维是另一个独立参数 |
| 兼容修正 | 文档完整输入（含标题、章节及换行）采用 360 UTF-8 字节保守预算；长段完整拆分并保留重叠，不静默截断；超长问题在请求模型前返回 422 |
| 全部片段逐条真实调用 | 17 段全部返回 384 维；最大 178 字符、360 UTF-8 字节；服务报告最大 110 tokens，未超过限制 |
| 实际批量入库 | 16 + 1 两批成功，4 份文档共 17 段 |

限制依据：[百度官方模型调用说明](https://ai.baidu.com/ai-doc/WENXINWORKSHOP/Ultiovtgu)、[官方 RAG 示例](https://qianfan.cloud.baidu.com/qianfandev/topic/271140)。360 字节是本项目采用的保守保护，不是精确 tokenizer；没有把字符或字节等同于 token。服务报告的 token 数已逐段记录，未只看批量总和。

证据：`artifacts/lesson-2-service-probe.json`、`artifacts/lesson-2-embedding-input-audit.json`。后者含每段的片段 ID、字符数、字节数、服务报告 tokens 和实际维度，不保存密钥或完整向量。

## Supabase 初始化与数据范围

初始化前执行只读结构检查：public 中存在 jobs、alembic_version；没有 marketing_agent 项目表，没有 vector 扩展，没有本项目 1536 维列或旧向量数据。

实际执行的 DDL 只有手动 init 所需的 CREATE SCHEMA IF NOT EXISTS、CREATE EXTENSION IF NOT EXISTS、CREATE TABLE IF NOT EXISTS；目标均限定在 marketing_agent。没有 DROP TABLE、TRUNCATE 或针对 public 业务表的写操作。

| 对象 | 结果 |
| --- | --- |
| schema | 新建 marketing_agent |
| vector 扩展 | 0.8.2，安装在 marketing_agent；未写入 public |
| marketing_agent.knowledge_index | 1 行：lesson2 集合，embedding-v1，dimensions=384 |
| marketing_agent.knowledge_chunks | 17 行，4 个不同 document_id，实际向量维度均为 384 |
| embedding 列 | marketing_agent.vector，未固定列维数；集合模型签名和维度校验阻止混用 |
| public.jobs / public.alembic_version | 未修改结构或数据，只查询过表名元数据 |
| 旧 1536 维数据处理 | 未发现，因此未迁移、删表或覆盖旧数据 |

TLS 实际检查：psycopg 客户端连接的 client_tls=true；pg_stat_ssl 的 backend_tls=false。前者确认本机到 Supabase pooler 使用 TLS；后者反映 pooler 到 PostgreSQL 后端，不能宣称整条链路都启用了 TLS。连接仍使用 sslmode=require，不等同于 verify-full 的主机身份校验。

`db-check` 已修正为分别输出 client_tls、backend_tls，避免混淆。数据库证据：`artifacts/lesson-2-database-audit.json`。

第一次入库返回 `changed:true, documents:4, chunks:17`；立即再次执行返回 `changed:false, documents:4, chunks:17`。没有重复插入，也没有再次请求文档 Embedding。状态接口真实返回 ready=true。应用启动仍然不会自动初始化或导入。

## 三组课堂问题：真实结果

使用 `python -m app.verify_knowledge`，整体 passed=true、三个案例均通过；下面摘述实际返回，不是预期答案。

| 问题 | 实际回答与引用 |
| --- | --- |
| 为什么汇总 CTR 不能直接平均各行 CTR？ | 回答直接平均会给小样本不合理的权重，正确方法是总点击/总展现；引用 03-aggregation.md 的两个真实片段 |
| 把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？ | 回答不能这样代表整体表现，应使用总点击/总展现；引用 CTR 定义与汇总计算章节 |
| 百度推广账户退款需要哪些材料、几个工作日到账？ | 检索到了相关候选，但资料不足；status=insufficient_evidence，citations=[]，没有编造材料清单或到账时效 |

第一个问题引用 ID：`f28c6257f3082f47a53f04d6`、`6df00083425a3be2e4d9c836`。
第二个问题引用 ID：`2e6931d86a760e58147af7ec`、`6df00083425a3be2e4d9c836`。
引用对象均与本次检索对象一致；已对照原文核对回答中的总点击/总展现和样本权重表述。该检查不意味着 RAG 完全消除幻觉。

真实 top_k 对比（同一问题、模型、阈值 0.35）：

| top_k | 返回片段 |
| --- | --- |
| 1 | 汇总 CTR 章节后半段，相似度约 0.6330 |
| 3 | 上述片段 0.6330；该章节前半段 0.5988；零展现时的点击率 0.4617 |

数量由 1 增加到 3，不代表三个片段同等必要或答案必然更好。完整响应和比较见 `artifacts/lesson-2-real-verification.json`。

## 浏览器、Electron 与回归

- 真实 Chrome：通过页面执行三个问题、核对引用与原文；再执行 top_k=1/3 的真实检索，返回数量分别为 1/3。
- 真实 Electron 构建版：app://dashboard 加载后使用真实后端问答，引用和原文匹配。
- 以上 UI 没有 Playwright route 替身，也没有拦截返回假数据。证据为 `artifacts/lesson-2-real-ui.json`，截图 `lesson-2-browser-real.png`、`lesson-2-electron-real.png`。
- 本轮真实浏览器打开时也验证了默认报表 21 行。第一课的完整报表回归和前端 typecheck/build 已在前一轮通过，本轮未修改前端源码或报表数据，复用此前结果。
- 本轮新增长度保护与无丢字切分测试，后端 46 passed；1 条既有 Starlette/httpx 弃用警告，非失败。
- 早期 Mock 测试覆盖空库、模型超时/失败、伪造引用、无匹配、加载与重试。本轮没有通过清空共享数据库或关闭付费服务重做破坏性的故障演示；这些故障分支仍标记为隔离测试，不冒充真实服务故障验证。

## 2026-09-30 报表数据库迁移补充

- 新建且仅新建 `marketing_agent.campaign_daily_reports`；表内 61 行、3 个计划，日期范围 2026-09-01 至 2026-09-21，`data_source=lesson1-seed-v1`。
- `report-seed` 首次执行由 0 行写入 61 行，立即再次执行前后均为 61 行，确认主键 upsert 不重复插入。
- 运行时接口已改为参数化 SQL 查询远程表；`data/seed/campaigns.json` 仅作为教师手动入库源。应用启动不会自动建表、清表或导入。
- 真实数据库接口验证：无参数 61 行；默认周 21 行，汇总展现 48,480、点击 1,131、消费 2,268.10、转化 30；日期加“课程”返回 3 行；空结果、422 日期错误和零分母 null 均符合契约。
- 结构核对仍只看到本项目三张表以及既有 `public.jobs`、`public.alembic_version`；本次没有对两个 public 表执行写入或结构变更。
- 后端隔离测试使用 `data/seed` 注入，不依赖远程网络；迁移后完整结果为 46 passed。真实数据库接口另行执行，不能用隔离测试冒充远程验证。
- 前端 typecheck/build 通过；浏览器真实报表、连续请求保护、失败重试、Electron 开发版与构建版以及知识 UI 隔离测试合计 8 passed。远程首次连接存在网络耗时，真实报表断言使用 15 秒测试等待上限，应用请求自身仍维持 15 秒超时。

## 学生包（迁移前历史包）

- 最新 ZIP：`artifacts/marketing-agent-lesson2-student-20260930-102807.zip`。
- SHA-256：`40c9ac057d2775bc47db9c9c543d53ed3b20f28187d443c68a7ae4450f05a438`。
- 明确清单：`scripts/lesson2-package-files.json`，58 个源码/运行资料文件加 MANIFEST.json，共 59 项。
- 已重新打包长度保护、切分、init、TLS 检查等源码修改，以及千帆配置示例和更新后的运行说明；不含真实 .env、密钥、.git、依赖目录或教师话术。
- 打包器已检查所有文件哈希、ZIP 完整性，以及本地真实 API key/完整 DATABASE_URL 未出现在包内容中。
- 先前学生包已在独立解压目录创建 venv、项目 Node 并安装依赖、构建和启动成功。本轮锁文件未变；最新包再核对清单并在该独立目录验证启动，不将本机验证称为学员新机器验证。
- 学员仍需教师单独发送 backend/.env，连接已经入库的远程知识库，不运行 init/ingest。

上述 ZIP 生成于报表数据库迁移之前，不包含本次迁移源码。本轮按教师要求没有生成或覆盖学生包；待全部功能确认后再统一生成。

## 查看与课前操作

在 Supabase 的 Table Editor 切换 schema 为 marketing_agent，查看 knowledge_index 和 knowledge_chunks。可复制的只读 SQL 见 `docs/lesson-2-run.md`“在 Supabase 查看本课数据”。

教师课前运行 db-check 和 verify，再启动后端/前端；无需再次初始化。额度、网络和模型可用性会变化，课堂当天以实际调用为准。学员新机器的环境与真实问答仍需在共享屏幕时验收。

未提交、推送 Git，未修改真实 .env，未开通额外服务或下载大型模型。
