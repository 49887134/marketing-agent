from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from app.database import database
from app.models import CampaignReport, CampaignSource, ReportResponse, ReportSummary
from app.rag_config import get_settings

CENT = Decimal('0.01')


def load_campaigns(start_date: date | None, end_date: date | None, keyword: str) -> list[CampaignSource]:
    clauses = []
    parameters = {}
    if start_date is not None:
        clauses.append('report_date >= :start_date')
        parameters['start_date'] = start_date
    if end_date is not None:
        clauses.append('report_date <= :end_date')
        parameters['end_date'] = end_date
    keyword = keyword.strip()
    if keyword:
        clauses.append('strpos(lower(campaign_name), lower(:keyword)) > 0')
        parameters['keyword'] = keyword
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    statement = text(f'''SELECT report_date AS date, campaign_id, campaign_name,
        impressions, clicks, cost, conversions
        FROM marketing_agent.campaign_daily_reports
        {where}
        ORDER BY report_date, campaign_id''')
    with database(get_settings()) as conn:
        rows = conn.execute(statement, parameters).mappings().all()
    return [CampaignSource.model_validate(dict(row)) for row in rows]


def ratios(impressions: int, clicks: int, cost: Decimal) -> dict:
    return {
        'ctr': float(Decimal(clicks) / Decimal(impressions)) if impressions else None,
        'cpc': (cost / Decimal(clicks)).quantize(CENT, rounding=ROUND_HALF_UP) if clicks else None,
    }


def get_campaign_reports(start_date: date | None, end_date: date | None, keyword: str) -> ReportResponse:
    rows = load_campaigns(start_date, end_date, keyword)
    items = [CampaignReport(**row.model_dump(), **ratios(row.impressions, row.clicks, row.cost)) for row in rows]
    impressions = sum(row.impressions for row in rows)
    clicks = sum(row.clicks for row in rows)
    cost = sum((row.cost for row in rows), Decimal('0.00')).quantize(CENT)
    summary = ReportSummary(
        impressions=impressions, clicks=clicks, cost=cost,
        conversions=sum(row.conversions for row in rows),
        **ratios(impressions, clicks, cost),
    )
    return ReportResponse(items=items, summary=summary, total=len(items))
