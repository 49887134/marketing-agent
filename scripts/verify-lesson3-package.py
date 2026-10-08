"""解压后的学生后端只读烟测；凭据仅通过子进程环境注入，不写入包。"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive_path = Path(sys.argv[1]).resolve()
    target = (ROOT / 'artifacts' / f'lesson3-package-smoke-{datetime.now():%Y%m%d-%H%M%S}').resolve()
    target.mkdir()
    with ZipFile(archive_path) as archive:
        for name in archive.namelist():
            if not (target / name).resolve().is_relative_to(target):
                raise ValueError('Unsafe archive path')
        archive.extractall(target)
    package = target / 'marketing-agent'
    assert not (package / 'backend/.env').exists()
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    environment.update({k: v for k, v in dotenv_values(ROOT / 'backend/.env').items() if v is not None})
    environment['PYTHONUTF8'] = '1'
    program = '''
import json
from pathlib import Path
from fastapi.testclient import TestClient
import app.main as module
assert Path(module.__file__).resolve().is_relative_to(Path.cwd())
client = TestClient(module.app)
metadata = client.get('/api/agent/metadata')
assert metadata.status_code == 200, 'metadata request failed'
scope = metadata.json()['scope']
report = client.get('/api/reports/campaigns', params={k: scope[k] for k in ('start_date','end_date')})
assert report.status_code == 200, 'report request failed'
assert report.json()['total'] == scope['rows']
knowledge = client.get('/api/knowledge/status')
assert knowledge.status_code == 200 and knowledge.json()['ready'], 'knowledge not ready'
print(json.dumps({'packed_backend': True, 'metadata': True, 'reports': True, 'knowledge': True, 'rows': scope['rows']}))
'''
    completed = subprocess.run([str(ROOT / 'backend/.venv/Scripts/python.exe'), '-c', program],
                               cwd=package / 'backend', env=environment, capture_output=True, text=True, encoding='utf-8')
    if completed.returncode:
        # 不输出第三方异常堆栈，防止连接字符串出现在日志。
        raise SystemExit('Packed backend smoke failed; inspect configuration locally without sharing credentials.')
    evidence = json.loads(completed.stdout)
    evidence.update(package=str(archive_path), dependency_environment='existing project .venv', fresh_machine_install=False)
    (ROOT / 'artifacts/lesson3-package-verification.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == '__main__':
    main()
