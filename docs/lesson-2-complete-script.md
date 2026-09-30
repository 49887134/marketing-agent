# 第二节课完整授课话术：投放知识库与 RAG 问答（60 分钟）

这份文档供教师共享屏幕时边操作边讲。它基于当前仓库与已完成的真实验证编写，采用千帆 `embedding-v1`、`ernie-4.5-turbo-20260402`、远程 Supabase PostgreSQL/pgvector，以及知识集合 `marketing_knowledge`。

本课不复盘第一节课，不要求学员现场从零开发，不布置课后作业。课堂目标是让学员看懂完整 RAG 数据流，在自己的电脑上运行项目，并能通过引用原文判断答案是否有依据。

## 一、本次项目新增功能是做什么用的

在第一节课的投放报表基础上，本次增加了以下能力：

| 新增功能 | 解决的问题 | 关键位置 |
| --- | --- | --- |
| 投放知识资料 | 给问答提供可核对的业务依据，避免只依赖模型已有知识 | `data/knowledge/*.md` |
| 文档切分 | 把长文档拆成适合向量模型和检索的片段，同时保留标题、章节、来源和哈希 | `load_chunks()` |
| Embedding | 把文档片段和用户问题转换成同维度向量，供语义检索 | `embed_texts()` |
| PostgreSQL + pgvector | 远程保存知识片段和向量，按余弦距离检索相关内容 | `knowledge_index`、`knowledge_chunks`、`search_chunks()` |
| 上下文组织 | 把用户问题和检索片段组成受约束的模型输入 | `build_messages()` |
| 带引用回答 | 返回答案、真实引用片段和候选检索片段，便于核对依据 | `generate_answer()`、`answer_question()` |
| 三个知识接口 | 分别检查知识库状态、仅检索、检索后回答 | `/status`、`/search`、`/ask` |
| Vue 知识问答页面 | 展示知识库状态、回答、引用原文、检索结果和异常状态 | `KnowledgePanel.vue` |
| 报表数据库化 | 第一节课报表从 JSON 运行时读取改为 Supabase 查询，为后续 Agent 报表工具提供统一数据源 | `reports.py`、`campaign_daily_reports` |
| 中性运行包 | 提供不含凭据、依赖目录和教师资料的可运行项目 | `scripts/project.ps1`、发布 ZIP |

可以用这段话概括本次变化：

> “第一节课解决的是结构化报表查询：输入日期和计划名称，后端返回确定的数据。第二节课解决的是非结构化知识问答：输入自然语言问题，系统先找资料，再让模型依据资料回答。两个模块以后会成为 Agent 的两类工具，一个查数据，一个查知识。”

## 二、课前 10 分钟准备（不计入课堂）

### 1. 启动并检查

仓库根目录执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action report-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action db-check
```

预期：报表 61 条、3 个计划；知识库 4 份文档、17 个片段。

终端 A 启动后端：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action backend
```

终端 B 启动前端：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lesson2.ps1 -Action frontend
```

打开：

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8000/docs`
- Chrome DevTools Network，过滤 `knowledge`

不要在共享屏幕中打开 `backend/.env`。

### 2. 提前打开文件

按讲解顺序放到编辑器标签页：

1. `data/knowledge/03-aggregation.md`
2. `backend/app/services/knowledge_documents.py`
3. `backend/app/services/model_client.py`
4. `backend/app/services/knowledge_store.py`
5. `backend/app/services/knowledge.py`
6. `backend/app/routes/knowledge.py`
7. `backend/app/rag_models.py`
8. `frontend/src/api/knowledge.ts`
9. `frontend/src/components/KnowledgePanel.vue`
10. `backend/app/services/reports.py`
11. 发布包中的 `README.md`

### 3. 准备发放文件

项目包：

```text
artifacts/marketing-agent-release-20260930-132401.zip
```

真实 `backend/.env` 单独私聊发送，不放在 ZIP 中。学员只执行发布包中的 `scripts/project.ps1`，不执行知识入库、建表或报表种子写入。

## 三、0–8 分钟：先演示完整效果

### 0–1 分钟：开场

打开浏览器，进入“知识问答”。

