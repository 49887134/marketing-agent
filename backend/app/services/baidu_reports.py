"""百度官方报告只读适配器。直接请求，不落库、不回退模拟数据。"""
import asyncio
import json
from decimal import Decimal
import httpx
from pydantic import ValidationError
from app.baidu_report_config import REPORT_URL, BaiduReportSettings, BaiduReportError
from app.baidu_report_models import BaiduReportQuery, BaiduReportData

REPORTS = {
    'interest': {'report_type': 2521394, 'dimension': 'interestsName', 'label': '新兴趣报表'},
    'region': {'report_type': 2324048, 'dimension': 'provinceName', 'label': '地域报表'},
}


def columns(report: str) -> list[str]:
    return ['date', 'userName', REPORTS[report]['dimension'], 'impression', 'click', 'cost', 'ctr', 'cpc', 'cpm']


def build_payload(query: BaiduReportQuery, settings: BaiduReportSettings) -> dict:
    spec = REPORTS[query.report]
    return {
        'header': {'accessToken': settings.access_token, 'userName': settings.user_name},
        'body': {'reportType': spec['report_type'], 'startDate': query.start_date.isoformat(), 'endDate': query.end_date.isoformat(),
                 'timeUnit': 'DAY', 'columns': columns(query.report),
                 'sorts': [{'column': 'date', 'sortRule': 'ASC'}, {'column': spec['dimension'], 'sortRule': 'ASC'}], 'filters': [],
                 'startRow': query.start_row, 'rowCount': query.page_size, 'needSum': False},
    }


def parse_report(payload: object, query: BaiduReportQuery) -> BaiduReportData:
    try:
        header = payload['header']
        if not isinstance(header, dict) or type(header.get('status')) is not int or not isinstance(header.get('failures'), list):
            raise ValueError
        if header['status'] != 0 or header['failures'] or ('succ' in header and header['succ'] != 1):
            # 不转发上游 desc/message，避免其中含认证信息或请求回显。
            raise BaiduReportError('baidu_business_error', '百度拒绝了报表请求（认证、权限、参数或服务异常）。请在官方调试台核对令牌、账户授权和日期；未展示部分失败的数据。')
        reports = payload['body']['data']
        if not isinstance(reports, list) or len(reports) != 1:
            raise ValueError
        if any(REPORTS[query.report]['dimension'] not in row for row in reports[0]['rows']):
            raise ValueError
        report = BaiduReportData.model_validate(reports[0])
        if report.rowCount > query.page_size or (report.rowCount and query.start_row + report.rowCount > report.totalRowCount):
            raise ValueError
        if report.rowCount == 0 and query.start_row < report.totalRowCount:
            raise ValueError
        if query.start_row + report.rowCount < report.totalRowCount and report.rowCount != query.page_size:
            raise ValueError
        return report
    except (KeyError, TypeError, ValueError, ValidationError):
        raise BaiduReportError('baidu_invalid_response', '百度报告响应结构或记录数不符合单报告约定，未展示数据。') from None


async def query_baidu_report(query: BaiduReportQuery, settings: BaiduReportSettings) -> dict:
    settings.require_credentials()
    try:
        async with asyncio.timeout(settings.timeout):
            async with httpx.AsyncClient(timeout=settings.timeout, follow_redirects=False) as client:
                async with client.stream('POST', REPORT_URL, json=build_payload(query, settings)) as response:
                    if response.status_code in (401, 403):
                        raise BaiduReportError('baidu_auth_failed', '百度认证或权限校验失败，请检查后端令牌、账户名及报表授权。')
                    if response.status_code == 429:
                        raise BaiduReportError('baidu_rate_limited', '百度请求频率或配额受限，请稍后重试。', 503)
                    if response.status_code < 200 or response.status_code >= 300:
                        raise BaiduReportError('baidu_http_error', '百度报表 HTTP 请求失败，请检查官方服务状态后重试。')
                    raw = bytearray()
                    async for part in response.aiter_bytes():
                        raw.extend(part)
                        if len(raw) > 4 * 1024 * 1024:
                            raise BaiduReportError('baidu_response_too_large', '百度响应超过单页大小限制，请缩小每页条数。')
        payload = json.loads(raw, parse_float=Decimal)
    except (httpx.TimeoutException, TimeoutError):
        raise BaiduReportError('baidu_timeout', '百度报表查询超时，请稍后重试。', 504) from None
    except httpx.RequestError:
        raise BaiduReportError('baidu_network_error', '无法连接百度报表服务，请检查网络后重试。') from None
    except (ValueError, UnicodeError):
        raise BaiduReportError('baidu_invalid_response', '百度未返回有效的 JSON 报告。') from None
    report = parse_report(payload, query)
    return {
        'source': 'baidu_api', 'report_type': REPORTS[query.report]['report_type'], 'query': query.model_dump(mode='json'),
        'rows': [row.model_dump(mode='json', include=set(columns(query.report))) for row in report.rows],
        'row_count': report.rowCount, 'total_row_count': report.totalRowCount,
        'page': query.start_row // query.page_size + 1,
        'total_pages': (report.totalRowCount + query.page_size - 1) // query.page_size,
        'next_start_row': query.start_row + query.page_size if query.start_row + query.page_size < report.totalRowCount else None,
        'units': {'amount': settings.amount_unit, 'ctr': 'ratio' if query.report == 'region' else settings.ctr_unit},
    }
