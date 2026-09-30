import re

from app.rag_config import Settings, RagError
from app.rag_models import KnowledgeQuery, KnowledgeStatus, RetrievalResponse, AnswerResponse
from app.services import knowledge_store as store
from app.services.knowledge_documents import load_chunks, corpus_hash
from app.services.model_client import embed_texts, generate_answer


def exact_query_terms(question: str) -> list[str]:
    terms = []
    for value in re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{6,}', question):
        date_match = re.fullmatch(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', value)
        variants = [value]
        if date_match:
            year, month, day = map(int, date_match.groups())
            variants.extend((f'{year:04}-{month:02}-{day:02}', f'{year}/{month}/{day}',
                             f'{year:04}/{month:02}/{day:02}'))
        for term in variants:
            if term not in terms:
                terms.append(term)
    return terms[:8]


def knowledge_status(settings: Settings) -> KnowledgeStatus:
    try:
        result = store.inspect_database(settings)
        meta = result['metadata']
        base = dict(document_count=result['documents'], chunk_count=result['chunks'],
                    embedding_model=meta['embedding_model'] if meta else None,
                    dimensions=meta['dimensions'] if meta else None)
        try:
            store.ensure_compatible(settings, meta)
            if not result['chunks']:
                raise RagError('knowledge_not_ready', '知识库为空，请联系系统管理员完成入库。', 409)
            settings.require_model('embedding')
            settings.require_model('chat')
        except RagError as error:
            return KnowledgeStatus(code=error.code, message=error.message, **base)
        return KnowledgeStatus(ready=True, code='ready', message='知识库已入库、配置完整；模型连通性以实际问答为准。', **base)
    except RagError as error:
        return KnowledgeStatus(code=error.code, message=error.message)


def ingest_documents(settings: Settings, rebuild: bool = False) -> dict:
    try:
        chunks = load_chunks(embedding_max_bytes=settings.embedding_max_bytes)
    except ValueError as error:
        raise RagError('invalid_documents', f'文档切分失败：{error}。原知识库保持不变。', 400) from None
    if not chunks:
        raise RagError('invalid_documents', '没有有效知识片段，保留远程知识库。', 400)
    fingerprint = corpus_hash(chunks)
    snapshot = store.inspect_database(settings)
    meta = snapshot['metadata']
    if meta and not rebuild:
        store.ensure_compatible(settings, meta)
        if meta['corpus_hash'] == fingerprint and snapshot['chunks'] == len(chunks):
            return {'changed': False, 'documents': snapshot['documents'], 'chunks': len(chunks)}
    vectors = []
    for offset in range(0, len(chunks), 16):
        batch = chunks[offset:offset + 16]
        vectors.extend(embed_texts(settings, [f'{c.title}\n{c.section}\n{c.content}' for c in batch]))
    store.replace_collection(settings, chunks, vectors, fingerprint, rebuild)
    return {'changed': True, 'documents': len({c.document_id for c in chunks}), 'chunks': len(chunks)}


def retrieve(settings: Settings, query: KnowledgeQuery) -> RetrievalResponse:
    snapshot = store.inspect_database(settings)
    store.ensure_compatible(settings, snapshot['metadata'])
    if not snapshot['chunks']:
        raise RagError('knowledge_not_ready', '知识库为空，请联系系统管理员完成入库。', 409)
    vector = embed_texts(settings, [query.question])[0]
    # 向量模型不擅长区分日期和长数字 ID；这些稳定标识使用绑定参数精确优先排序。
    chunks = store.search_chunks(settings, vector, query.top_k, exact_query_terms(query.question))
    return RetrievalResponse(question=query.question, top_k=query.top_k, min_similarity=settings.min_similarity, chunks=chunks)


def answer_question(settings: Settings, query: KnowledgeQuery) -> AnswerResponse:
    retrieval = retrieve(settings, query)
    insufficient = AnswerResponse(**retrieval.model_dump(), status='insufficient_evidence',
        answer='现有资料依据不足，无法回答该问题。请补充相关知识资料；当前账户实时数据需通过报表查询。', citations=[])
    if not retrieval.chunks:
        return insufficient
    result = generate_answer(settings, query.question, retrieval.chunks)
    if not result.sufficient:
        return insufficient
    ids = set(result.citation_ids)
    return AnswerResponse(**retrieval.model_dump(), status='answered', answer=result.answer,
        citations=[chunk for chunk in retrieval.chunks if chunk.chunk_id in ids])
