"""真实服务验证入口。只读知识库，会消耗模型额度；无 Mock 回退。"""
import json
from datetime import datetime, timezone
from pathlib import Path
from app.rag_config import get_settings, RagError
from app.rag_models import KnowledgeQuery
from app.services.knowledge import knowledge_status, answer_question, retrieve

QUESTIONS = [
    '为什么汇总 CTR 不能直接平均各行 CTR？',
    '把每个计划的点击百分比加起来除以计划数，能代表整体表现吗？',
    '百度推广账户退款需要哪些材料、几个工作日到账？',
]


def main():
    record = {'mode': 'real_services_only', 'time': datetime.now(timezone.utc).isoformat(), 'cases': [], 'passed': False}
    try:
        settings = get_settings()
        status = knowledge_status(settings)
        record['knowledge_status'] = status.model_dump()
        if not status.ready:
            raise RagError(status.code, status.message)
        for index, question in enumerate(QUESTIONS):
            response = answer_question(settings, KnowledgeQuery(question=question))
            passed = response.status == ('insufficient_evidence' if index == 2 else 'answered')
            if index < 2:
                passed = passed and any(c.section == '汇总 CTR 为什么不能直接平均' for c in response.citations)
            record['cases'].append({'case': index + 1, 'passed': passed, 'response': response.model_dump()})
        record['top_k_comparison'] = [retrieve(settings, KnowledgeQuery(question=QUESTIONS[0], top_k=k)).model_dump() for k in (1, 3)]
        record['passed'] = all(case['passed'] for case in record['cases'])
    except RagError as error:
        record['error'] = {'code': error.code, 'message': error.message}
    target = Path(__file__).resolve().parents[2] / 'artifacts' / 'lesson-2-real-verification.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': record['passed'], 'completed_cases': len(record['cases']), 'record': str(target)}, ensure_ascii=False))
    raise SystemExit(0 if record['passed'] else 1)


if __name__ == '__main__':
    main()
