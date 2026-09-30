"""只读取 backend/.env；进程环境变量优先，不在日志中输出配置。"""
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / '.env', override=False)


class RagError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(repr=False)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', ''))
    embedding_base_url: str = field(default_factory=lambda: os.getenv('EMBEDDING_BASE_URL', '').rstrip('/'))
    embedding_api_key: str = field(default_factory=lambda: os.getenv('EMBEDDING_API_KEY', ''))
    embedding_model: str = field(default_factory=lambda: os.getenv('EMBEDDING_MODEL', ''))
    dimensions: int = field(default_factory=lambda: int(os.getenv('EMBEDDING_DIMENSIONS', '1536')))
    send_dimensions: bool = field(default_factory=lambda: os.getenv('EMBEDDING_SEND_DIMENSIONS', 'false').lower() == 'true')
    chat_base_url: str = field(default_factory=lambda: os.getenv('CHAT_BASE_URL', '').rstrip('/'))
    chat_api_key: str = field(default_factory=lambda: os.getenv('CHAT_API_KEY', ''))
    chat_model: str = field(default_factory=lambda: os.getenv('CHAT_MODEL', ''))
    timeout: float = field(default_factory=lambda: float(os.getenv('MODEL_TIMEOUT_SECONDS', '35')))
    min_similarity: float = field(default_factory=lambda: float(os.getenv('RAG_MIN_SIMILARITY', '0.35')))

    @property
    def signature(self) -> str:
        # 不保存 URL 或密钥；同模型名但不同服务也不能静默混用。
        return hashlib.sha256(f'{self.embedding_base_url}|{self.embedding_model}|{self.dimensions}'.encode()).hexdigest()

    @property
    def embedding_max_bytes(self) -> int | None:
        # embedding-v1: 384 tokens / 1000 字符。采用更保守的 UTF-8 字节预算，
        # 预留特殊 token 空间；不是把字符数或字节数冒充精确 token 数。
        return 360 if self.embedding_model.lower() == 'embedding-v1' else None

    def require_model(self, kind: str) -> None:
        prefix = 'embedding' if kind == 'embedding' else 'chat'
        if not all(getattr(self, f'{prefix}_{key}') for key in ('base_url', 'api_key', 'model')):
            raise RagError('configuration_missing', f'请在后端 .env 配置 {prefix.upper()}_BASE_URL、API_KEY 和 MODEL。')
        url = urlsplit(getattr(self, f'{prefix}_base_url'))
        if url.scheme not in ('http', 'https') or not url.netloc or url.username or url.password or url.query:
            raise RagError('configuration_invalid', '模型 BASE_URL 必须是无账号、无查询参数的 HTTP(S) API 地址。')


def get_settings() -> Settings:
    try:
        settings = Settings()
        if not 1 <= settings.dimensions <= 16000 or not 1 <= settings.timeout <= 60 or not 0 <= settings.min_similarity <= 1:
            raise ValueError
        return settings
    except ValueError:
        raise RagError('configuration_invalid', '请检查维度、超时（1–60秒）和相似度阈值（0–1）配置。') from None
