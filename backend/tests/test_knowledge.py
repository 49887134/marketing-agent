"""隔离测试：替身数据库/模型，不代表 Supabase 或真实模型已经验证。"""
import json
import math
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.rag_config import Settings, RagError, get_settings
from app.rag_models import RetrievedChunk, KnowledgeQuery
from app.services import knowledge, knowledge_store, model_client
from app.services.knowledge import exact_query_terms
from app.services.knowledge_documents import load_chunks, corpus_hash


@pytest.fixture
def settings():
    return Settings(database_url='', embedding_base_url='https://embedding.invalid/v1',
        embedding_api_key='TEST_ONLY', embedding_model='test-embedding', dimensions=3,
        chat_base_url='https://chat.invalid/v1', chat_api_key='TEST_ONLY', chat_model='test-chat')


@pytest.fixture
def chunk():
    source = next(c for c in load_chunks() if c.section == '汇总 CTR 为什么不能直接平均')
    return RetrievedChunk(**source.model_dump(), similarity=0.87)


@pytest.fixture
def client(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as instance:
        yield instance
    app.dependency_overrides.clear()


def mock_model(monkeypatch, payload):
    monkeypatch.setattr(model_client, 'post_model', lambda *args: payload)


def test_chunks_stable_versioned_and_bounded(tmp_path):
    path = tmp_path / 'case.md'
    path.write_text('# 文档\n\n## 长段\n' + '中文正文。' * 200, encoding='utf-8')
    first = load_chunks(tmp_path)
    assert len(first) > 1 and first == load_chunks(tmp_path)
    assert all(len(c.content) <= 600 for c in first)
    assert first[0].content[-80:] == first[1].content[:80]
    path.write_text('# 文档\n\n## 长段\n修改后的内容', encoding='utf-8')
    updated = load_chunks(tmp_path)
    assert updated[0].document_id == first[0].document_id
    assert updated[0].chunk_id != first[0].chunk_id
    assert corpus_hash(updated) != corpus_hash(first)


def test_actual_corpus():
    chunks = load_chunks()
    files = [path for path in (Path(__file__).resolve().parents[2] / 'data' / 'knowledge').iterdir()
             if path.suffix.lower() in ('.md', '.csv') and path.name.lower() != 'readme.md']
    assert len({c.document_id for c in chunks}) == len(files)
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert any(c.source.endswith('.csv') and '创意ID：' in c.content for c in chunks)


def test_gb18030_csv_with_preamble_is_structured_and_bounded(tmp_path):
    content = ('数据生成时间：2026-09-30\n数据生成条件：\n1. 时间范围：20260501至20260830\n\n'
               '日期,账户,创意ID,标题,展现,点击,消费\n'
               '2026-06-10,测试账户,1422692106788,中文创意标题,444,10,73.98\n')
    (tmp_path / 'creative.csv').write_bytes(content.encode('gb18030'))
    chunks = load_chunks(tmp_path, embedding_max_bytes=360)
    assert chunks and {c.document_id for c in chunks} == {'marketing_knowledge/creative'}
    assert all(len(f'{c.title}\n{c.section}\n{c.content}'.encode('utf-8')) <= 360 for c in chunks)
    merged = ''.join(chunk.content for chunk in chunks)
    for expected in ('日期：2026-06-10', '创意ID：1422692106788', '消费：73.98'):
        assert expected in merged


def test_generic_csv_detects_header_and_uses_row_identity(tmp_path):
    content = ('数据生成时间：2026-09-30\n数据生成条件：\n1. 时间范围：20260501至20260830\n\n'
               '日期,省,展现,直播间观看人数（旧）\n'
               '2026/6/4,北京,43,0\n2026/6/4,上海,53,0\n')
    (tmp_path / 'targeting.csv').write_bytes(content.encode('gb18030'))
    chunks = load_chunks(tmp_path, embedding_max_bytes=360)
    assert len(chunks) == 2
    assert chunks[0].title == 'CSV 数据表'
    assert chunks[0].section == '日期 2026/6/4 / 省 北京'
    assert chunks[0].content == '日期：2026/6/4；省：北京；展现：43；直播间观看人数（旧）：0'


@pytest.mark.parametrize('body', [{'question': ' '}, {'question': 'x' * 1001}, {'question': 'CTR', 'top_k': 0}, {'question': 'CTR', 'top_k': 7}, {'question': 'CTR', 'top_k': 1.5}])
def test_input_validation(client, body):
    assert client.post('/api/knowledge/ask', json=body).status_code == 422


def test_missing_database_is_sanitized(client):
    result = client.get('/api/knowledge/status').json()
    assert result['ready'] is False and result['code'] == 'configuration_missing'
    result = client.post('/api/knowledge/ask', json={'question': 'CTR'})
    assert result.status_code == 503
    assert 'TEST_ONLY' not in result.text


def test_post_preflight(client):
    result = client.options('/api/knowledge/ask', headers={'Origin': 'http://127.0.0.1:5173', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
    assert result.status_code == 200
    assert result.headers['access-control-allow-origin'] == 'http://127.0.0.1:5173'


def test_model_signature_mismatch(settings):
    with pytest.raises(RagError, match='重新构建'):
        knowledge_store.ensure_compatible(settings, {'embedding_signature': 'old', 'dimensions': 3})
    with pytest.raises(RagError, match='尚未入库'):
        knowledge_store.ensure_compatible(settings, None)


@pytest.mark.parametrize('vector', [[1, 2], [0, 0, 0], [1, float('nan'), 0]])
def test_invalid_embedding_rejected(monkeypatch, settings, vector):
    mock_model(monkeypatch, {'data': [{'index': 0, 'embedding': vector}]})
    with pytest.raises(RagError) as exc:
        model_client.embed_texts(settings, ['CTR'])
    assert exc.value.code == 'embedding_mismatch'


def test_embedding_order_and_request(monkeypatch, settings):
    def fake_post(config, kind, path, payload):
        assert kind == 'embedding' and path == '/embeddings'
        assert 'dimensions' not in payload
        return {'data': [{'index': 1, 'embedding': [0, 1, 0]}, {'index': 0, 'embedding': [1, 0, 0]}]}
    monkeypatch.setattr(model_client, 'post_model', fake_post)
    assert model_client.embed_texts(settings, ['a', 'b']) == [[1, 0, 0], [0, 1, 0]]


def prepare_retrieval(monkeypatch, settings, chunks):
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': {'embedding_signature': settings.signature, 'dimensions': 3}, 'chunks': 12, 'documents': 4})
    monkeypatch.setattr(knowledge, 'embed_texts', lambda *_: [[1, 0, 0]])
    monkeypatch.setattr(knowledge.store, 'search_chunks', lambda *args: chunks[:args[2]])


def test_retrieval_forwards_exact_dates_and_ids(monkeypatch, settings):
    metadata = {'embedding_signature': settings.signature, 'dimensions': settings.dimensions}
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': metadata, 'chunks': 1})
    monkeypatch.setattr(knowledge, 'embed_texts', lambda *_: [[1, 0, 0]])
    captured = []
    monkeypatch.setattr(knowledge.store, 'search_chunks', lambda *args: captured.extend(args[3]) or [])
    knowledge.retrieve(settings, KnowledgeQuery(question='查询 2026/6/10 创意 1422692106788，重复日期 2026/6/10'))
    assert captured == ['2026/6/10', '2026-06-10', '2026/06/10', '1422692106788']


def test_exact_query_terms_normalizes_date_separators():
    assert exact_query_terms('2026/6/22 的点击') == ['2026/6/22', '2026-06-22', '2026/06/22']
    assert exact_query_terms('2026-06-22 的点击') == ['2026-06-22', '2026/6/22', '2026/06/22']


def test_answer_citations_are_real_retrieved_chunks(client, monkeypatch, settings, chunk):
    prepare_retrieval(monkeypatch, settings, [chunk])
    mock_model(monkeypatch, {'choices': [{'message': {'content': json.dumps({'sufficient': True, 'answer': '应使用总点击除以总展现。', 'citation_ids': [chunk.chunk_id]})}}]})
    response = client.post('/api/knowledge/ask', json={'question': '汇总 CTR？'})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'answered'
    assert body['citations'][0] == body['chunks'][0]
    assert body['citations'][0]['source'] == 'data/knowledge/03-aggregation.md'


@pytest.mark.parametrize('content', ['not json', '{"sufficient":true,"answer":"编造","citation_ids":["fake"]}', '{"sufficient":true,"answer":"无引用","citation_ids":[]}'])
def test_invalid_model_citations_rejected(monkeypatch, settings, chunk, content):
    mock_model(monkeypatch, {'choices': [{'message': {'content': content}}]})
    with pytest.raises(RagError) as exc:
        model_client.generate_answer(settings, 'CTR', [chunk])
    assert exc.value.code == 'invalid_model_answer'


def test_no_matches_does_not_call_chat(client, monkeypatch, settings):
    prepare_retrieval(monkeypatch, settings, [])
    monkeypatch.setattr(knowledge, 'generate_answer', lambda *_: pytest.fail('不应调用生成模型'))
    body = client.post('/api/knowledge/ask', json={'question': '退款政策'}).json()
    assert body['status'] == 'insufficient_evidence' and body['citations'] == []


def test_related_but_insufficient(client, monkeypatch, settings, chunk):
    prepare_retrieval(monkeypatch, settings, [chunk])
    mock_model(monkeypatch, {'choices': [{'message': {'content': '{"sufficient":false,"answer":"无退款资料","citation_ids":[]}'}}]})
    body = client.post('/api/knowledge/ask', json={'question': '退款政策'}).json()
    assert body['chunks'] and not body['citations'] and body['status'] == 'insufficient_evidence'


def test_empty_knowledge(client, monkeypatch, settings):
    prepare_retrieval(monkeypatch, settings, [])
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': {'embedding_signature': settings.signature, 'dimensions': 3}, 'chunks': 0})
    assert client.post('/api/knowledge/ask', json={'question': 'CTR'}).status_code == 409


@pytest.mark.parametrize('timeout', [False, True])
def test_http_model_failures_sanitized(monkeypatch, settings, timeout):
    original = httpx.Client
    def handler(request):
        if timeout:
            raise httpx.ReadTimeout('SECRET_URL_AND_KEY', request=request)
        return httpx.Response(401, json={'error': 'SECRET_URL_AND_KEY'})
    monkeypatch.setattr(model_client.httpx, 'Client', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(RagError) as exc:
        model_client.post_model(settings, 'chat', '/chat/completions', {})
    assert exc.value.status_code == (504 if timeout else 502)
    assert 'SECRET' not in str(exc.value)


def test_ingest_idempotence_skips_model(monkeypatch, settings):
    chunks = load_chunks()
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': {'embedding_signature': settings.signature, 'dimensions': 3, 'corpus_hash': corpus_hash(chunks)}, 'chunks': len(chunks), 'documents': 4})
    monkeypatch.setattr(knowledge, 'embed_texts', lambda *_: pytest.fail('重复入库不应请求模型'))
    assert knowledge.ingest_documents(settings)['changed'] is False


def test_changed_corpus_embeds_before_replace(monkeypatch, settings):
    expected = len(load_chunks())
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': None, 'chunks': 0, 'documents': 0})
    operations = []
    def embed(_, texts):
        operations.append('embed')
        return [[1, 0, 0] for _ in texts]
    def replace(_, chunks, vectors, fingerprint, rebuild):
        assert len(chunks) == len(vectors) == expected
        operations.append('replace')
    monkeypatch.setattr(knowledge, 'embed_texts', embed)
    monkeypatch.setattr(knowledge.store, 'replace_collection', replace)
    assert knowledge.ingest_documents(settings)['changed'] is True
    assert operations == ['embed'] * math.ceil(expected / 16) + ['replace']


def test_failed_embedding_does_not_write(monkeypatch, settings):
    monkeypatch.setattr(knowledge.store, 'inspect_database', lambda _: {'metadata': None})
    def fail(*_):
        raise RagError('model_unavailable', '失败')
    monkeypatch.setattr(knowledge, 'embed_texts', fail)
    monkeypatch.setattr(knowledge.store, 'replace_collection', lambda *_: pytest.fail('失败后不能写库'))
    with pytest.raises(RagError):
        knowledge.ingest_documents(settings)


def test_context_contains_only_selected_sources(chunk):
    messages = model_client.build_messages('问题', [chunk])
    payload = json.loads(messages[1]['content'])
    assert payload['question'] == '问题'
    assert payload['materials'][0]['id'] == chunk.chunk_id
    assert payload['materials'][0]['content'] == chunk.content


def test_qianfan_chunk_budget_preserves_every_character(tmp_path, settings):
    settings.embedding_model = 'embedding-v1'
    body = ''.join(chr(0x4e00 + i) for i in range(500))
    (tmp_path / 'case.md').write_text('# 指标文档\n\n## 指标定义\n' + body, encoding='utf-8')
    chunks = load_chunks(tmp_path, embedding_max_bytes=settings.embedding_max_bytes)
    assert len(chunks) > 1
    positions = []
    for c in chunks:
        assert len(f'{c.title}\n{c.section}\n{c.content}'.encode('utf-8')) <= 360
        positions.append((body.index(c.content), body.index(c.content) + len(c.content)))
    assert positions[0][0] == 0 and positions[-1][1] == len(body)
    assert all(right[0] <= left[1] and right[1] > left[1] for left, right in zip(positions, positions[1:]))


@pytest.mark.parametrize('texts', [['中' * 121], ['a'] * 17, ['']])
def test_qianfan_limits_reject_before_network(monkeypatch, settings, texts):
    settings.embedding_model = 'embedding-v1'
    monkeypatch.setattr(model_client, 'post_model', lambda *_: pytest.fail('超限输入不能被截断后偷偷发送'))
    with pytest.raises(RagError) as exc:
        model_client.embed_texts(settings, texts)
    assert exc.value.status_code == 422
