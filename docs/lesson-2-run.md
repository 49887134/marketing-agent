# 第二课：运行、配置与知识入库

## 环境与方案

Windows PowerShell；Python 3.12；系统 Node >=20.19 与 npm；项目局部 Node 22.22.0（由 `.tools/package-lock.json` 安装）。后端新增 SQLAlchemy 2.0、psycopg 3、python-dotenv，完整版本见 `backend/requirements.lock`。只安装到 `backend/.venv`。无需本地数据库或 Docker。

数据库使用已授权共用的远程 Supabase session pooler（5432）。SQLAlchemy 的 `postgresql+psycopg://` 与 psycopg 3 匹配，不把这个 URL 直接交给 psycopg 的原始连接函数。使用短连接 `NullPool` 和 `prepare_threshold=None`，避免依赖池化端点的预处理语句状态。参考 [SQLAlchemy psycopg 方言](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)、[Supabase 连接说明](https://supabase.com/docs/guides/database/connecting-to-postgres)。

业务表只在 `marketing_agent` schema，知识集合固定为 `lesson2`。报表使用 `campaign_daily_reports`，知识库使用 `knowledge_index`、`knowledge_chunks`。应用启动、状态、检索和问答均不建表、不入库。教师课前手动操作一次，学员默认使用已有报表和知识索引。

## 配置一次即可

如果 `backend/.env` 已存在，保留并补充缺失项，不用示例覆盖。没有时复制 `backend/.env.example` 为 `backend/.env`，在编辑器中填写。文件由后端按固定路径读取，与终端当前目录无关；进程环境变量优先。修改后重启后端。

| 配置 | 用途 |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://用户:编码后的密码@池化地址:5432/postgres?sslmode=require`。从 Supabase 控制台获取真实值，密码中的 `@`、`:`、`/` 等需 URL 编码。 |
| `EMBEDDING_BASE_URL` | 提供 `/embeddings` 的 OpenAI 兼容 API 前缀，例如供应商给出的 `/v1` 前缀；不要填完整 `/embeddings`。 |
| `EMBEDDING_API_KEY`、`EMBEDDING_MODEL` | 独立的向量服务凭据和模型名。不能假设 Chat 模型支持 Embedding。 |
| `EMBEDDING_DIMENSIONS` | 模型实际输出维度，必须与现有索引一致。当前千帆 embedding-v1 实测为 384，示例配置也是 384。 |
| `EMBEDDING_SEND_DIMENSIONS` | 默认 false，仅校验返回维度；供应商明确支持 dimensions 参数时才改 true。 |
| `CHAT_BASE_URL`、`CHAT_API_KEY`、`CHAT_MODEL` | 提供 `/chat/completions` 的生成服务、凭据与模型。可与 Embedding 来自不同供应商。 |
| `MODEL_TIMEOUT_SECONDS` | 单次模型 HTTP 读写等操作的超时，默认 35，范围 1–60；连接超时 10 秒。不是整条流程的严格总时限。 |
| `RAG_MIN_SIMILARITY` | 余弦相似度最低阈值，默认 0.35，范围 0–1；需结合真实模型和问题评估，不是通用最佳值。 |

模型服务须支持浮点 Embedding、Chat 的 `messages`、`temperature`、`max_tokens`，并能遵循 JSON 回答指令。程序通过 httpx 请求，不强绑某个 SDK。未实现自动选择模型或兼容所有供应商参数；先用实际配置执行 verify。API key、连接串不进入前端，前端只有 `VITE_API_BASE_URL`。

数据库连接缺省使用 `sslmode=require` 强制 TLS；拒绝 disable/prefer。`require` 保证加密，但不等同于校验服务端主机身份。若使用 Supabase 证书，可配置 `sslmode=verify-full` 与 `DATABASE_SSLROOTCERT` 证书路径；发给学员时也需提供相应 CA 文件并调整路径。`db-check` 分别返回 psycopg 实际客户端连接的 `client_tls` 和 `pg_stat_ssl` 的 `backend_tls`。本次实测前者 true、后者 false：客户端到 pooler 使用 TLS，但不能据此声称 pooler 到数据库的链路也使用 TLS。

## 教师课前最短顺序

以下都从项目根目录执行，无需激活虚拟环境；在 PowerShell 中运行。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action install
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action db-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action init
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action ingest
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action ingest
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action verify
```

报表表首次初始化和种子数据写入也只由教师执行。`report-seed` 使用 `(report_date, campaign_id)` 主键 upsert，可重复执行且不增加重复记录；不会删除其他来源的数据：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action report-init
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action report-seed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action report-check
```

预期：db-check 返回两段 TLS 状态、扩展位置和计数；init 创建缺失的本项目 schema、vector 扩展及表，不移动已存在的扩展；当前千帆配置首次 ingest 返回 `changed:true, documents:4, chunks:17`，再次相同内容返回 `changed:false`，不重复请求 Embedding。verify 调用真实服务验证三个问题与 top_k 对比，写入 `artifacts/lesson-2-real-verification.json`。没有 Mock 回退；配置缺失时明确失败。检查记录中的答案和原文，自动通过也不能代替语义核对。

当前数据库已由教师完成初始化和入库。新环境若 db-check 提示扩展缺失，执行手动 init；若权限不足才由管理员按下一节最小 SQL 处理。**老师已经入库后，学员不执行 init/ingest/report-init/report-seed**；学员路径见学生 README。

启动后端与前端，各占一个终端：

```powershell
# 终端 A，项目根目录
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action backend
```

```powershell
# 终端 B，项目根目录
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action frontend
```

页面 `http://127.0.0.1:5173`，Swagger `http://127.0.0.1:8000/docs`。后端仅监听 127.0.0.1，学员在自己电脑启动自己的后端，共用远程数据库及约定的模型服务。

Electron 复用页面。浏览器 Vite 已运行时，在 frontend 目录执行 `..\scripts\npm-local.cmd exec -- electron . --dev`。独立 Electron 开发运行则从根目录执行 `-Action electron`，不与另一份 Vite 同时启动。构建仍在 frontend 执行 `..\scripts\npm-local.cmd run build`；构建后 `run electron:start` 使用 `app://dashboard`。

## 扩展与权限不足时的最小 SQL

由教师在 Supabase SQL Editor 执行。先只读确认扩展：

```sql
SELECT e.extname, n.nspname AS extension_schema
FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
WHERE e.extname='vector';
```

没有 vector 时，在本项目 schema 启用；已在其他 schema 启用时不用移动它。本次已实际创建在 marketing_agent：

```sql
CREATE SCHEMA IF NOT EXISTS marketing_agent;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA marketing_agent;
```

如果连接角色不能创建 schema，让管理员创建上述项目 schema 后授权。下例 `your_connection_role` 须替换为真实数据库角色，通常与池化用户名的项目后缀不同；可在 SQL Editor 执行 `SELECT current_user` 核对。只授予本项目所需权限，不使用 `GRANT ALL ON DATABASE`。

```sql
GRANT USAGE, CREATE ON SCHEMA marketing_agent TO your_connection_role;
-- vector 若已在其他 schema，则额外授予该 schema 的 USAGE；本项目新装位于 marketing_agent。
-- 项目表已由另一个角色建立时才需要执行以下两句：
GRANT SELECT, INSERT, UPDATE ON marketing_agent.knowledge_index TO your_connection_role;
GRANT SELECT, INSERT, DELETE ON marketing_agent.knowledge_chunks TO your_connection_role;
```

随后运行 init/ingest。表不存在时先运行 init，不要提前执行针对不存在表的 GRANT。管理员与应用使用同一 postgres 角色通常不需要额外授权。没有创建/重置其他业务表或重置整个数据库的 SQL。

## 入库行为与更新范围

`load_chunks` 读取 `data/knowledge/*.md`（排除 README），按二级标题切分，基础上限为 600 字符窗口、80 字符重叠。使用 embedding-v1 时，进一步将标题、章节、换行和正文的完整输入限制在 **360 UTF-8 字节**内；短窗口重叠不超过窗口的四分之一，连续窗口覆盖所有正文，不丢弃尾部。四份初始资料在当前配置得到 **17 段**。原文、相对来源、文档/片段哈希、片段顺序均保存。

千帆 Embedding-V1 的公开限制为单条不超过 **384 tokens 且 1000 字符**、每批最多 **16 条**，见[百度官方模型调用说明](https://ai.baidu.com/ai-doc/WENXINWORKSHOP/Ultiovtgu)及[官方 RAG 示例](https://qianfan.cloud.baidu.com/qianfandev/topic/271140)。向量输出 384 维和输入上限 384 tokens 是两件事。当前没有引入供应商精确 tokenizer，使用更保守的字节预算预留空间，不把字符/字节等同于 token；超限问题在发请求前明确拒绝。此次逐一调用实际模型核对了全部 17 段：最大 178 字符、360 UTF-8 字节、服务报告最大 110 tokens，均返回 384 维；实际入库批次为 16+1，成功。其他模型仍需按其限制配置与验证。

`knowledge_index` 保存 lesson2 集合的内容指纹、Embedding 模型、维度以及服务前缀/模型/维度组合的哈希签名。签名不含密钥。同名模型换了服务也会要求重新入库；同一服务悄悄更换模型权重无法由名称检测，需人工统一重建。

`ingest_documents` 内容和配置未变化时跳过。内容改变时先在数据库事务外生成全部向量，成功后才进入一个事务，获得项目导入锁，更新 lesson2 元信息并替换 lesson2 片段；事务失败会回滚。删除本地资料后再手动入库，将移除该资料在 lesson2 集合的旧片段。目录为空则拒绝操作，保留远程内容。不会清理其他 collection 或其他 schema。

切换 Embedding 服务、模型、维度时，教师确认后显式运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action ingest -Rebuild
```

该命令只替换本项目 lesson2 集合；学员须同步模型配置。数据规模很小，使用 pgvector 精确余弦距离排序，无需 HNSW 索引。`similarity = 1 - cosine_distance`；先取 top_k，再保留达到阈值的结果，实际返回数可能小于 top_k。[pgvector 官方说明](https://github.com/pgvector/pgvector)说明了精确搜索与距离运算符。

共享数据库已获授权。资料正文和向量在远程数据库；文档/问题会发送给 Embedding 服务，问题与候选片段会发送给 Chat 服务。不是数据完全留在本机的方案。

## 在 Supabase 查看本课数据

进入对应 Supabase 项目，在 **Table Editor** 的 schema 选择处切换为 **marketing_agent**，可看到 `campaign_daily_reports`、`knowledge_index` 与 `knowledge_chunks`；没有立即出现时刷新页面。也可在 **SQL Editor** 执行以下只读语句，不需要改动 API 暴露 schema 配置：

```sql
SELECT 'campaign_daily_reports' AS table_name, count(*) AS rows
FROM marketing_agent.campaign_daily_reports
UNION ALL
SELECT 'knowledge_index', count(*)
FROM marketing_agent.knowledge_index
UNION ALL
SELECT 'knowledge_chunks', count(*) FROM marketing_agent.knowledge_chunks;

SELECT min(report_date) AS start_date, max(report_date) AS end_date,
       count(DISTINCT campaign_id) AS campaigns, count(*) AS rows
FROM marketing_agent.campaign_daily_reports;

SELECT collection, embedding_model, dimensions, updated_at
FROM marketing_agent.knowledge_index;

SELECT document_id, title, count(*) AS chunks
FROM marketing_agent.knowledge_chunks
WHERE collection = 'lesson2'
GROUP BY document_id, title ORDER BY document_id;

SELECT chunk_id, title, section, content, source,
       marketing_agent.vector_dims(embedding) AS dimensions
FROM marketing_agent.knowledge_chunks
WHERE collection = 'lesson2' ORDER BY document_id, ordinal;
```

本次初始化结果：schema `marketing_agent`；`campaign_daily_reports` **61 行**，`knowledge_index` **1 行**，`knowledge_chunks` **17 行**，对应 **4 份知识文档**；vector 扩展 0.8.2 安装于同一 schema，所有片段实际 384 维。embedding 列为未固定维数的 vector 类型，兼容性由集合元信息与请求校验约束。初始化前没有本项目 1536 维列，所以未进行向量迁移、删表或覆盖旧数据。没有对 public.jobs、public.alembic_version 发出写入或结构变更。

## 排错与验证边界

先看 `/api/knowledge/status` 的 code，再看 `/search`，最后看 `/ask`。仅检索成功但回答失败通常指向 Chat 服务或 JSON/引用输出；检索失败通常指向数据库、Embedding 或维度。不要将真实 `.env`、连接串或第三方完整错误响应贴到公开日志。

`ready=true` 代表索引存在、配置一致且必填模型配置齐全，不会在状态请求中扣模型额度测试连通性。只有真实 ask/verify 成功才证明这次模型调用可用。

后端测试：在 backend 执行 `.\.venv\Scripts\python.exe -m pytest -q`。前端构建：在 frontend 执行 `..\scripts\npm-local.cmd run build`。UI 自动测试需要本机 Chrome 和 Electron 运行时；`run test:ui` 中知识问答响应使用替身，报表页面通过本地 FastAPI 访问远程 Supabase。
