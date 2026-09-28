import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from app.models import ReportResponse
from app.services.reports import get_campaign_reports

router = APIRouter(prefix='/api/reports', tags=['报表'])


def parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f'{field} 必须是有效的 YYYY-MM-DD 日期') from None


@router.get('/campaigns', response_model=ReportResponse)
def campaigns(
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: Annotated[str, Query(max_length=100)] = '',
) -> ReportResponse:
    start = parse_date(start_date, 'start_date')
    end = parse_date(end_date, 'end_date')
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail='开始日期不能晚于结束日期')
    return get_campaign_reports(start, end, keyword)
