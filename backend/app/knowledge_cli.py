"""python -m app.knowledge_cli check|init|ingest [--rebuild]。不输出凭据。"""
import argparse
import json
from app.rag_config import get_settings, RagError
from app.services.knowledge_store import initialize, inspect_database
from app.services.knowledge import ingest_documents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['check', 'init', 'ingest'])
    parser.add_argument('--rebuild', action='store_true', help='仅重建本项目知识集合的向量')
    args = parser.parse_args()
    try:
        settings = get_settings()
        if args.command == 'check':
            result = inspect_database(settings)
            # 只输出白名单字段，不输出数据库 URL、模型地址、签名或凭据。
            print(json.dumps({k: result[k] for k in ('client_tls', 'backend_tls', 'vector_schema', 'documents', 'chunks')}, ensure_ascii=False))
        elif args.command == 'init':
            initialize(settings)
            print('Project tables ready. No documents imported or removed.')
        else:
            print(json.dumps(ingest_documents(settings, args.rebuild), ensure_ascii=False))
    except RagError as error:
        print(f'{error.code}: {error.message}')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
