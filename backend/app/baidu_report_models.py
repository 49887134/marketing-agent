"""独立百度新兴趣报告契约，不复用模拟报表或 Agent。"""
import re
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BaiduReportQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    report: Literal['interest', 'region'] = 'interest'
    start_date: date
    end_date: date
    start_row: int = Field(default=0, ge=0, le=2147483447, strict=True)
    page_size: int = Field(default=200, ge=1, le=200, strict=True)

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def iso_date(cls, value):
        if isinstance(value, str) and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('日期必须为 YYYY-MM-DD')
        return value

    @model_validator(mode='after')
    def range_valid(self):
        if self.start_row % self.page_size:
            raise ValueError('分页偏移必须等于(page-1)*page_size')
        if self.start_date > self.end_date:
            raise ValueError('开始日期不能晚于结束日期')
        if (self.end_date - self.start_date).days + 1 > 731:
            raise ValueError('新兴趣报告单次最多查询731天')
        return self


class BaiduReportRow(BaseModel):
    # 只返回声明的报表字段，忽略上游额外字段。
    date: str | None
    userName: str | None
    interestsName: str | None = None
    provinceName: str | None = None
    impression: int | None = Field(ge=0)
    click: int | None = Field(ge=0)
    cost: Decimal | None = Field(ge=0, allow_inf_nan=False)
    ctr: Decimal | None = Field(ge=0, allow_inf_nan=False)
    cpc: Decimal | None = Field(ge=0, allow_inf_nan=False)
    cpm: Decimal | None = Field(ge=0, allow_inf_nan=False)

    @field_validator('*', mode='before')
    @classmethod
    def empty_and_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError('布尔值不是报表数值')
        return None if value == '' else value


class BaiduReportData(BaseModel):
    rowCount: int = Field(ge=0, strict=True)
    totalRowCount: int = Field(ge=0, strict=True)
    rows: list[BaiduReportRow]

    @model_validator(mode='after')
    def count_valid(self):
        if self.rowCount != len(self.rows) or self.totalRowCount < self.rowCount:
            raise ValueError('记录数与返回行数不一致')
        return self
