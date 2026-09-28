"""从仓库根目录执行 python data/mock/generate.py；确定性生成教学样本。"""
import json
from decimal import Decimal
from pathlib import Path

rows = []
for day in range(1, 8):
    for index, name in enumerate(['品牌词推广', '课程咨询推广', '新客拓展计划'], 1):
        impressions = 1000 * index + day * 120
        clicks = 25 * index + day * 3
        conversions = max(0, clicks // 15 - index)
        if index == 3 and day in (2, 5):
            clicks, conversions = 0, 0
        if index == 3 and day == 5:
            impressions = 0
        cost = (Decimal(clicks) * (Decimal('1.25') + Decimal(index) * Decimal('0.35'))).quantize(Decimal('0.01'))
        rows.append(dict(date=f'2026-09-{day:02}', campaign_id=f'C00{index}', campaign_name=name,
                         impressions=impressions, clicks=clicks, cost=str(cost), conversions=conversions))
Path(__file__).with_name('campaigns.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
