import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.models import CampaignReport, CampaignSource, ReportResponse, ReportSummary

DATA_PATH = Path(__file__).resolve().parents[3] / 'data' / 'mock' / 'campaigns.json'
CENT = Decimal('0.01')


def load_campaigns() -> list[CampaignSource]:
    with DATA_PATH.open(encoding='utf-8') as source:
        return [CampaignSource.model_validate(row) for row in json.load(source)]


def ratios(impressions: int, clicks: int, cost: Decimal) -> dict:
    return {
        'ctr': float(Decimal(clicks) / Decimal(impressions)) if impressions else None,
        'cpc': (cost / Decimal(clicks)).quantize(CENT, rounding=ROUND_HALF_UP) if clicks else None,
    }


def get_campaign_reports(start_date: date | None, end_date: date | None, keyword: str) -> ReportResponse:
    keyword = keyword.strip().casefold()
    rows = [row for row in load_campaigns()
            if (start_date is None or row.date >= start_date)
            and (end_date is None or row.date <= end_date)
            and keyword in row.campaign_name.casefold()]
    rows.sort(key=lambda row: (row.date, row.campaign_id))
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
