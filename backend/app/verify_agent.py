"""真实数据库与模型课堂验收；只读，不迁移或入库。"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services import agent

QUESTIONS = {
    'A': '为什么汇总 CTR 不能直接平均？',
    'B': '分析演示日期范围内各计划的投放表现，结合知识库规则，说明哪些问题值得优先检查。',
    'C': '哪个计划最赚钱？',
    'report': '查询演示日期范围内各计划的消费、CTR和CPC，只看报表数据。',
    'empty': '查询演示日期范围内计划名称为不存在的计划XYZ的投放报表。',
    'recent': '分析最近7天各计划的投放表现。',
    'missing': '查询各计划的投放报表。',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=[*QUESTIONS, 'all'], default='all')
    args = parser.parse_args()
    client = TestClient(app)
    meta = client.get('/api/agent/metadata')
    meta.raise_for_status()
    scope = meta.json()['scope']
    filters = {key: scope[key] for key in ('start_date', 'end_date')} | {'keyword': ''}
    cases = QUESTIONS if args.case == 'all' else {args.case: QUESTIONS[args.case]}
    root = Path(__file__).resolve().parents[2] / 'artifacts'
    root.mkdir(exist_ok=True)
    all_passed = True
    for name, question in cases.items():
        exchanges = []
        original_post = agent.post_model
        def capture(*values):
            result = original_post(*values)
            message = result['choices'][0]['message']
            exchanges.append({k: message[k] for k in ('content', 'tool_calls') if k in message})
            return result
        agent.post_model = capture
        try:
            response = client.post('/api/agent/analyze', json={'question': question, 'filters': {} if name == 'missing' else filters})
        finally:
            agent.post_model = original_post
        response.raise_for_status()
        body = response.json()
        names = {event['name'] for event in body['events']}
        if name == 'A':
            passed = body['status'] == 'completed' and names == {'search_knowledge'} and bool(body['analysis']['rules'])
        elif name == 'B':
            original = client.get('/api/reports/campaigns', params=filters).json()
            passed = (body['status'] == 'completed' and names == {'query_report', 'search_knowledge'}
                and body['reports'][0]['summary'] == original['summary'] and bool(body['analysis']['suggestions']))
        elif name == 'C':
            passed = body['status'] in ('unsupported', 'needs_input') and '收入' in body['message']
        elif name == 'report':
            passed = body['status'] == 'completed' and names == {'query_report'}
        elif name == 'empty':
            passed = body['status'] == 'no_data' and bool(body['reports']) and body['reports'][0]['total'] == 0
        elif name == 'recent':
            passed = not body['reports'] and (any(e['code'] == 'outside_demo_range' for e in body['errors']) or body['status'] in ('needs_input', 'unsupported'))
        else:
            passed = body['status'] == 'needs_input' and not body['reports']
        all_passed = all_passed and passed
        result = {'case': name, 'passed': passed, 'verified_at': datetime.now(timezone.utc).isoformat(), 'scope': scope, 'response': body, 'model_outputs': exchanges}
        (root / f'lesson3-real-{name}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'case': name, 'passed': passed, 'status': body['status'], 'tools': list(names), 'errors': body['errors']}, ensure_ascii=False), flush=True)
    if not all_passed:
        raise SystemExit(1)
    

if __name__ == '__main__':
    main()
