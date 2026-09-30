# 知识库接口契约

后端地址默认 `http://127.0.0.1:8000`；Swagger `/docs`。所有来源标题、相对路径、原文来自实际入库片段，不由模型生成。服务配置缺失或调用失败时会返回明确错误。

## GET /api/knowledge/status

读取远程索引和模型配置是否完整，不调用模型。示例结构（不是本机真实远程验证记录）：

```json
{
  "ready": true,
  "code": "ready",
  "message": "知识库已入库、配置完整；模型连通性以实际问答为准。",
  "document_count": 4,
  "chunk_count": 17,
  "embedding_model": "embedding-v1",
  "dimensions": 384
}
```

配置缺失、数据库不可用、扩展缺失、空知识库或索引不兼容时通常返回 HTTP 200，`ready=false`，`code/message` 说明原因。非数字或越界环境配置无法创建 Settings 时为 503。不要仅凭 HTTP 200 判断知识库就绪。

## POST /api/knowledge/search 与 POST /api/knowledge/ask

Content-Type 为 `application/json`。两个接口共用输入：

```json
{"question":"为什么汇总 CTR 不能直接平均各行 CTR？","top_k":3}
```

`question` 必填，长度 1–1000，去首尾空白后不能为空；`top_k` 可省略，默认 3，严格整数 1–6。非法输入返回 422，使用 FastAPI 标准 `detail` 校验列表。

使用 `embedding-v1` 时另有模型输入保护：问题最多 360 个 UTF-8 字节；超出返回 422 `embedding_input_too_long` 及说明，不截断问题。上面的 1000 字符是通用接口上限，不能替代实际模型限制。文档按含标题的相同字节预算切分，每批不超过 16 条。

`search`：校验远程索引 → 问题 Embedding → pgvector 余弦检索。不调用回答模型。

```text
question: 本次问题
top_k: 请求的候选数量上限
min_similarity: 当前最低相似度阈值
chunks: 达到阈值的候选片段数组（可为空）
```

每个片段包含：

| 字段 | 含义 |
| --- | --- |
| `chunk_id` | 文档、章节、顺序、正文组成的稳定哈希前缀；内容变化时会改变 |
| `document_id` | 如 `marketing_knowledge/03-aggregation` |
| `title`、`section` | 文档标题、章节标题 |
| `source` | 如 `data/knowledge/03-aggregation.md`，不是外部 URL，也不是服务器绝对路径 |
| `ordinal` | 文档内片段顺序，从 1 开始 |
| `content` | 完整片段原文 |
| `content_hash`、`document_hash` | 原文 SHA-256，用于核对版本 |
| `similarity` | `1 - cosine_distance`，数值越大表示向量越接近，不是可信度或正确率百分比 |

`ask`：执行同一检索流程，将候选片段 ID、标题、章节、正文和问题组成上下文，再调用 Chat。响应包含 search 的全部字段，额外增加：

| 字段 | 含义 |
| --- | --- |
| `status` | `answered` 或 `insufficient_evidence` |
| `answer` | 中文纯文本回答；前端通过 Vue 插值转义显示，不执行 HTML |
| `citations` | 回答引用的片段子集，结构与 chunks 完全一致 |

模型必须返回内部结构 `sufficient`、`answer`、`citation_ids`。后端用 Pydantic 校验结构，并验证所有引用 ID 属于本次检索。`sufficient=true` 时必须有非空回答和引用。伪造 ID、无引用或无效 JSON 返回 502，不展示该回答。校验并不证明每句话都被原文支持，仍需核对。

无匹配资料时不调用 Chat；有相关资料但模型判断不足时，返回 `insufficient_evidence`、统一的依据不足提示、空 `citations`。`chunks` 保留本次候选，便于说明“相关”不等于“足以回答”。这两种情况是 HTTP 200，不是网络错误。

## 错误

可控的服务错误统一为：

```json
{"detail":{"code":"model_unavailable","message":"chat 模型调用失败，请检查后端配置、额度和网络。"}}
```

| HTTP | code 示例 | 处理 |
| --- | --- | --- |
| 409 | `knowledge_not_ready`、`database_not_initialized` | 联系系统管理员检查初始化与入库状态 |
| 409 | `embedding_mismatch` | 索引服务、模型或维度不一致，恢复配置或重建索引 |
| 422 | 标准校验列表 | 检查 question、top_k |
| 422 | `embedding_input_too_long`、`embedding_input_invalid` | 缩短问题或调整文档切分；没有截断后偷偷调用模型 |
| 502 | `model_unavailable`、`invalid_model_answer` | 模型调用或输出校验失败，可重试 |
| 502 | `embedding_mismatch` | 服务返回无效维度、数量、零向量或非有限数值 |
| 503 | `configuration_missing`、`configuration_invalid` | 检查后端 .env |
| 503 | `database_unavailable`、`database_permission_denied`、`extension_missing` | 检查网络、SSL、权限、扩展 |
| 504 | `model_timeout` | 模型超时，稍后重试 |

不会把数据库原始异常、完整连接串、供应商响应体或密钥放入上述错误。后端模型调用不是流式输出；前端总等待上限为 150 秒，状态检查等待上限 30 秒。数据库连接超时 8 秒，SQL statement timeout 10 秒，锁等待 5 秒。前端取消请求不保证远端模型停止处理或计费。

报表接口继续保留，详见 [报表接口契约](api-contract.md)。知识问答只解释知识，不调用报表 service 获取账户实时数据。
