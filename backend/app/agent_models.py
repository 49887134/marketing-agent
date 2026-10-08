from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ReportArgs(StrictModel):
    start_date: date | None = None
    end_date: date | None = None
    keyword: str = Field(default='', max_length=100)
    period: Literal['explicit', 'last_7_days'] = 'explicit'

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def valid_date(cls, value):
        if isinstance(value, str):
            import re
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('日期必须为 YYYY-MM-DD')
        return value

    @model_validator(mode='after')
    def ordered(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('开始日期不能晚于结束日期')
        return self


class SearchArgs(StrictModel):
    question: str = Field(min_length=1, max_length=110)
    top_k: int = Field(default=3, ge=1, le=6, strict=True)

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or len(value.encode('utf-8')) > 360:
            raise ValueError('检索问题为空或超过模型字节上限')
        return value.strip()


class AgentRequest(StrictModel):
    question: str = Field(min_length=1, max_length=1000)
    filters: ReportArgs = Field(default_factory=ReportArgs)

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('问题不能为空')
        return value.strip()


class Decision(StrictModel):
    status: Literal['ready', 'needs_input', 'unsupported']
    message: str = Field(default='', max_length=1200)


class Insight(StrictModel):
    text: str = Field(min_length=1, max_length=800)
    fact_ids: list[str] = Field(default_factory=list, max_length=20)
    citation_ids: list[str] = Field(default_factory=list, max_length=10)


class Analysis(StrictModel):
    interpretation: list[Insight] = Field(default_factory=list, max_length=8)
    rules: list[Insight] = Field(default_factory=list, max_length=8)
    suggestions: list[Insight] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)