直接讲：

> “今天这一小时我们给现有营销工作台增加 RAG 知识问答。RAG 的核心不是让模型记住我们的资料，而是在每次提问时先检索资料，再把相关片段交给模型。”
>
> “我先不讲代码，先演示最终效果。你重点观察三个区域：模型给出的回答、回答实际引用的原文，以及系统检索到的全部候选片段。后面我们再沿着一次请求把代码串起来。”

点击“刷新状态”。

预期看到：

- 知识库已就绪。
- 文档数 4。
- 片段数 17。
- Embedding 模型 `embedding-v1`。
- 向量维度 384。

继续讲：

> “状态接口只检查配置、数据库元数据和片段数量，不调用 Chat 模型。状态就绪说明索引可以使用，但不能保证模型服务此刻一定有额度，所以真正是否连通还要用一次问答验证。”

### 1–4 分钟：有明确依据的问题

输入：

```text
为什么汇总 CTR 不能直接平均各行 CTR？
```

保持 `top_k=3`，点击“提问”。

结果出来后，从上到下展开“引用依据”和“检索片段”。

直接讲：

> “答案说明汇总 CTR 应该用总点击除以总展现，不能直接平均每一行 CTR。页面下面的引用来自 `03-aggregation.md`，原文还给出了 5.5% 与 1.9% 的计算差异。”
>
> “这里要区分两个概念。检索片段是系统找到的候选资料；引用依据是模型生成答案时声明实际使用的候选资料。引用必须是检索结果的子集，模型不能自己编一个文件名。”

指向相似度：

> “相似度只是向量接近程度。本次最高约 0.639，它不是 63.9% 的答案正确率，也不是经过校准的可信度。”

### 4–6 分钟：换一种表达

输入：

```text
把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？
```

点击“提问”。

直接讲：

> “这句话没有照抄文档标题，也没有直接说‘平均 CTR’，但 Embedding 会把语义相近的文本映射到相近向量。当前真实结果仍然检索到了汇总 CTR 章节，并回答不能直接平均。”
>
> “这也是向量检索相比纯关键词匹配的价值。不过语义检索不是永远正确，所以我们始终展示实际检索片段。”

### 6–8 分钟：资料未覆盖的问题

输入：

```text
百度推广账户退款需要哪些材料、几个工作日到账？
```

点击“提问”。

预期：状态为资料依据不足，引用为空，但可以看到候选片段。

直接讲：

> “当前知识资料没有退款所需材料和到账时效。模型可能知道一些通用说法，但本项目不允许用常识补齐未提供的政策，所以返回‘现有资料依据不足’。”
>
> “资料不足是一次成功的业务响应，HTTP 仍然可以是 200。模型超时、数据库不可用、配置缺失才属于服务错误。这两类状态不能混在一起。”

转场：

> “刚才看到的是最终结果。接下来十二分钟先讲清楚四个概念：切分、Embedding、向量检索和上下文组织。”

## 四、8–20 分钟：讲清 RAG 的四个核心概念

### 8–11 分钟：知识文档和切分

打开 `data/knowledge/03-aggregation.md`，然后打开 `backend/app/services/knowledge_documents.py`，定位 `load_chunks()`。

直接讲：

> “知识库的起点就是这些 Markdown 文件。它们不是拿来训练模型，而是作为每次问答时可以检索的外部资料。”
>
> “`load_chunks()` 遍历 `data/knowledge` 中的 Markdown，跳过 README。一级标题作为文档标题，二级标题作为 section。长正文再按窗口拆分，并保留少量重叠。”

指向这些字段：

```text
document_id
chunk_id
title
source
section
ordinal
content_hash
document_hash
```

继续讲：

> “`document_id` 标识一份文档，`chunk_id` 标识一个具体片段。source 保存相对路径，ordinal 保存片段顺序，两个哈希分别追踪片段和整份文档的版本。这些信息让回答可以追溯到真实资料。”
>
> “千帆 embedding-v1 的输入窗口比较短。项目采用 360 个 UTF-8 字节的保守预算，标题和章节名也计算在内。它不是精确 token 数，而是一层发送前保护；代码不会静默截断资料。”

