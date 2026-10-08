"""真实只读验收；只保存计数、校验结果，不保存认证或账户明细。"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


def main():
    client = TestClient(app)
    records = []
    def query(kind, offset=0, start='2026-05-01', end='2026-06-07'):
        response = client.post('/api/baidu-reports/query', json={
            'report': kind, 'start_date': start, 'end_date': end, 'start_row': offset, 'page_size': 200})
        if response.status_code != 200:
            raise RuntimeError(response.json().get('detail', {}).get('code', 'http_failure'))
        data = response.json()
        records.append({'report': kind, 'dates': [start, end], 'start_row': offset, 'row_count': data['row_count'],
                        'total_row_count': data['total_row_count'], 'page': data['page'], 'total_pages': data['total_pages'],
                        'units': data['units']})
        assert len(data['rows']) == data['row_count']
        assert data['page'] == offset // 200 + 1
        return data
    evidence = {'verified_at': datetime.now(timezone.utc).isoformat(), 'source': 'real_baidu_api', 'requests': records, 'passed': False}
    try:
        interest = query('interest')
        first = query('region')
        total = first['total_row_count']
        pages = [first]
        if total > 200:
            pages.append(query('region', 200))
        last_offset = max(0, (first['total_pages'] - 1) * 200)
        if last_offset > 200:
            pages.append(query('region', last_offset))
        assert all(p['total_row_count'] == total for p in pages)
        assert pages[-1]['next_start_row'] is None
        assert pages[-1]['row_count'] == total - last_offset
        keys = [(r['date'], r['userName'], r['provinceName']) for p in pages for r in p['rows']]
        assert len(set(keys)) == len(keys), 'sampled_pages_overlap'
        repeat = query('region')
        assert repeat['rows'] == first['rows'], 'first_page_changed'
        day = query('region', start='2026-05-23', end='2026-05-23')
        assert all(r['date'] == '2026-05-23' for r in day['rows'])
        example = next((r for r in day['rows'] if r['provinceName'] == '北京'), None)
        evidence['example_found'] = example is not None
        if example:
            assert abs(Decimal(example['ctr']) - Decimal(example['click']) / Decimal(example['impression'])) < Decimal('1e-12')
            evidence['example_display'] = {k: f'{Decimal(example[k]):.2f}' for k in ('cost', 'cpc', 'cpm')}
            evidence['example_display']['ctr'] = f"{Decimal(example['ctr']) * 100:.2f}%"
        empty = query('region', start='2026-05-01', end='2026-05-01')
        evidence.update(passed=True, interest_total=interest['total_row_count'], region_total=total,
                        sampled_pages_no_overlap=True, repeated_first_page_identical=True,
                        empty_date_verified=empty['total_row_count'] == 0)
    except Exception as error:
        # 不打印第三方异常正文、请求、连接或凭据。
        evidence['failure_type'] = type(error).__name__
    output = Path(__file__).resolve().parents[2] / 'artifacts/baidu-reports-real-verification.json'
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(evidence, ensure_ascii=False))
    if not evidence['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
