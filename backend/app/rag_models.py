from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeQuery(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=6, strict=True)

    @field_validator('question')
    @classmethod
    def strip_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('问题不能为空')
        return value.strip()


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str
    section: str
    ordinal: int
    content: str
    content_hash: str
    document_hash: str


class RetrievedChunk(Chunk):
    similarity: float


class KnowledgeStatus(BaseModel):
    ready: bool = False
    code: str
    message: str
    document_count: int = 0
    chunk_count: int = 0
    embedding_model: str | None = None
    dimensions: int | None = None


class RetrievalResponse(BaseModel):
    question: str
    top_k: int
    min_similarity: float
    chunks: list[RetrievedChunk]


class AnswerResponse(RetrievalResponse):
    status: Literal['answered', 'insufficient_evidence']
    answer: str
    citations: list[RetrievedChunk]


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    sufficient: bool
    answer: str = Field(max_length=6000)
    citation_ids: list[str] = Field(max_length=6)
