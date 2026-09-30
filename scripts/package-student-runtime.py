"""按明确清单生成内含课程共享配置的学员运行包。"""
import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'artifacts', 'docs', 'data'}
REQUIRED_CONFIG = {
    'DATABASE_URL', 'EMBEDDING_BASE_URL', 'EMBEDDING_API_KEY', 'EMBEDDING_MODEL',
    'EMBEDDING_DIMENSIONS', 'CHAT_BASE_URL', 'CHAT_API_KEY', 'CHAT_MODEL',
}


def checked_path(value: str, target: bool = False) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Unsafe package path: {value}')
    if target and any(part in FORBIDDEN_PARTS for part in path.parts):
        raise ValueError(f'Forbidden package target: {value}')
    return path


def main() -> None:
    env_path = ROOT / 'backend/.env'
    config = dotenv_values(env_path)
    missing = sorted(key for key in REQUIRED_CONFIG if not config.get(key))
    if missing:
        raise ValueError(f'backend/.env 缺少运行配置：{missing}')

    pairs = json.loads((ROOT / 'scripts/student-runtime-package-files.json').read_text(encoding='utf-8'))
    files: dict[str, bytes] = {}
    manifest = []
    for source, target in pairs:
        source_path = ROOT / checked_path(source)
        if not source_path.resolve().is_relative_to(ROOT) or not source_path.is_file():
            raise ValueError(f'Package source missing or outside workspace: {source}')
        target_name = str(checked_path(target, target=True))
        if target_name in files:
            raise ValueError(f'Duplicate package target: {target_name}')
        content = source_path.read_bytes()
        files[target_name] = content
        manifest.append({'path': target_name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)})

    secret_values = [str(config[key]).encode() for key in REQUIRED_CONFIG
                     if (key.endswith('API_KEY') or key == 'DATABASE_URL') and len(str(config[key])) >= 12]
    leaked = [name for name, content in files.items() if name != 'backend/.env'
              and any(secret in content for secret in secret_values)]
    if leaked:
        raise ValueError(f'运行凭据出现在 backend/.env 之外：{leaked}')

    markdown = [name for name in files if PurePosixPath(name).suffix.lower() == '.md']
    if markdown != ['README.md']:
        raise ValueError(f'学员包只允许一个 Markdown：{markdown}')
    if 'backend/.env' not in files or any(name.startswith(('docs/', 'data/')) for name in files):
        raise ValueError('学员包配置或内容边界不正确')

    destination = ROOT / 'artifacts' / f'marketing-agent-student-runtime-{datetime.now():%Y%m%d-%H%M%S}.zip'
    destination.parent.mkdir(exist_ok=True)
    prefix = 'marketing-agent/'
    with ZipFile(destination, 'x', ZIP_DEFLATED) as archive:
        for target, content in files.items():
            archive.writestr(prefix + target, content)
        archive.writestr(prefix + 'MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        names = set(archive.namelist())
        expected = {prefix + name for name in files} | {prefix + 'MANIFEST.json'}
        if names != expected:
            raise ValueError('ZIP file list mismatch')
        for item in manifest:
            if hashlib.sha256(archive.read(prefix + item['path'])).hexdigest() != item['sha256']:
                raise ValueError(f'ZIP checksum mismatch: {item["path"]}')

    result = {
        'archive': str(destination), 'files': len(files) + 1,
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'contains_runtime_config': True, 'markdown_files': markdown,
    }
    (ROOT / 'artifacts/student-runtime-package-check.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
