"""远程 PostgreSQL 连接边界。不会记录连接串或自动创建业务表。"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.rag_config import Settings, RagError


@contextmanager
def database(settings: Settings):
    if not settings.database_url:
        raise RagError('configuration_missing', '请在 backend/.env 配置 DATABASE_URL。')
    engine = None
    try:
        url = make_url(settings.database_url)
        if url.drivername != 'postgresql+psycopg':
            raise RagError('configuration_invalid', 'DATABASE_URL 必须使用 postgresql+psycopg://。')
        sslmode = url.query.get('sslmode', 'require')
        if sslmode not in ('require', 'verify-ca', 'verify-full'):
            raise RagError('configuration_invalid', '远程数据库须使用 sslmode=require、verify-ca 或 verify-full。')
        args = {'sslmode': sslmode, 'connect_timeout': 8, 'prepare_threshold': None}
        if os.getenv('DATABASE_SSLROOTCERT'):
            args['sslrootcert'] = os.environ['DATABASE_SSLROOTCERT']
        engine = create_engine(url, connect_args=args, poolclass=NullPool, hide_parameters=True)
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL statement_timeout = '10000'"))
            conn.execute(text("SET LOCAL lock_timeout = '5000'"))
            yield conn
    except SQLAlchemyError as error:
        sqlstate = getattr(getattr(error, 'orig', None), 'sqlstate', None)
        if sqlstate == '42501':
            raise RagError('database_permission_denied', '数据库权限不足，请检查 marketing_agent schema 的最小权限。') from None
        if sqlstate == '42P01':
            raise RagError('database_not_initialized', '本项目数据库表尚未初始化，请联系系统管理员。', 409) from None
        raise RagError('database_unavailable', '数据库操作失败。请检查连接、SSL、权限及初始化状态。') from None
    except (ValueError, TypeError):
        raise RagError('configuration_invalid', '数据库连接配置格式错误，请检查后端 .env（勿分享真实连接串截图）。') from None
    finally:
        if engine is not None:
            engine.dispose()
