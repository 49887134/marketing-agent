"""数据库管理员手动执行：python -m app.report_cli init|seed|check。"""
import argparse
import json
from pathlib import Path

from sqlalchemy import text

from app.database import database
from app.models import CampaignSource
from app.rag_config import RagError, get_settings

SEED_PATH = Path(__file__).resolve().parents[2] / 'data' / 'seed' / 'campaigns.json'
SEED_SOURCE = 'sample-v1'


def initialize() -> None:
    with database(get_settings()) as conn:
        conn.execute(text('CREATE SCHEMA IF NOT EXISTS marketing_agent'))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS marketing_agent.campaign_daily_reports (
            report_date date NOT NULL,
            campaign_id text NOT NULL,
            campaign_name text NOT NULL,
            impressions bigint NOT NULL CHECK (impressions >= 0),
            clicks bigint NOT NULL CHECK (clicks >= 0),
            cost numeric(14,2) NOT NULL CHECK (cost >= 0),
            conversions bigint NOT NULL CHECK (conversions >= 0),
            data_source text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (report_date, campaign_id)
        )'''))


def read_seed() -> list[CampaignSource]:
    rows = [CampaignSource.model_validate(row) for row in json.loads(SEED_PATH.read_text(encoding='utf-8'))]
    if len({(row.date, row.campaign_id) for row in rows}) != len(rows):
        raise RagError('invalid_seed', 'Seed 中 date + campaign_id 不唯一，未写入数据库。', 400)
    return rows


def seed_reports() -> dict:
    rows = read_seed()
    values = [{**row.model_dump(), 'data_source': SEED_SOURCE} for row in rows]
    with database(get_settings()) as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(791260903)'))
        before = conn.execute(text('SELECT count(*) FROM marketing_agent.campaign_daily_reports WHERE data_source=:source'), {'source': SEED_SOURCE}).scalar_one()
        conn.execute(text('''INSERT INTO marketing_agent.campaign_daily_reports
            (report_date,campaign_id,campaign_name,impressions,clicks,cost,conversions,data_source)
            VALUES (:date,:campaign_id,:campaign_name,:impressions,:clicks,:cost,:conversions,:data_source)
            ON CONFLICT (report_date,campaign_id) DO UPDATE SET
              campaign_name=excluded.campaign_name, impressions=excluded.impressions,
              clicks=excluded.clicks, cost=excluded.cost, conversions=excluded.conversions,
              data_source=excluded.data_source, updated_at=now()'''), values)
        after = conn.execute(text('SELECT count(*) FROM marketing_agent.campaign_daily_reports WHERE data_source=:source'), {'source': SEED_SOURCE}).scalar_one()
    return {'seed_rows': len(rows), 'managed_before': before, 'managed_after': after}


def check_reports() -> dict:
    with database(get_settings()) as conn:
        exists = bool(conn.execute(text("SELECT to_regclass('marketing_agent.campaign_daily_reports')")).scalar())
        if not exists:
            return {'ready': False, 'rows': 0}
        row = conn.execute(text('''SELECT count(*) AS rows, count(DISTINCT campaign_id) AS campaigns,
            min(report_date) AS start_date, max(report_date) AS end_date
            FROM marketing_agent.campaign_daily_reports''')).mappings().one()
        return {'ready': True, **dict(row)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init', 'seed', 'check'])
    args = parser.parse_args()
    try:
        if args.command == 'init':
            initialize()
            result = {'initialized': True}
        elif args.command == 'seed':
            result = seed_reports()
        else:
            result = check_reports()
        print(json.dumps(result, ensure_ascii=False, default=str))
    except RagError as error:
        print(f'{error.code}: {error.message}')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
