from fastapi import APIRouter, Depends
from app.rag_config import Settings, get_settings
from app.rag_models import KnowledgeQuery, KnowledgeStatus, RetrievalResponse, AnswerResponse
from app.services.knowledge import knowledge_status, retrieve, answer_question

router = APIRouter(prefix='/api/knowledge', tags=['知识库'])


@router.get('/status', response_model=KnowledgeStatus)
def status(settings: Settings = Depends(get_settings)):
    return knowledge_status(settings)


@router.post('/search', response_model=RetrievalResponse)
def search(query: KnowledgeQuery, settings: Settings = Depends(get_settings)):
    return retrieve(settings, query)


@router.post('/ask', response_model=AnswerResponse)
def ask(query: KnowledgeQuery, settings: Settings = Depends(get_settings)):
    return answer_question(settings, query)
