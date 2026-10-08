"""生成无文档、无截图、无凭据的可运行 ZIP。"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts' / f'marketing-agent-runtime-{datetime.now():%Y%m%d-%H%M%S}.zip'


def add_tree(files, folder, suffixes):
    for path in (ROOT / folder).rglob('*'):
        if path.is_file() and path.suffix.lower() in suffixes:
            files[path.relative_to(ROOT).as_posix()] = path


def main():
    files = {}
    for name in [
        '.tools/package.json', '.tools/package-lock.json',
        'scripts/npm-local.cmd', 'scripts/install-electron.ps1', 'scripts/project.ps1',
        'backend/.env.example', 'backend/requirements.in', 'backend/requirements.lock',
        'frontend/.env.example', 'frontend/package.json', 'frontend/package-lock.json',
        'frontend/index.html', 'frontend/tsconfig.json', 'frontend/vite.config.ts',
        'frontend/electron/main.cjs',
    ]:
        files[name] = ROOT / name
    add_tree(files, 'backend/app', {'.py'})
    add_tree(files, 'frontend/src', {'.ts', '.vue', '.css'})

    # 对外统一为中性的启动脚本名，不带课程或角色名称。
    files['scripts/run.ps1'] = ROOT / 'scripts/project.ps1'

    environment = dotenv_values(ROOT / 'backend/.env')
    secrets = [str(value).encode() for key, value in environment.items()
               if value and len(str(value)) > 8 and any(part in key.upper() for part in ('KEY', 'PASSWORD', 'DATABASE_URL', 'TOKEN', 'USER_NAME'))]
    password = urlsplit(environment.get('DATABASE_URL') or '').password
    if password:
        secrets.extend([password.encode(), unquote(password).encode()])

    entries = {}
    manifest = []
    for destination, source in sorted(files.items()):
        path = Path(destination)
        if path.suffix.lower() == '.md' or any(part in path.parts for part in ('.git', '.venv', 'node_modules', '__pycache__', 'tests', 'artifacts')):
            raise SystemExit(f'Forbidden package entry: {destination}')
        if path.name == '.env':
            raise SystemExit('Real .env is forbidden')
        data = source.read_bytes()
        if any(secret in data for secret in secrets):
            raise SystemExit(f'Credential detected in {destination}')
        archive_name = f'marketing-agent/{destination}'
        entries[archive_name] = data
        manifest.append({'file': destination, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})

    entries['marketing-agent/MANIFEST.json'] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
    OUTPUT.parent.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, 'w', ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    with ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP integrity failed')
        forbidden = [name for name in archive.namelist() if name.lower().endswith('.md') or name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        if forbidden:
            raise SystemExit(f'Forbidden files: {forbidden}')
    print(json.dumps({'zip': str(OUTPUT), 'files': len(entries), 'bytes': OUTPUT.stat().st_size,
                      'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
