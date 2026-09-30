"""按明确清单生成脱敏发布包，不遍历收集工作目录。"""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'test-results', 'artifacts'}
FORBIDDEN_TEXT = ('教学', '教师', '学员', '授课', '备课', '作业', '课堂', '课后', '模拟', 'lesson', 'student', 'homework', 'mock')


def safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or any(p in FORBIDDEN for p in path.parts):
        raise ValueError('Unsafe package path')
    if path.name.startswith('.env') and path.name != '.env.example':
        raise ValueError('Real environment files are forbidden')
    if path.suffix in ('.pyc', '.log') or 'guide' in path.name or 'verification' in path.name or 'homework' in path.name:
        raise ValueError('Internal or generated file is forbidden')
    return path


def main():
    pairs = json.loads((ROOT / 'scripts/lesson2-package-files.json').read_text(encoding='utf-8'))
    config = {**dotenv_values(ROOT / 'backend/.env'), **os.environ}
    secrets = [v.encode() for k, v in config.items() if v and len(v) >= 12 and (k.endswith('API_KEY') or k == 'DATABASE_URL')]
    files = {}
    manifest = []
    for source, target in pairs:
        source_path = ROOT / str(safe_path(source))
        if not source_path.resolve().is_relative_to(ROOT):
            raise ValueError('Source outside workspace')
        target = str(safe_path(target))
        if target in files:
            raise ValueError('Duplicate target')
        content = source_path.read_bytes()
        if any(secret in content for secret in secrets):
            raise ValueError('Credential content detected; package not generated')
        if source_path.suffix.lower() in {'.py', '.ps1', '.cmd', '.json', '.md', '.ts', '.vue', '.cjs', '.html'}:
            decoded = content.decode('utf-8')
            found = [word for word in FORBIDDEN_TEXT if word.lower() in decoded.lower()]
            if found:
                raise ValueError(f'Internal wording detected in {source}: {found}')
        files[target] = content
        manifest.append({'path': target, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)})
    destination = ROOT / 'artifacts' / f'marketing-agent-release-{datetime.now():%Y%m%d-%H%M%S}.zip'
    destination.parent.mkdir(exist_ok=True)
    prefix = 'marketing-agent/'
    with ZipFile(destination, 'x', ZIP_DEFLATED) as archive:
        for target, content in files.items():
            archive.writestr(prefix + target, content)
        archive.writestr(prefix + 'MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {prefix + name for name in files} | {prefix + 'MANIFEST.json'}
        for item in manifest:
            assert hashlib.sha256(archive.read(prefix + item['path'])).hexdigest() == item['sha256']
    result = {'archive': str(destination), 'files': len(files) + 1, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    (ROOT / 'artifacts/release-package-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
