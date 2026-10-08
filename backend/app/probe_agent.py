"""只读检查课堂数据与原生工具调用，不输出配置或凭据。"""
import json
from pathlib import Path
from sqlalchemy import text
from app.database import database
from app.rag_config import get_settings
from app.services.model_client import post_model
from app.services.knowledge import knowledge_status


def main():
    settings = get_settings()
    with database(settings) as conn:
        scope = dict(conn.execute(text('SELECT min(report_date) AS start_date, max(report_date) AS end_date, count(*) AS rows FROM marketing_agent.campaign_daily_reports')).mappings().one())
        sources = [dict(row) for row in conn.execute(text('SELECT data_source,count(*) AS rows FROM marketing_agent.campaign_daily_reports GROUP BY data_source')).mappings()]
        budget = conn.execute(text("SELECT count(*) FROM marketing_agent.knowledge_chunks WHERE source LIKE '%05-budget-rules.md'")).scalar_one()
    response = post_model(settings, 'chat', '/chat/completions', {
        'model': settings.chat_model, 'temperature': 0, 'max_tokens': 300,
        'messages': [{'role': 'user', 'content': '请调用 search_knowledge 查询汇总CTR规则，不要直接回答。'}],
        'tools': [{'type': 'function', 'function': {'name': 'search_knowledge', 'description': '查询知识', 'parameters': {'type': 'object', 'properties': {'question': {'type': 'string'}}, 'required': ['question']}}}],
        'tool_choice': 'auto',
    })
    message = response['choices'][0]['message']
    calls = message.get('tool_calls', [])
    result = {'scope': scope, 'sources': sources, 'knowledge': knowledge_status(settings).model_dump(), 'budget_chunks': budget,
              'chat_model': settings.chat_model, 'native_tool_calls': calls, 'native_supported': bool(calls)}
    path = Path(__file__).resolve().parents[2] / 'artifacts/lesson3-probe.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
