import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.reports import router
from app.routes.knowledge import router as knowledge_router
from app.routes.agent import router as agent_router
from app.routes.baidu_reports import router as baidu_reports_router
from app.baidu_report_config import BaiduReportError
from app.rag_config import RagError
from fastapi.responses import JSONResponse

app = FastAPI(title='百度营销智能运营 Agent API', version='0.1.0')
origins = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173,app://dashboard')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(',') if origin.strip()],
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['Accept', 'Content-Type'],
)
app.include_router(router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(baidu_reports_router)


@app.exception_handler(RagError)
@app.exception_handler(BaiduReportError)
async def rag_error_handler(request, error: RagError):
    return JSONResponse(status_code=error.status_code, content={'detail': {'code': error.code, 'message': error.message}})
