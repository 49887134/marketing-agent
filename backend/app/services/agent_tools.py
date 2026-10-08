"""两个只读工具：金额与比率由后端计算；工具内不调用 Chat。"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import text
from app.agent_models import ReportArgs, SearchArgs
from app.database import database
from app.rag_config import Settings, RagError
from app.rag_models import KnowledgeQuery
from app.services.reports import get_campaign_reports, ratios
from app.services.knowledge import retrieve


def today() -> date:
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()


def report_scope(settings: Settings) -> dict:
    with database(settings) as conn:
        row = conn.execute(text('''SELECT min(report_date) AS start_date,
            max(report_date) AS end_date, count(*) AS rows,
            bool_and(data_source = 'sample-v1') AS simulated
            FROM marketing_agent.campaign_daily_reports''')).mappings().one()
    return {key: value.isoformat() if isinstance(value, date) else value for key, value in row.items()}


def query_report(args: ReportArgs, scope: dict) -> dict:
    if args.period == 'last_7_days':
        end = today()
        start = end - timedelta(days=6)
    else:
        start, end = args.start_date, args.end_date
    if not start or not end:
        raise RagError('missing_dates', '请补充开始和结束日期，或选择页面演示范围。', 422)
    if (end - start).days > 366:
        raise RagError('date_range_too_large', '单次查询最多覆盖 367 天。', 422)
    if not scope['start_date'] or start.isoformat() < scope['start_date'] or end.isoformat() > scope['end_date']:
        raise RagError('outside_demo_range', f'请求范围 {start} 至 {end} 不在模拟数据覆盖范围 {scope["start_date"]} 至 {scope["end_date"]} 内；未替换日期，请选择演示范围。', 422)
    report = get_campaign_reports(start, end, args.keyword)
    groups = defaultdict(list)
    for row in report.items:
        groups[row.campaign_id].append(row)
    facts = []
    for campaign_id, rows in groups.items():
        impressions = sum(row.impressions for row in rows)
        clicks = sum(row.clicks for row in rows)
        cost = sum((row.cost for row in rows), Decimal('0.00'))
        conversions = sum(row.conversions for row in rows)
        metrics = ratios(impressions, clicks, cost)
        facts.append({'fact_id': f'campaign:{campaign_id}:{start}:{end}', 'campaign_id': campaign_id,
            'campaign_name': rows[-1].campaign_name, 'impressions': impressions, 'clicks': clicks,
            'cost': str(cost), 'conversions': conversions, 'ctr': metrics['ctr'],
            'cpc': str(metrics['cpc']) if metrics['cpc'] is not None else None})
    return {'filters': {'start_date': str(start), 'end_date': str(end), 'keyword': args.keyword},
            'simulated': scope['simulated'], 'total': report.total, 'summary': report.summary.model_dump(mode='json'),
            'facts': facts, 'items': [row.model_dump(mode='json') for row in report.items],
            'missing_metrics': ['收入', '毛利', '完整成本', '转化价值'],
            'notice': '有转化量，但没有收入与利润，不能计算盈利排名或确定预算调整金额。'}


def search_knowledge(args: SearchArgs, settings: Settings) -> dict:
    return retrieve(settings, KnowledgeQuery(**args.model_dump())).model_dump(mode='json')


TOOL_SCHEMAS = [
    {'type': 'function', 'function': {'name': 'query_report',
        'description': '只读查询模拟报表与各计划汇总。支持日期、计划名称关键词。CTR/CPC由后端计算。没有收入或利润。需要日期；最近7天使用last_7_days。',
        'parameters': ReportArgs.model_json_schema()}},
    {'type': 'function', 'function': {'name': 'search_knowledge',
        'description': '只读检索投放知识、预算检查规则，返回原文、ID、来源和相似度。不生成回答。使用简短语义问题。',
        'parameters': SearchArgs.model_json_schema()}},
]
