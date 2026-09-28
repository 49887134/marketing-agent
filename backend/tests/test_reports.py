from decimal import Decimal, ROUND_HALF_UP

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
URL = '/api/reports/campaigns'


def test_health_and_default_summary():
    assert client.get('/health').json() == {'status': 'ok'}
    response = client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 21
    assert len({row['campaign_id'] for row in data['items']}) == 3
    assert len({row['date'] for row in data['items']}) == 7
    assert any(row['conversions'] == 0 for row in data['items'])
    assert any(row['conversions'] > 0 for row in data['items'])
    assert_summary(data)


def assert_summary(data):
    rows, summary = data['items'], data['summary']
    for key in ('impressions', 'clicks', 'conversions'):
        assert summary[key] == sum(row[key] for row in rows)
    cost = sum((Decimal(row['cost']) for row in rows), Decimal('0.00'))
    assert Decimal(summary['cost']) == cost
    if summary['impressions']:
        assert summary['ctr'] == pytest.approx(summary['clicks'] / summary['impressions'])
    if summary['clicks']:
        assert Decimal(summary['cpc']) == (cost / summary['clicks']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def test_inclusive_date_and_keyword_filters():
    response = client.get(URL, params={'start_date': '2026-09-02', 'end_date': '2026-09-04', 'keyword': '  课程  '})
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 3
    assert [row['date'] for row in data['items']] == ['2026-09-02', '2026-09-03', '2026-09-04']
    assert all(row['campaign_name'] == '课程咨询推广' for row in data['items'])
    assert_summary(data)
    assert client.get(URL, params={'start_date': '2026-09-07'}).json()['total'] == 3
    assert client.get(URL, params={'end_date': '2026-09-01'}).json()['total'] == 3


@pytest.mark.parametrize('params', [
    {'keyword': '不存在的计划'}, {'start_date': '2030-01-01'},
])
def test_empty_results(params):
    response = client.get(URL, params=params)
    assert response.status_code == 200
    assert response.json() == {'items': [], 'total': 0, 'summary': {
        'impressions': 0, 'clicks': 0, 'cost': '0.00', 'conversions': 0, 'ctr': None, 'cpc': None,
    }}


@pytest.mark.parametrize('params', [
    {'start_date': '2026-02-30'}, {'end_date': '2026-13-01'},
    {'start_date': '20260901'}, {'start_date': '2026-9-1'}, {'end_date': ''},
    {'start_date': '2026-09-07', 'end_date': '2026-09-01'}, {'keyword': '字' * 101},
])
def test_invalid_query(params):
    response = client.get(URL, params=params)
    assert response.status_code == 422
    assert response.json()['detail']


@pytest.mark.parametrize(('day', 'ctr'), [('02', 0.0), ('05', None)])
def test_zero_denominators(day, ctr):
    data = client.get(URL, params={'start_date': f'2026-09-{day}', 'end_date': f'2026-09-{day}', 'keyword': '新客'}).json()
    assert data['total'] == 1
    for metrics in (data['items'][0], data['summary']):
        assert metrics['clicks'] == 0
        assert metrics['cpc'] is None
        assert metrics['ctr'] == ctr


def test_cors_allowlist():
    for origin in ('http://127.0.0.1:5173', 'app://dashboard'):
        response = client.get(URL, headers={'Origin': origin})
        assert response.headers['access-control-allow-origin'] == origin
    for origin in ('https://untrusted.example', 'null'):
        assert 'access-control-allow-origin' not in client.get(URL, headers={'Origin': origin}).headers
