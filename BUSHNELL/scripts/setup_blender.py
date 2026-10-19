"""Install the pinned Blender export tool, with verified mirror fallback."""
from pathlib import Path
import hashlib
import os
import shutil
import tarfile
import urllib.error
import urllib.request

NAME = 'blender-4.5.3-linux-x64'
SIZE = 377397328
SHA256 = '975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845'
URLS = tuple(base + NAME + '.tar.xz' for base in (
    'https://mirror.blender.org/release/Blender4.5/',
    'https://mirrors.ocf.berkeley.edu/blender/release/Blender4.5/',
    'https://download.blender.org/release/Blender4.5/',
))


def verify(path):
    if path.stat().st_size != SIZE:
        raise ValueError('Blender archive size mismatch')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != SHA256:
            raise ValueError('Blender archive SHA256 mismatch')


def download(archive):
    if archive.is_file():
        try:
            verify(archive)
            return
        except ValueError:
            archive.unlink()
    partial = archive.with_suffix(archive.suffix + '.part')
    failures = []
    for url in URLS:
        try:
            print('BLENDER_DOWNLOAD', url, flush=True)
            request = urllib.request.Request(url, headers={'User-Agent': 'BushnellTrackBuild/1.0'})
            with urllib.request.urlopen(request, timeout=180) as src, partial.open('wb') as dst:
                shutil.copyfileobj(src, dst)
            verify(partial)
            partial.replace(archive)
            return
        except (OSError, ValueError, urllib.error.URLError) as exc:
            failures.append(f'{url}: {exc}')
            print('BLENDER_DOWNLOAD_REJECTED', failures[-1], flush=True)
        finally:
            partial.unlink(missing_ok=True)
    raise RuntimeError('No verified Blender download: ' + '; '.join(failures))


def main():
    root = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'bushnell-blender'
    root.mkdir(parents=True, exist_ok=True)
    archive = root / (NAME + '.tar.xz')
    download(archive)
    with tarfile.open(archive) as tar:
        tar.extractall(root, filter='data')
    exe = root / NAME / 'blender'
    exe.chmod(exe.stat().st_mode | 0o111)
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'], 'a') as out:
            out.write('BUSHNELL_BLENDER=' + str(exe) + '\n')
    print('BUSHNELL_BLENDER_VERIFIED', exe, flush=True)


if __name__ == '__main__':
    main()
