from fastapi import APIRouter, Depends
from app.agent_models import AgentRequest
from app.rag_config import Settings, get_settings
from app.services.agent import run_agent, MAX_STEPS, MAX_TOOLS, TOTAL_TIMEOUT
from app.services.agent_tools import report_scope

router = APIRouter(prefix='/api/agent', tags=['智能分析'])


@router.get('/metadata')
def metadata(settings: Settings = Depends(get_settings)):
    return {'scope': report_scope(settings), 'mode': 'native_tool_calling',
            'limits': {'steps': MAX_STEPS, 'tools': MAX_TOOLS, 'timeout_seconds': TOTAL_TIMEOUT}}


@router.post('/analyze')
async def analyze(request: AgentRequest, settings: Settings = Depends(get_settings)):
    return await run_agent(request, settings)
