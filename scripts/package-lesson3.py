"""第三课无凭据运行包。白名单打包；不复用旧的含真实环境打包行为。"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from urllib.parse import urlsplit, unquote
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    for case in ('A', 'B', 'C', 'report', 'empty', 'recent', 'missing'):
        evidence = ROOT / f'artifacts/lesson3-real-{case}.json'
        if not evidence.exists() or not json.loads(evidence.read_text(encoding='utf-8'))['passed']:
            raise SystemExit(f'Real verification required: {case}')
    old = json.loads((ROOT / 'scripts/student-runtime-package-files.json').read_text(encoding='utf-8-sig'))
    files = {dest: source for source, dest in old if source not in ('backend/.env', 'docs/student-runtime-readme.md', 'scripts/student.ps1')}
    files['README.md'] = 'docs/lesson-3-student.md'
    additions = ['backend/.env.example', 'backend/requirements.in', 'scripts/project.ps1', 'scripts/lesson3.ps1']
    additions += [p.relative_to(ROOT).as_posix() for p in (ROOT / 'backend/app').rglob('*.py')]
    additions += [p.relative_to(ROOT).as_posix() for p in (ROOT / 'frontend/src').rglob('*') if p.is_file() and p.suffix in ('.ts', '.vue', '.css')]
    additions += [p.relative_to(ROOT).as_posix() for p in (ROOT / 'data/knowledge').rglob('*') if p.is_file() and p.suffix.lower() in ('.md', '.csv')]
    files.update({name: name for name in additions})
    environment = dotenv_values(ROOT / 'backend/.env')
    secrets = [str(v).encode() for k, v in environment.items()
               if v and len(str(v)) > 8 and any(part in k.upper() for part in ('KEY', 'PASSWORD', 'DATABASE_URL', 'TOKEN'))]
    password = urlsplit(environment.get('DATABASE_URL') or '').password
    if password:
        secrets.extend([password.encode(), unquote(password).encode()])
    entries, manifest = {}, []
    for dest, source in sorted(files.items()):
        path = Path(dest)
        if path.name.startswith('.env') and path.name != '.env.example':
            raise SystemExit('Real environment file forbidden')
        if any(part in path.parts for part in ('.git', '.venv', 'node_modules', '__pycache__', 'artifacts')):
            raise SystemExit('Excluded directory in package')
        data = (ROOT / source).read_bytes()
        if any(secret in data for secret in secrets):
            raise SystemExit(f'Credential detected in {dest}; package not created')
        if path.suffix == '.py':
            compile(data, dest, 'exec')
        entries[f'marketing-agent/{dest}'] = data
        manifest.append({'file': dest, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    entries['marketing-agent/MANIFEST.json'] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
    output = ROOT / f'artifacts/marketing-agent-lesson3-student-{datetime.now():%Y%m%d-%H%M%S}.zip'
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(entries)
    print(json.dumps({'zip': str(output), 'files': len(entries), 'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'credential_scan': 'passed'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