### 11–14 分钟：Embedding

打开 `backend/app/services/model_client.py`，定位 `embed_texts()`。

直接讲：

> “Embedding 可以理解为把一段文字转换成一组数字。语义越接近，向量方向通常越接近。文档入库时计算文档向量，用户提问时计算问题向量，两边必须使用兼容模型和相同维度。”
>
> “当前使用 embedding-v1，实际返回 384 维。代码会检查每批最多 16 条、返回数量、索引顺序、向量维度、有限数值和非零向量。回答模型使用另一个 Chat 接口，因为聊天模型和向量模型是两种职责，不能假设同一个模型同时支持。”

可用前端经验类比：

> “如果把 TypeScript 类型理解成开发期约束，这里的向量检查更像运行时 schema 校验。供应商即使返回 HTTP 200，只要数量或维度不符合预期，我们也拒绝写入数据库。”

### 14–17 分钟：pgvector 检索

打开 `backend/app/services/knowledge_store.py`，定位 `COLLECTION`、`metadata()`、`search_chunks()`。

直接讲：

> “知识数据存放在远程 Supabase 的 `marketing_agent` schema。`knowledge_index` 保存集合级元数据，`knowledge_chunks` 保存正文、来源和向量。当前集合名是 `marketing_knowledge`。”
>
> “`search_chunks()` 把问题向量传给 PostgreSQL，使用 pgvector 的余弦距离运算符排序。先最多取 top_k 条，再过滤低于相似度阈值的结果，所以最终片段数可能小于 top_k。”
>
> “当前只有十七个片段，使用精确搜索更容易验证。数据量很大时才需要评估 HNSW 等近似索引，本节不展开。”

### 17–20 分钟：上下文组织与回答约束

仍在 `model_client.py`，定位 `build_messages()` 和 `generate_answer()`。

直接讲：

> “检索结果不会自动变成答案。`build_messages()` 把用户问题和候选资料组织成 Chat 上下文，每段资料只放 ID、标题、章节和正文。”
>
> “系统提示要求模型只根据资料回答；资料不足时返回 `sufficient=false`；有依据时返回 answer 和 citation_ids。temperature 设置为 0，用来降低随机性，但不保证每次文字完全一致。”
>
> “模型输出也不是直接展示。`generate_answer()` 先用 Pydantic 校验 JSON 结构，再检查每个 citation_id 是否属于本次检索集合。有依据的回答必须有非空答案和至少一个真实引用。校验失败返回错误，不展示不可信的模型结果。”

转场：

> “四个概念现在连起来了：文档切片，文字转向量，数据库找相近片段，再把片段和问题交给 Chat。下面沿代码看两条真实流程。”

## 五、20–35 分钟：沿代码讲入库流程和问答流程

### 20–26 分钟：流程 A，知识文档怎样进入数据库

依次打开：

1. `backend/app/knowledge_cli.py` 的 `main()`。
2. `backend/app/services/knowledge.py` 的 `ingest_documents()`。
3. `backend/app/services/knowledge_documents.py` 的 `load_chunks()`、`corpus_hash()`。
4. `backend/app/services/model_client.py` 的 `embed_texts()`。
5. `backend/app/services/knowledge_store.py` 的 `replace_collection()`。

直接讲：

> “入库不是应用启动时自动执行，而是管理员显式运行命令。这样可以避免每次启动重复调用模型、重复写库，也避免学员连接共享数据库时误改索引。”
>
> “`ingest_documents()` 先切分文档，计算整个语料指纹，再读取数据库中的集合元数据。内容、模型签名、维度和片段数量都没变化时直接返回 `changed=false`，不再请求 Embedding。”
>
> “确实发生变化时，每批最多十六段调用 Embedding。所有向量成功返回之后，才进入 `replace_collection()` 的数据库事务。事务中取得项目导入锁，更新 `knowledge_index`，替换当前集合的片段。如果模型调用失败，事务还没有开始，原知识库不会被清空。”

指向 `WHERE collection=:collection`：

> “所有知识写操作都限制在 `marketing_agent` schema 和 `marketing_knowledge` 集合，不会重置整个 Supabase，也不会修改 public 中的其他项目表。”

