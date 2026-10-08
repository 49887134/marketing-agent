"""故障与边界使用替身；真实验收另见 app.verify_agent。"""
import asyncio
import json
from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.agent_models import AgentRequest, ReportArgs, Analysis
from app.rag_config import Settings, RagError
from app.services import agent, agent_tools

SCOPE = {'start_date': '2026-09-01', 'end_date': '2026-09-21', 'rows': 61, 'simulated': True}
FILTERS = {'start_date': '2026-09-01', 'end_date': '2026-09-21'}


def call(name='query_report', arguments=None, id='one'):
    return {'id': id, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(FILTERS if arguments is None else arguments)}}


def completion(calls=None, content=None):
    return {'choices': [{'message': {'role': 'assistant', **({'tool_calls': calls} if calls else {'content': json.dumps(content)})}}]}


@pytest.fixture
def isolated(monkeypatch):
    monkeypatch.setattr(agent_tools, 'report_scope', lambda _: SCOPE)
    monkeypatch.setattr(agent_tools, 'search_knowledge', lambda *args: {'chunks': []})
    return Settings(database_url='', chat_model='test', chat_api_key='test', chat_base_url='https://invalid.test')


def run(settings, question='分析报表'):
    return asyncio.run(agent.run_agent(AgentRequest(question=question, filters=ReportArgs(**FILTERS)), settings))


@pytest.mark.parametrize('bad', [call('shell'), call(arguments={'sql': 'SELECT *'}), call(arguments={'start_date': '2026-02-30'}), call(arguments={'start_date': '2026-09-21', 'end_date': '2026-09-01'}), call('search_knowledge', {'question': 'CTR', 'top_k': 99})])
def test_invalid_calls_never_execute(monkeypatch, isolated, bad):
    monkeypatch.setattr(agent, 'post_model', lambda *args: completion([bad]))
    monkeypatch.setattr(agent_tools, 'query_report', lambda *args: pytest.fail('非法参数不能调用工具'))
    result = run(isolated)
    assert result['status'] == 'error' and result['events'] == []


def test_tool_limit(monkeypatch, isolated):
    monkeypatch.setattr(agent, 'post_model', lambda *args: completion([call(id=str(i)) for i in range(4)]))
    result = run(isolated)
    assert result['errors'][0]['code'] == 'tool_limit' and not result['events']


def test_repeated_call_limit(monkeypatch, isolated):
    monkeypatch.setattr(agent, 'post_model', lambda *args: completion([call('search_knowledge', {'question': 'CTR'})]))
    result = run(isolated)
    assert result['calls'] == 3 and result['status'] == 'error'
    assert result['errors'][-1]['code'] == 'tool_limit'


def test_graph_step_limit(monkeypatch, isolated):
    monkeypatch.setattr(agent, 'MAX_STEPS', 1)
    monkeypatch.setattr(agent, 'post_model', lambda *args: completion([call('search_knowledge', {'question': 'CTR'})]))
    assert run(isolated)['errors'][-1]['code'] == 'step_limit'


def test_model_failure_sanitized(monkeypatch, isolated):
    def fail(*args):
        raise RagError('model_unavailable', '模型调用失败')
    monkeypatch.setattr(agent, 'post_model', fail)
    result = run(isolated)
    assert result['status'] == 'error' and not result['events']
    assert 'SECRET' not in json.dumps(result)


def test_single_tool_failure_retains_success(monkeypatch, isolated):
    responses = iter([
        completion([call('search_knowledge', {'question': 'CTR'}), call(id='two')]),
        completion(content={'status': 'ready', 'message': ''}),
        completion(content={'interpretation': [], 'rules': [{'text': '点击率是点击占展现的比例。', 'citation_ids': ['real'], 'fact_ids': []}], 'suggestions': [], 'limitations': ['报表查询失败，无法分析计划表现。']}),
    ])
    monkeypatch.setattr(agent, 'post_model', lambda *args: next(responses))
    monkeypatch.setattr(agent_tools, 'search_knowledge', lambda *args: {'chunks': [{'chunk_id': 'real', 'content': 'CTR是点击除以展现'}]})
    def fail(*args):
        raise RagError('database_unavailable', '报表查询失败')
    monkeypatch.setattr(agent_tools, 'query_report', fail)
    result = run(isolated)
    assert result['status'] == 'partial'
    assert [e['status'] for e in result['events']] == ['success', 'failed']
    assert result['analysis'] and not result['reports']


def test_hallucinated_references_and_numbers_rejected():
    state = {'reports': [], 'chunks': []}
    with pytest.raises(ValueError):
        agent.validate_analysis(Analysis(rules=[{'text': '规则', 'citation_ids': ['invented']}]), state)
    with pytest.raises(ValueError):
        agent.validate_analysis(Analysis(rules=[{'text': 'CTR为99%', 'citation_ids': ['ok']}]), {'reports': [], 'chunks': [{'chunk_id': 'ok'}]})


def test_report_totals_and_ratios(monkeypatch):
    from app.models import CampaignReport, ReportResponse, ReportSummary
    rows = [CampaignReport(date='2026-09-01', campaign_id='C1', campaign_name='计划', impressions=100, clicks=10, cost='20.00', conversions=1, ctr=.1, cpc='2.00'),
            CampaignReport(date='2026-09-02', campaign_id='C1', campaign_name='计划', impressions=900, clicks=9, cost='90.00', conversions=0, ctr=.01, cpc='10.00')]
    summary = ReportSummary(impressions=1000, clicks=19, cost='110.00', conversions=1, ctr=.019, cpc='5.79')
    monkeypatch.setattr(agent_tools, 'get_campaign_reports', lambda *args: ReportResponse(items=rows, total=2, summary=summary))
    report = agent_tools.query_report(ReportArgs(**FILTERS), SCOPE)
    assert report['facts'][0]['ctr'] == .019
    assert Decimal(report['facts'][0]['cpc']) == Decimal('5.79')
    assert report['summary']['cost'] == '110.00'
    other = agent_tools.query_report(ReportArgs(start_date='2026-09-02', end_date='2026-09-21'), SCOPE)
    assert report['facts'][0]['fact_id'] != other['facts'][0]['fact_id']


def test_recent_range_is_not_replaced(monkeypatch):
    monkeypatch.setattr(agent_tools, 'today', lambda: date(2030, 1, 1))
    with pytest.raises(RagError) as error:
        agent_tools.query_report(ReportArgs(**FILTERS, period='last_7_days'), SCOPE)
    assert error.value.code == 'outside_demo_range'


def test_missing_dates():
    with pytest.raises(RagError) as error:
        agent_tools.query_report(ReportArgs(), SCOPE)
    assert error.value.code == 'missing_dates'


def test_timeout(monkeypatch, isolated):
    monkeypatch.setattr(agent, 'TOTAL_TIMEOUT', 0.001)
    import time
    monkeypatch.setattr(agent, 'post_model', lambda *args: time.sleep(.02))
    result = run(isolated)
    assert result['status'] == 'error' and result['errors'][-1]['code'] == 'agent_timeout'


@pytest.mark.parametrize('body', [{'question': ''}, {'question': '报表', 'filters': {'start_date': '2026-02-30'}}, {'question': '报表', 'tools': ['shell']}])
def test_api_rejects_invalid_input(body):
    assert TestClient(app).post('/api/agent/analyze', json=body).status_code == 422
