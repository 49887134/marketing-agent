"""HTTP 替身验证，不表示真实百度账户已接通。"""
import copy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.baidu_report_config import BaiduReportSettings, get_baidu_settings, REPORT_URL
from app.services import baidu_reports

QUERY = {'start_date': '2026-05-01', 'end_date': '2026-06-07'}
ROW = {'date': '2026-05-22', 'ctr': 0, 'interestsName': '', 'cpm': 0, 'cost': 0, 'cpc': 0, 'impression': 4, 'userName': '示例账户', 'click': 0}


def response(rows=None, total=None):
    rows = [ROW] if rows is None else rows
    return {'header': {'failures': [], 'succ': 1, 'desc': 'success', 'status': 0},
            'body': {'data': [{'rowCount': len(rows), 'totalRowCount': len(rows) if total is None else total, 'rows': rows}]}}


@pytest.fixture
def setup(monkeypatch):
    settings = BaiduReportSettings(access_token='PRIVATE_TEST_TOKEN', user_name='PRIVATE_AUTH_ACCOUNT')
    app.dependency_overrides[get_baidu_settings] = lambda: settings
    original = httpx.AsyncClient
    requests = []
    def install(handler):
        def handle(request):
            requests.append(request)
            return handler(request)
        monkeypatch.setattr(baidu_reports.httpx, 'AsyncClient', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle)))
    yield TestClient(app), settings, install, requests
    app.dependency_overrides.pop(get_baidu_settings, None)


def test_success_protocol_and_zero(setup):
    client, _, install, requests = setup
    install(lambda _: httpx.Response(200, json=response()))
    result = client.post('/api/baidu-reports/query', json=QUERY)
    assert result.status_code == 200
    data = result.json()
    assert data['source'] == 'baidu_api' and data['row_count'] == data['total_row_count'] == 1
    assert data['rows'][0]['cost'] == '0' and data['rows'][0]['click'] == 0
    assert data['rows'][0]['interestsName'] is None
    assert data['units'] == {'amount': 'unknown', 'ctr': 'unknown'}
    assert 'PRIVATE_' not in result.text
    request = requests[0]
    assert str(request.url) == REPORT_URL and request.method == 'POST'
    assert 'authorization' not in request.headers
    sent = json.loads(request.content)
    assert sent['header'] == {'accessToken': 'PRIVATE_TEST_TOKEN', 'userName': 'PRIVATE_AUTH_ACCOUNT'}
    assert sent['body'] == {'reportType': 2521394, 'startDate': '2026-05-01', 'endDate': '2026-06-07', 'timeUnit': 'DAY',
                            'columns': baidu_reports.columns('interest'), 'sorts': [{'column': 'date', 'sortRule': 'ASC'}, {'column': 'interestsName', 'sortRule': 'ASC'}], 'filters': [], 'startRow': 0, 'rowCount': 200, 'needSum': False}


def test_empty(setup):
    client, _, install, _ = setup
    install(lambda _: httpx.Response(200, json=response([])))
    body = client.post('/api/baidu-reports/query', json=QUERY).json()
    assert body['rows'] == [] and body['total_row_count'] == 0 and body['next_start_row'] is None


def test_region_pagination_first_second_last(setup):
    client, _, install, requests = setup
    row = {**ROW, 'provinceName': '', 'ctr': '0.024193548387096774', 'cpc': '2.2083333333333335'}
    def handler(request):
        offset = json.loads(request.content)['body']['startRow']
        return httpx.Response(200, json=response([row] * min(200, 763-offset), total=763))
    install(handler)
    first = client.post('/api/baidu-reports/query', json={**QUERY, 'report': 'region'}).json()
    assert first['next_start_row'] == 200 and first['total_pages'] == 4
    assert first['units']['ctr'] == 'ratio' and first['rows'][0]['provinceName'] is None
    assert first['rows'][0]['ctr'] == row['ctr'] and first['rows'][0]['cpc'] == row['cpc']
    assert 'interestsName' not in first['rows'][0]
    second = client.post('/api/baidu-reports/query', json={**QUERY, 'report': 'region', 'start_row': 200}).json()
    assert second['next_start_row'] == 400 and second['page'] == 2
    last = client.post('/api/baidu-reports/query', json={**QUERY, 'report': 'region', 'start_row': 600}).json()
    assert last['next_start_row'] is None
    assert last['row_count'] == 163 and last['page'] == 4
    assert [json.loads(r.content)['body']['startRow'] for r in requests] == [0, 200, 600]
    sent = json.loads(requests[0].content)['body']
    assert sent['reportType'] == 2324048 and sent['columns'] == baidu_reports.columns('region')
    assert sent['sorts'][1] == {'column': 'provinceName', 'sortRule': 'ASC'}