不要现场重新入库。可以展示课前结果：4 文档、17 片段。

### 26–35 分钟：流程 B，问题怎样变成带引用的答案

严格按真实请求顺序讲：

#### 第一步：前端输入和状态

打开 `frontend/src/components/KnowledgePanel.vue`，定位：

- `examples`
- `question`
- `topK`
- `refreshStatus()`
- `run()`
- `submit()`
- `searchOnly()`

直接讲：

> “组件维护问题、top_k、知识库状态、加载状态、错误、回答和仅检索结果。点击提问走 `submit()`，点击仅检索走 `searchOnly()`，两者最终都进入 `run()`。”
>
> “开始新请求时会取消旧请求并增加 requestId，防止旧响应晚回来覆盖新结果。状态请求和问答请求分别管理，页面卸载时也会取消。”

#### 第二步：HTTP 请求封装

打开 `frontend/src/api/knowledge.ts`，定位 `request()`、`askKnowledge()`、`searchKnowledge()`。

直接讲：

> “API 地址仍然来自 `VITE_API_BASE_URL`。前端只发送 question 和 top_k，数据库密码与模型密钥从不进入 VITE 环境变量。”
>
> “状态接口使用 GET，检索和问答使用 POST JSON。请求模块统一处理超时、后端 detail 和网络错误，组件不用重复写 fetch 细节。”

#### 第三步：FastAPI 路由和 Pydantic

打开 `backend/app/routes/knowledge.py` 与 `backend/app/rag_models.py` 的 `KnowledgeQuery`。

直接讲：

> “FastAPI 路由可以类比 Express Router。`@router.post('/ask')` 是请求入口，`KnowledgeQuery` 是运行时输入模型。question 去空白后不能为空，最大 1000 字符；top_k 必须是 1 到 6 的严格整数，默认 3。”
>
> “Python 类型注解本身更接近 TypeScript 类型提示，真正的运行时解析和校验由 Pydantic 完成。校验通过以后，路由把工作交给 service，不在路由里堆数据库和模型逻辑。”

#### 第四步：检索 service

打开 `backend/app/services/knowledge.py`，定位 `retrieve()`。

直接讲：

> “`retrieve()` 先检查知识库元数据与当前 Embedding 配置是否兼容，再把问题转成向量，然后调用 `search_chunks()`。这里返回的是结构化 RetrievalResponse，包含问题、top_k、阈值和候选片段。”

#### 第五步：生成与引用

定位 `answer_question()`，再回到 `generate_answer()`。

直接讲：

> “如果没有检索片段，service 直接返回依据不足，不调用 Chat。存在候选片段时才生成回答。如果模型判断资料不足，同样返回统一的不足提示和空引用。”
>
> “如果资料足够，后端根据模型返回的 citation_ids，从本次真实检索片段中重新构造 citations。标题、来源和原文都来自数据库记录，不接受模型自己生成来源。”

#### 第六步：页面更新

回到 `KnowledgePanel.vue` 模板，指出回答、引用和 `<details>` 检索片段区域。

直接讲：

> “最终响应回到 Vue。回答使用普通文本插值，Vue 会转义 HTML；引用单独显示来源和原文；候选片段放在可展开区域。这样用户既看到结论，也能看到系统究竟检索了什么。”

在 Swagger 执行一次 `POST /api/knowledge/ask`，请求体：

```json
{
  "question": "为什么汇总 CTR 不能直接平均各行 CTR？",
  "top_k": 3
}
```

对照响应中的：

```text
status
answer
citations
chunks
```

转场：

> “到这里代码主线已经完整走通。接下来把发布包发给你，在你的电脑上完成同一条真实链路。”

## 六、35–50 分钟：发包并带学员运行

### 35–38 分钟：解压和放置配置

发送：

- `marketing-agent-release-20260930-132401.zip`
- 单独私聊的 `backend/.env`

直接讲：

