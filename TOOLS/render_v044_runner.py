"""Read-only previews from the authenticated, saved v044 checkpoint."""
import base64,json,os,subprocess,sys,zipfile
from pathlib import Path
from v044_common import R,sha,read,atomic
from v044_source import api,download,blob

RELEASE_ID=410822890
CHECKPOINT_SHA256='13bdf7ab83c4d5fe3b12e75132abfd8e0b2760d0311cb14f5647a7e8c6baa066'
CHECKPOINT_BYTES=1599713588
SCENERY_SHA256='111af7d07ea3f3fb0e1ac6f3d50d1904977d0e41c0615caa0bcc5912429f49f7'
TERRAIN_SHA256='f6ce21f9b1a0ff4ca3a822d92dcba5904eeea860cd95952bd4ba44ac9cb5c4b9'

def main():
    assert api('')['private']
    release=api('/releases/'+str(RELEASE_ID))
    assert release['draft'] and release['target_commitish']=='238a193dabefa3bd95c647e70b69abe15baa109a'
    assets={a['name']:a for a in release['assets']}
    asset=assets['OrlandoMX-v044-source-checkpoint.zip']
    assert asset['size']==CHECKPOINT_BYTES and asset['digest']=='sha256:'+CHECKPOINT_SHA256
    checkpoint=R/'BUILD/v044-preview-source.zip'
    download(asset,checkpoint)
    assert sha(checkpoint)==CHECKPOINT_SHA256
    with zipfile.ZipFile(checkpoint) as z:
        for item in z.infolist():
            path=Path(item.filename)
            assert not path.is_absolute() and '..' not in path.parts
            if not item.is_dir() and item.filename.startswith('V044_OUTPUT/'):
                atomic(R/item.filename,z.read(item))
    checkpoint.unlink()
    out=R/'V044_OUTPUT'
    assert sha(out/'scenery.fbx')==SCENERY_SHA256 and sha(out/'terrain.raw')==TERRAIN_SHA256
    assert read(out/'v044_source_validation.json')['checks_pass']
    print('Exact saved v044 source authenticated; PKZ build untouched.',flush=True)
    subprocess.run([sys.executable,str(R/'TOOLS/render_v044_previews.py'),'--width','2560','--height','1440'],cwd=R,check=True)
    manifest=read(R/'DOCUMENTATION/v044_renders/manifest.json')
    assert manifest['track_sources_unchanged']
    manifest['source_release_id']=RELEASE_ID
    manifest['source_checkpoint_sha256']=CHECKPOINT_SHA256
    for row in manifest['renders']:
        image=R/'DOCUMENTATION/v044_renders/images'/row['filename']
        assert sha(image)==row['sha256']
        row['image_base64_blob_sha']=blob(base64.b64encode(image.read_bytes()).decode('ascii'))
        print('CODEX_V044_RENDER_IMAGE '+row['filename']+' '+row['image_base64_blob_sha'],flush=True)
    print('CODEX_V044_RENDER_MANIFEST_BLOB '+blob(json.dumps(manifest)),flush=True)
    print('Actual-source previews complete. Native rendering confirmation remains pending.',flush=True)
if __name__=='__main__':main()
