"""按文档结构切分 Markdown 与通用 CSV；不是按 token 切分。"""
import csv
import hashlib
import io
import re
from pathlib import Path
from app.rag_models import Chunk

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / 'data' / 'knowledge'


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def split_content(body: str, title: str, section: str, size: int, overlap: int,
                  embedding_max_bytes: int | None):
    budget = None if embedding_max_bytes is None else embedding_max_bytes - len(f'{title}\n{section}\n'.encode('utf-8'))
    if budget is not None and budget < 32:
        raise ValueError('文档标题或章节标题太长，无法为正文保留安全的 Embedding 输入空间')
    start = 0
    while start < len(body):
        end = min(start + size, len(body))
        if budget is not None:
            while end > start and len(body[start:end].encode('utf-8')) > budget:
                end -= 1
        if end == start:
            raise ValueError('单个字符超过 Embedding 输入空间')
        yield body[start:end]
        if end == len(body):
            break
        # 短模型窗口最多重叠四分之一，确保推进且不丢弃字符。
        start = end - min(overlap, (end - start) // 4)


def make_chunk(document_id: str, title: str, source: str, section: str, ordinal: int,
               content: str, document_hash: str) -> Chunk:
    return Chunk(
        chunk_id=digest(f'{document_id}|{section}|{ordinal}|{content}')[:24],
        document_id=document_id, title=title, source=source, section=section,
        ordinal=ordinal, content=content, content_hash=digest(content),
        document_hash=document_hash,
    )


def load_markdown(path: Path, size: int, overlap: int,
                  embedding_max_bytes: int | None) -> list[Chunk]:
    text = path.read_text(encoding='utf-8').strip()
    title = text.splitlines()[0].lstrip('# ').strip()
    document_id = f'marketing_knowledge/{path.stem}'
    source = f'data/knowledge/{path.name}'
    document_hash = digest(text)
    parts = re.split(r'^## (.+)$', text, flags=re.MULTILINE)
    chunks = []
    ordinal = 0
    for i in range(1, len(parts), 2):
        section, body = parts[i], parts[i + 1].strip()
        for content in split_content(body, title, section, size, overlap, embedding_max_bytes):
            ordinal += 1
            chunks.append(make_chunk(document_id, title, source, section, ordinal, content, document_hash))
    return chunks


def decode_csv(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f'CSV 编码无法识别：{path.name}')


def load_csv(path: Path, size: int, overlap: int,
             embedding_max_bytes: int | None) -> list[Chunk]:
    text = decode_csv(path).strip()
    table = list(csv.reader(io.StringIO(text)))

    # 导出文件允许在表头前放生成时间、筛选条件和空行。取首个至少两列且
    # 下一条非空记录列数一致的行作为表头，兼容创意、定向、计划等报表。
    header_index = None
    for index, row in enumerate(table):
        names = [value.strip() for value in row if value.strip()]
        if len(names) < 2 or len(names) != len(set(names)):
            continue
        following = next((candidate for candidate in table[index + 1:] if any(value.strip() for value in candidate)), None)
        if following is not None and len(following) == len(row):
            header_index = index
            break
    if header_index is None:
        raise ValueError(f'CSV 未找到有效表头：{path.name}')
    header_cells = [name.strip() for name in table[header_index]]
    selected_columns = [(index, name) for index, name in enumerate(header_cells) if name]
    headers = [name for _, name in selected_columns]

    creative_report = {'日期', '创意ID', '展现', '点击', '消费'}.issubset(headers)
    title = '百度创意投放明细' if creative_report else 'CSV 数据表'
    document_id = f'marketing_knowledge/{path.stem}'
    source = f'data/knowledge/{path.name}'
    document_hash = digest(text)
    chunks = []
    ordinal = 0
    for row_number, values in enumerate(table[header_index + 1:], header_index + 2):
        if not any(value.strip() for value in values):
            continue
        if len(values) != len(header_cells):
            raise ValueError(f'CSV 第 {row_number} 行字段数量不一致：{path.name}')
        record = {name: values[index].strip() for index, name in selected_columns}
        identity = []
        for name in ('日期', '小时', '省', '创意ID', '计划/方案ID', '账户'):
            if record.get(name):
                identity.append(f'{name} {record[name]}')
            if len(identity) == 3:
                break
        section = ' / '.join(identity) if identity else f'第 {row_number} 行'
        body = '；'.join(f'{name}：{record[name]}' for name in headers if record[name] != '')
        for content in split_content(body, title, section, size, overlap, embedding_max_bytes):
            ordinal += 1
            chunks.append(make_chunk(document_id, title, source, section, ordinal, content, document_hash))
    return chunks


def load_chunks(directory: Path = KNOWLEDGE_DIR, size: int = 600, overlap: int = 80,
                embedding_max_bytes: int | None = None) -> list[Chunk]:
    if size <= overlap or overlap < 0:
        raise ValueError('切分长度必须大于重叠长度')
    chunks: list[Chunk] = []
    for path in sorted(directory.glob('*.md')):
        if path.name.lower() == 'readme.md':
            continue
        chunks.extend(load_markdown(path, size, overlap, embedding_max_bytes))
    for path in sorted(directory.glob('*.csv')):
        chunks.extend(load_csv(path, size, overlap, embedding_max_bytes))
    return chunks


def corpus_hash(chunks: list[Chunk]) -> str:
    return digest('\n'.join(chunk.model_dump_json() for chunk in chunks))
