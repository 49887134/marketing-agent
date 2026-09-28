"""接口金额使用十进制字符串；比率使用 JSON 数字或 null。"""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class CampaignSource(BaseModel):
    date: date
    campaign_id: str
    campaign_name: str
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    cost: Decimal = Field(ge=0, decimal_places=2)
    conversions: int = Field(ge=0)


class CampaignReport(CampaignSource):
    ctr: float | None
    cpc: Decimal | None


class ReportSummary(BaseModel):
    impressions: int
    clicks: int
    cost: Decimal
    conversions: int
    ctr: float | None
    cpc: Decimal | None


class ReportResponse(BaseModel):
    items: list[CampaignReport]
    summary: ReportSummary
    total: int
