from fastapi import APIRouter, Depends
from app.baidu_report_config import BaiduReportSettings, get_baidu_settings
from app.baidu_report_models import BaiduReportQuery
from app.services.baidu_reports import query_baidu_report

router = APIRouter(prefix='/api/baidu-reports', tags=['百度投放数据'])


@router.get('/status')
def status(settings: BaiduReportSettings = Depends(get_baidu_settings)):
    return {'configured': bool(settings.access_token and settings.user_name), 'source': 'baidu_api',
            'integration_status': 'configured' if settings.access_token and settings.user_name else 'not_configured',
            'units': {'amount': settings.amount_unit, 'ctr': settings.ctr_unit}}


@router.post('/query')
async def query(request: BaiduReportQuery, settings: BaiduReportSettings = Depends(get_baidu_settings)):
    return await query_baidu_report(request, settings)