> “请把 ZIP 解压到一个新目录，不要覆盖昨天的目录，也不要在压缩包预览界面直接运行。建议路径使用英文，例如 `D:\projects\marketing-agent`。”
>
> “用 VS Code 打开内层 `marketing-agent` 目录，确认根目录可以直接看到 backend、frontend、scripts 和 .tools。然后把我单独发给你的 `.env` 放到 backend 目录，注意不要变成 `.env.txt`。”

### 38–44 分钟：检查环境和安装依赖

让学员在项目根目录 PowerShell 执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action check
```

直接讲：

> “check 只检查 Python 3.12、系统 Node、npm 和 backend/.env 是否存在，不会打印密钥，也不会证明远程服务已经连通。”

然后执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action install
```

直接讲：

> “install 会在当前项目创建新的 Python 虚拟环境，按 requirements.lock 安装后端依赖，再在项目目录准备锁定的 Node 和前端依赖。不要复制我电脑上的 `.venv` 或 node_modules，因为里面可能包含绝对路径和平台相关文件。”

如果安装超过 6 分钟，直接转入“故障恢复顺序”，不要继续讲补充原理。

### 44–47 分钟：启动后端和检查远程状态

终端 A 执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action backend
```

打开：

```text
http://127.0.0.1:8000/docs
```

执行 `GET /api/knowledge/status`。

直接讲：

> “后端默认只监听 127.0.0.1。现在这个本地 FastAPI 进程使用 backend/.env 连接远程 Supabase 和千帆，密钥不会发给浏览器。”

预期：ready=true、4 文档、17 片段、384 维。

如果需要进一步检查，可在新终端执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action report-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action db-check
```

### 47–50 分钟：启动前端并完成第一次问答

终端 B 执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/project.ps1 -Action frontend
```

打开 `http://127.0.0.1:5173`，切换“知识问答”，输入第一个问题。

直接讲：

> “现在不是只验收页面能打开。我们必须看到一次真实回答、至少一条引用，以及引用原文与回答内容一致。只有这三项同时出现，才能说明从浏览器、FastAPI、Embedding、pgvector、Chat 到页面的完整链路已经跑通。”

## 七、50–60 分钟：观察检索、调整参数和收尾

### 50–54 分钟：验证改写和资料不足

依次输入：

```text
把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？
```

```text
百度推广账户退款需要哪些材料、几个工作日到账？
```

直接讲：

> “第一个问题验证语义改写后能否找到相同主题；第二个问题验证系统能否拒绝超出资料范围的政策问题。我们不能只测试成功回答，还要验证系统在没有依据时会停下来。”

当前真实结果：

- 改写问题返回 answered，并引用汇总 CTR 章节。
- 退款问题返回 insufficient_evidence，引用为空。

### 54–57 分钟：top_k 参数对比

使用问题：

```text
为什么汇总 CTR 不能直接平均各行 CTR？
```

先把 top_k 改为 1，点击“仅检索”；再改为 3，点击“仅检索”。

直接讲：

> “这次我们只改变一个变量：候选数量上限。top_k=1 时当前真实结果返回汇总 CTR 章节的一段，约 0.639；top_k=3 时增加同章节另一段和零展现 CTR 片段，约 0.639、0.618、0.462。”
>
> “数量增加不代表答案必然更好。新增片段可能补充上下文，也可能引入相邻但不必要的信息。参数调优要结合真实问题集观察检索结果，不能只追求数量或分数。”

### 57–60 分钟：完整总结话术

切回知识问答页面，同时保留一次成功回答和引用。

直接讲：

> “今天新增的是一条完整 RAG 链路。知识资料先经过切分和 Embedding，向量存到 PostgreSQL 的 pgvector。用户提问时，问题也被转换成同维度向量，数据库找出相关片段，后端把问题和片段组织成上下文，再调用 Chat 模型。”
>
> “项目没有把模型回答直接当成可信结果。它会校验输出结构、检查引用 ID，并把真实来源和原文展示给用户。资料未覆盖时返回依据不足，数据库、网络或模型失败时返回独立错误。”
>
> “第一节课的报表现在也已经进入同一个远程数据库。报表模块负责结构化数据，知识模块负责解释性资料。下一阶段如果接入 Agent，可以把报表查询和知识问答注册成两种工具，让 Agent 根据用户问题决定调用哪一个。”
>
> “你今天需要真正理解的不是某个框架 API，而是数据怎么流动：文档到片段，片段到向量，问题到向量，向量到候选资料，候选资料到带引用回答。只要这条链路讲清楚，换模型、换数据库或换前端框架时仍然能继续实现。”

