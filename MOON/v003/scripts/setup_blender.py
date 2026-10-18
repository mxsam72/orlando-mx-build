"""Download and verify the exact Blender used for v003 native source exports."""
from pathlib import Path
import hashlib,os,shutil,tarfile,urllib.request
root=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'moon-v003-blender';root.mkdir(exist_ok=True)
name='blender-4.5.3-linux-x64';archive=root/(name+'.tar.xz')
if not archive.exists():
    with urllib.request.urlopen('https://download.blender.org/release/Blender4.5/'+archive.name,timeout=180) as src,archive.open('wb') as dst:shutil.copyfileobj(src,dst)
assert archive.stat().st_size==377397328
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845'
with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
exe=root/name/'blender';exe.chmod(exe.stat().st_mode|0o111)
if os.environ.get('GITHUB_ENV'):
    with open(os.environ['GITHUB_ENV'],'a') as out:out.write('BLENDER_V003='+str(exe)+'\n')
print('BLENDER_V003_VERIFIED',exe,flush=True)
