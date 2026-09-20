"""Restore the exact checked inputs used by the Windows native build."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'BUILD_INPUTS/manifest.json').read_text())
    pieces = []
    for item in manifest['parts']:
        data = (ROOT / item['path']).read_bytes()
        if len(data) != item['bytes'] or sha256(data) != item['sha256']:
            raise RuntimeError('Input part failed integrity check: ' + item['path'])
        pieces.append(data)
    archive = b''.join(pieces)
    if len(archive) != manifest['archive_bytes'] or sha256(archive) != manifest['archive_sha256']:
        raise RuntimeError('Combined input archive failed integrity check')
    expected = {item['path']: item for item in manifest['files']}
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        if set(source.namelist()) != set(expected):
            raise RuntimeError('Archive members differ from the input manifest')
        for name in source.namelist():
            target = (ROOT / name).resolve()
            if not target.is_relative_to(ROOT):
                raise RuntimeError('Unsafe input path: ' + name)
            data = source.read(name)
            item = expected[name]
            if len(data) != item['bytes'] or sha256(data) != item['sha256']:
                raise RuntimeError('Input file failed integrity check: ' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    print('Restored and verified', len(expected), 'native input files.', flush=True)

    # v007 is an integrity-checked overlay on the immutable v006 native inputs.
    patch_path = ROOT / 'BUILD_V007/manifest.json'
    if patch_path.exists():
        patch = json.loads(patch_path.read_text())
        parts = []
        for item in patch['parts']:
            data = (ROOT / item['path']).read_bytes()
            if len(data) != item['bytes'] or sha256(data) != item['sha256']:
                raise RuntimeError('v007 patch part failed integrity: ' + item['path'])
            parts.append(data)
        archive = b''.join(parts)
        if sha256(archive) != patch['archive_sha256']:
            raise RuntimeError('v007 patch archive failed integrity')
        expected = {x['path']:x for x in patch['files']}
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            if set(source.namelist()) != set(expected):
                raise RuntimeError('v007 patch file list mismatch')
            for name in source.namelist():
                target = (ROOT / name).resolve()
                if not target.is_relative_to(ROOT):
                    raise RuntimeError('Unsafe v007 patch path')
                data = source.read(name)
                if len(data) != expected[name]['bytes'] or sha256(data) != expected[name]['sha256']:
                    raise RuntimeError('v007 patch file failed integrity: ' + name)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
        from apply_scenery_patch import main as update_scenery
        update_scenery()
        print('Restored and verified',len(expected),'v007 overlay inputs.',flush=True)


if __name__ == '__main__':
    main()


