"""Restore and authenticate the real v043 release before v044 authoring."""
import os, json, urllib.request, urllib.error, zipfile, shutil
from v044_common import *
API='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
HEADERS={'Authorization':'Bearer '+os.environ['V044_RELEASE_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-v044-build'}
def api(path,data=None):
    body=None if data is None else json.dumps(data).encode()
    headers=HEADERS|({'Content-Type':'application/json'} if body else {})
    with urllib.request.urlopen(urllib.request.Request(API+path,data=body,headers=headers),timeout=180) as r:return json.load(r)
def download(asset,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(asset['url'],headers=HEADERS|{'Accept':'application/octet-stream'})
    h=hashlib.sha256();count=0
    with urllib.request.urlopen(req,timeout=300) as response,path.open('wb') as out:
        while b:=response.read(4*1024*1024):out.write(b);h.update(b);count+=len(b)
    assert count==asset['size'] and h.hexdigest()==asset['digest'].removeprefix('sha256:')
def blob(text):return api('/git/blobs',{'content':text,'encoding':'utf-8'})['sha']
def main():
    cfg=read(S/'visual_spec.json');assert api('')['private']
    rel=api('/releases/'+str(cfg['baseline_release_id']))
    assert rel['draft'] and rel['target_commitish']==cfg['baseline_source_commit']
    assets={a['name']:a for a in rel['assets']}
    a=assets['OrlandoMX-v043-source-checkpoint.zip']
    assert a['size']==cfg['baseline_checkpoint_bytes'] and a['digest']=='sha256:'+cfg['baseline_checkpoint_sha256']
    p=R/'BUILD/v044-delivered-v043.zip';download(a,p)
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        for i in z.infolist():
            n=i.filename
            if i.is_dir():continue
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            keep=n.startswith(('V043_OUTPUT/','V043_SOURCE/','V024_OUTPUT/'))
            keep|=n.startswith('12_RELEASE/orlandomx_2026_v043/') and not n.endswith('.map')
            if keep:atomic(R/n,z.read(i))
    p.unlink()
    a=assets['OrlandoMX_v043_Validation.json']
    assert a['digest']=='sha256:'+cfg['baseline_validation_sha256']
    path=R/'BUILD/v044_baseline_native_validation.json';download(a,path);qa=read(path)
    assert qa['compiled'] and qa['centerline_merged'] and qa['source_checks']
    assert qa['source_commit']==cfg['baseline_source_commit']
    for k in ['independent_source_checks','staging_validation','object_texture_validation','native_coordinate_validation']:assert qa[k]['checks_pass'],k
    assert qa['pkz_bytes']==cfg['baseline_pkz_bytes'] and qa['pkz_sha256']==cfg['baseline_pkz_sha256']
    assert sha(BASE/'scenery.fbx')==qa['source_validation']['scenery_sha256']
    assert sha(BASE/'terrain.raw')==qa['source_validation']['terrain_sha256']
    print('Delivered v043 source and native validation authenticated. Standard-weather v044 has no 500 MB cap.',flush=True)
if __name__=='__main__':main()
