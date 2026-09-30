"""所有写操作限定 marketing_agent schema 的项目知识集合；启动只读。"""
import json
from sqlalchemy import text
from app.database import database
from app.rag_config import Settings, RagError
from app.rag_models import Chunk, RetrievedChunk

COLLECTION = 'marketing_knowledge'


def vector_schema(conn) -> str:
    name = conn.execute(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'" )).scalar()
    if not name:
        raise RagError('extension_missing', '数据库未启用 vector；请由系统管理员按运行说明完成初始化。')
    return conn.dialect.identifier_preparer.quote_schema(name)


def metadata(conn) -> dict | None:
    if not conn.execute(text("SELECT to_regclass('marketing_agent.knowledge_index')")).scalar():
        return None
    row = conn.execute(text('SELECT * FROM marketing_agent.knowledge_index WHERE collection=:collection'), {'collection': COLLECTION}).mappings().first()
    return dict(row) if row else None


def ensure_compatible(settings: Settings, meta: dict | None) -> None:
    if meta is None:
        raise RagError('knowledge_not_ready', '知识库尚未入库，请联系系统管理员完成初始化与文档入库。', 409)
    if meta['embedding_signature'] != settings.signature or meta['dimensions'] != settings.dimensions:
        raise RagError('embedding_mismatch', '当前 Embedding 服务、模型或维度与知识库不一致。请恢复匹配配置，或由系统管理员重新构建索引。', 409)


def inspect_database(settings: Settings) -> dict:
    with database(settings) as conn:
        extension = vector_schema(conn)
        backend_tls = conn.execute(text('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()')).scalar()
        client_tls = bool(conn.connection.driver_connection.pgconn.ssl_in_use)
        meta = metadata(conn)
        counts = {'documents': 0, 'chunks': 0}
        if meta:
            counts = dict(conn.execute(text('SELECT count(DISTINCT document_id) AS documents, count(*) AS chunks FROM marketing_agent.knowledge_chunks WHERE collection=:collection'), {'collection': COLLECTION}).mappings().one())
        return {'client_tls': client_tls, 'backend_tls': bool(backend_tls), 'vector_schema': extension, 'metadata': meta, **counts}


def initialize(settings: Settings) -> None:
    # 仅由数据库管理员手动调用；已存在的扩展不移动，缺失时安装在本项目 schema。
    with database(settings) as conn:
        conn.execute(text('CREATE SCHEMA IF NOT EXISTS marketing_agent'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA marketing_agent'))
        schema = vector_schema(conn)
        conn.execute(text('''CREATE TABLE IF NOT EXISTS marketing_agent.knowledge_index (
            collection text PRIMARY KEY, embedding_signature text NOT NULL,
            embedding_model text NOT NULL, dimensions integer NOT NULL,
            corpus_hash text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
        )'''))
        conn.execute(text(f'''CREATE TABLE IF NOT EXISTS marketing_agent.knowledge_chunks (
            collection text NOT NULL REFERENCES marketing_agent.knowledge_index(collection),
            chunk_id text NOT NULL, document_id text NOT NULL, title text NOT NULL,
            source text NOT NULL, section text NOT NULL, ordinal integer NOT NULL,
            content text NOT NULL, content_hash text NOT NULL, document_hash text NOT NULL,
            embedding {schema}.vector NOT NULL, PRIMARY KEY(collection, chunk_id)
        )'''))


def replace_collection(settings: Settings, chunks: list[Chunk], vectors: list[list[float]], fingerprint: str, rebuild: bool) -> None:
    if not chunks or len(chunks) != len(vectors):
        raise RagError('invalid_documents', '没有有效文档或向量数量不一致，保留原知识库。', 400)
    with database(settings) as conn:
        # 串行化本项目手动导入；全部向量已成功生成后才进入原子写事务。
        conn.execute(text('SELECT pg_advisory_xact_lock(791260902)'))
        schema = vector_schema(conn)
        old = metadata(conn)
        if old and not rebuild:
            ensure_compatible(settings, old)
        conn.execute(text('''INSERT INTO marketing_agent.knowledge_index
            (collection, embedding_signature, embedding_model, dimensions, corpus_hash)
            VALUES (:collection, :signature, :model, :dimensions, :hash)
            ON CONFLICT(collection) DO UPDATE SET embedding_signature=excluded.embedding_signature,
            embedding_model=excluded.embedding_model, dimensions=excluded.dimensions,
            corpus_hash=excluded.corpus_hash, updated_at=now()'''), {
            'collection': COLLECTION, 'signature': settings.signature, 'model': settings.embedding_model,
            'dimensions': settings.dimensions, 'hash': fingerprint,
        })
        conn.execute(text('DELETE FROM marketing_agent.knowledge_chunks WHERE collection=:collection'), {'collection': COLLECTION})
        rows = [{**chunk.model_dump(), 'collection': COLLECTION, 'embedding': json.dumps(vector)} for chunk, vector in zip(chunks, vectors, strict=True)]
        conn.execute(text(f'''INSERT INTO marketing_agent.knowledge_chunks
            (collection,chunk_id,document_id,title,source,section,ordinal,content,content_hash,document_hash,embedding)
            VALUES (:collection,:chunk_id,:document_id,:title,:source,:section,:ordinal,:content,:content_hash,:document_hash,CAST(:embedding AS {schema}.vector))'''), rows)


def search_chunks(settings: Settings, vector: list[float], top_k: int,
                  exact_terms: list[str] | None = None) -> list[RetrievedChunk]:
    with database(settings) as conn:
        # 读元数据和向量使用一致快照，避免索引更新时读到混合版本。
        conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'))
        ensure_compatible(settings, metadata(conn))
        schema = vector_schema(conn)
        params = {'embedding': json.dumps(vector), 'collection': COLLECTION, 'top_k': top_k}
        matches = []
        for index, term in enumerate(exact_terms or []):
            name = f'exact_{index}'
            params[name] = f'%{term}%'
            matches.append(f'(CASE WHEN section ILIKE :{name} OR content ILIKE :{name} THEN 1 ELSE 0 END)')
        exact_score = ' + '.join(matches) if matches else '0'
        rows = conn.execute(text(f'''SELECT chunk_id,document_id,title,source,section,ordinal,content,content_hash,document_hash,
            1 - (embedding OPERATOR({schema}.<=>) CAST(:embedding AS {schema}.vector)) AS similarity,
            {exact_score} AS exact_score
            FROM marketing_agent.knowledge_chunks WHERE collection=:collection
            ORDER BY exact_score DESC,
              embedding OPERATOR({schema}.<=>) CAST(:embedding AS {schema}.vector), chunk_id LIMIT :top_k'''), params).mappings().all()
        return [RetrievedChunk(**{k: v for k, v in row.items() if k != 'exact_score'})
                for row in rows if row['exact_score'] > 0 or row['similarity'] >= settings.min_similarity]