最后确认：

- 学员浏览器能打开报表与知识问答。
- 知识状态为 4 文档、17 片段。
- 至少完成一次真实问答并看到引用原文。
- 资料未覆盖问题返回依据不足。
- 学员没有执行 init、ingest、report-init 或 report-seed。

本节到此结束，不布置课后作业。

## 八、课堂故障恢复话术

### Python 版本不存在

> “这个错误说明 Windows 没找到 Python 3.12，不是项目代码错误。先执行 `py --list` 看已安装版本；缺少 3.12 时先安装并重开 VS Code。”

### 虚拟环境指向其他电脑路径

> “这个 `.venv` 来自其他目录或电脑，里面记录的解释器路径无效。删除当前解压目录的 backend/.venv，再运行 install 重新创建。”

### npm 或项目 Node 安装失败

> “先确认 `node --version` 和 `npm.cmd --version`。网络恢复后重试 install，不删除锁文件，也不使用强制升级命令。”

### configuration_missing

> “后端没有读取到完整配置。检查文件是否位于 backend/.env、是否被保存成 .env.txt，修改后重启后端。不要共享屏幕展示文件内容。”

### database_unavailable

> “先检查 Supabase 项目状态和本机到 5432 的网络，再检查连接串和 SSL。这个错误不代表知识为空，也不要通过重新建表解决连接问题。”

### knowledge_not_ready

> “当前配置对应的知识集合没有完成入库。普通运行环境不要执行写库命令，由项目管理员检查远程集合。”

### embedding_mismatch

> “当前 Embedding 服务、模型或维度与入库时不一致。恢复匹配配置；确实需要换模型时统一重建索引，不能把不同维度静默混用。”

### search 成功但 ask 失败

> “仅检索能返回片段，说明数据库和 Embedding 基本正常。问答失败应继续检查 Chat 模型、额度、超时和 JSON 输出格式。”

### Electron 下载失败

> “本节主线使用浏览器即可完整验证 RAG。先完成浏览器问答，Electron 运行时下载可以在网络恢复后单独处理。”

## 九、常见追问的简短回答

1. **RAG 是否完全消除幻觉？**

   不能。它提供外部依据并缩小回答范围，仍需引用校验、评测和人工核对。

2. **为什么不用关键词搜索？**

   关键词适合精确词匹配；向量检索可以处理换一种表达的语义问题。实际系统也可以组合两者。

3. **为什么 Chat 和 Embedding 分开配置？**

   两者用途和接口不同，回答模型不一定支持向量生成，也可能采用不同计费和输入限制。

4. **为什么不用前端直接调用模型？**

   前端会暴露 API Key，也无法安全访问数据库。模型和数据库凭据只由后端读取。

5. **为什么相似度不是可信度？**

   它只衡量向量距离，没有校准为答案正确概率。

6. **为什么需要 corpus_hash？**

   用于判断文档内容是否改变，避免相同内容重复调用 Embedding 和重复写库。

7. **为什么写库前先完成全部 Embedding？**

   避免模型调用到一半失败时先清掉旧索引，保证旧知识库仍然可用。

8. **后续 Agent 会怎样复用？**

   把报表 service 封装成结构化数据工具，把知识检索或问答封装成知识工具，再由 Agent 根据意图选择调用。

## 十、时间不足时的删减顺序

必须保留：

1. 三类效果中的正常问答和依据不足。
2. 文档 → Embedding → pgvector → Chat → 引用的主线。
3. 学员环境至少完成一次真实问答。

可以删减：

1. 余弦距离数学解释。
2. 文档哈希细节。
3. 数据库事务锁细节。
4. top_k 对比。
5. Electron 现场启动。
6. 常见追问。

如果安装排错占用时间，停止补充讲解，优先保证学员完成后端、前端和一次真实问答，不把未完成的运行验收描述为成功。
