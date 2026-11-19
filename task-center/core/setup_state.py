"""Initialize local installation state without registering or starting services."""
import argparse
import json
import os
import tempfile
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def atomic_write(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def initialize(root, repository, python):
    root, repository, python = map(Path, (root, repository, python))
    registry = root / 'services.json'
    installation = root / 'installation.json'
    # Validate before any writes; never turn corrupt local state into an empty list.
    existing = read(registry) if registry.exists() else []
    if not isinstance(existing, list) or any(
        not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip()
        for row in existing
    ):
        raise ValueError('services.json must be a list of named service instances; existing file preserved')
    ids = [row['id'] for row in existing]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate service IDs in services.json; existing file preserved')
    settings = read(installation) if installation.exists() else {}
    if not isinstance(settings, dict):
        raise ValueError('installation.json must be an object; existing file preserved')
    previous = settings.get('root')
    if previous and Path(previous).resolve() != repository.resolve() and existing:
        raise ValueError('Repository moved with registered services. Update their absolute paths before switching installations.')
    root.mkdir(parents=True, exist_ok=True)
    for name in ('instances', 'runtime', 'setup-examples'):
        (root / name).mkdir(exist_ok=True)
    if not registry.exists():
        atomic_write(registry, [])
    settings.update(root=str(repository.resolve()), python=str(python.resolve()))
    atomic_write(installation, settings)
    # Examples are drafts outside the active registry. Never overwrite user edits.
    for source in (repository / 'examples').glob('*.json'):
        target = root / 'setup-examples' / source.name
        if target.exists():
            continue
        def localize(value):
            if isinstance(value, dict):
                return {key: localize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [localize(item) for item in value]
            if not isinstance(value, str):
                return value
            return (value.replace('F:/Development/research/agent-skills', repository.resolve().as_posix())
                    .replace('C:/Users/YOU', root.parent.resolve().as_posix())
                    .replace('C:/Python/pythonw.exe', python.with_name('pythonw.exe').resolve().as_posix())
                    .replace('C:/Python/python.exe', python.resolve().as_posix()))
        # Resolve project paths/identities manually; examples are not activated.
        atomic_write(target, localize(read(source)))
    return dict(registry=str(registry), instances=len(existing), examples=str(root / 'setup-examples'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--running', choices=('gui', 'supervise'))
    args = parser.parse_args()
    if args.running:
        import psutil
        entry = os.path.normcase(str((args.repository/'task-center/orbit.py').resolve()))
        for process in psutil.process_iter(['name']):
            try:
                if (process.info['name'] or '').lower() not in ('python.exe', 'pythonw.exe'):
                    continue
                argv = process.cmdline()
                if args.running not in argv:
                    continue
                if any(os.path.normcase(os.path.abspath(os.path.join(process.cwd(), arg))) == entry for arg in argv[1:] if arg.endswith('.py')):
                    print('yes')
                    return
            except (psutil.Error, OSError):
                continue
        print('no')
        return
    if not args.python:
        parser.error('--python is required when initializing')
    print(json.dumps(initialize(Path.home()/'.orbit', args.repository, args.python), ensure_ascii=True))


if __name__ == '__main__':
    main()
