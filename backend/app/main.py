import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.reports import router

app = FastAPI(title='百度营销智能运营 Agent API', version='0.1.0')
origins = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173,app://dashboard')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(',') if origin.strip()],
    allow_credentials=False,
    allow_methods=['GET'],
    allow_headers=['Accept', 'Content-Type'],
)
app.include_router(router)