def test_incomplete_middle_page_rejected(setup):
    client, _, install, _ = setup
    install(lambda _: httpx.Response(200, json=response([ROW], total=763)))
    assert client.post('/api/baidu-reports/query', json=QUERY).json()['detail']['code'] == 'baidu_invalid_response'


@pytest.mark.parametrize('status,code', [(401, 'baidu_auth_failed'), (403, 'baidu_auth_failed'), (429, 'baidu_rate_limited'), (500, 'baidu_http_error'), (302, 'baidu_http_error')])
def test_http_failures_no_credential_echo(setup, status, code):
    client, _, install, _ = setup
    install(lambda _: httpx.Response(status, text='PRIVATE_TEST_TOKEN PRIVATE_AUTH_ACCOUNT'))
    result = client.post('/api/baidu-reports/query', json=QUERY)
    assert result.json()['detail']['code'] == code and 'PRIVATE_' not in result.text
    assert 'rows' not in result.json()


def test_business_auth_error_and_partial_not_returned(setup):
    client, _, install, _ = setup
    payload = response()
    payload['header'].update(status=1, failures=[{'code': 123, 'message': 'PRIVATE_TEST_TOKEN'}])
    install(lambda _: httpx.Response(200, json=payload))
    result = client.post('/api/baidu-reports/query', json=QUERY)
    assert result.status_code == 502 and result.json()['detail']['code'] == 'baidu_business_error'
    assert 'PRIVATE_' not in result.text and 'rows' not in result.json()


@pytest.mark.parametrize('invalid', [{}, {'header': {'status': 0}}, {'header': {'status': 0, 'failures': []}, 'body': {'data': []}}, {'header': {'status': 0, 'failures': []}, 'body': {'data': [{}, {}]}}])
def test_invalid_envelope(setup, invalid):
    client, _, install, _ = setup
    install(lambda _: httpx.Response(200, json=invalid))
    assert client.post('/api/baidu-reports/query', json=QUERY).json()['detail']['code'] == 'baidu_invalid_response'


@pytest.mark.parametrize('field,value', [('rowCount', 2), ('totalRowCount', -1), ('rows', [{**ROW, 'cost': 'NaN'}]), ('rows', [{**ROW, 'click': True}])])
def test_invalid_report(setup, field, value):
    client, _, install, _ = setup
    payload = copy.deepcopy(response())
    payload['body']['data'][0][field] = value
    install(lambda _: httpx.Response(200, json=payload))
    assert client.post('/api/baidu-reports/query', json=QUERY).json()['detail']['code'] == 'baidu_invalid_response'


def test_missing_config_and_status_do_not_leak(setup):
    client, settings, install, requests = setup
    install(lambda _: pytest.fail('缺配置不得调用百度'))
    assert 'PRIVATE_' not in client.get('/api/baidu-reports/status').text
    settings.access_token = ''
    assert client.get('/api/baidu-reports/status').json()['configured'] is False
    assert client.post('/api/baidu-reports/query', json=QUERY).status_code == 503
    assert not requests


@pytest.mark.parametrize('override', [{'start_date': '2026-02-30'}, {'start_date': '2026/05/01'}, {'start_date': '2026-07-01'}, {'start_date': '2020-01-01'}, {'start_row': -1}, {'start_row': 1}, {'report': 'any_url'}, {'report': 2324048}, {'page_size': 201}, {'page_size': True}, {'accessToken': 'forbidden'}, {'reportType': 999}])
def test_invalid_query(setup, override):
    client, _, install, requests = setup
    install(lambda _: pytest.fail('非法参数不得调用百度'))
    assert client.post('/api/baidu-reports/query', json={**QUERY, **override}).status_code == 422
    assert not requests


@pytest.mark.parametrize('exception,code', [(httpx.ReadTimeout('secret'), 'baidu_timeout'), (httpx.ConnectError('secret'), 'baidu_network_error')])
def test_network_errors(setup, exception, code):
    client, _, install, _ = setup
    def fail(_):
        raise exception
    install(fail)
    result = client.post('/api/baidu-reports/query', json=QUERY)
    assert result.json()['detail']['code'] == code and 'secret' not in result.text


def test_non_json_and_decimal_preservation(setup):
    client, _, install, _ = setup
    install(lambda _: httpx.Response(200, text='<html>error</html>'))
    assert client.post('/api/baidu-reports/query', json=QUERY).status_code == 502
    row = {**ROW, 'cost': '123456.78901', 'ctr': '0.00123', 'unknown': 'PRIVATE_TEST_TOKEN'}
    install(lambda _: httpx.Response(200, json=response([row])))
    result = client.post('/api/baidu-reports/query', json=QUERY)
    assert result.json()['rows'][0]['cost'] == '123456.78901'
    assert result.json()['rows'][0]['ctr'] == '0.00123' and 'PRIVATE_' not in result.text
