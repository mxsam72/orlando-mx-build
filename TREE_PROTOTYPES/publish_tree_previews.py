"""Publish an explicitly labelled prototype review package, never a track build."""
import json,os,urllib.request,urllib.parse,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'output'
repo='mxsam72/orlando-mx-build';api='https://api.github.com/repos/'+repo
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-tree-prototype-review'}
def request(path,data=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(api+path,data=body,headers=headers|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
j=request('');assert j['id']==1368050549 and j['full_name']==repo and j['visibility']=='public'
qa=json.loads((O/'prototype_validation.json').read_text());assert qa['review_only'] and not qa['track_modified']
rel=request('/releases',dict(tag_name='tree-prototypes-'+os.environ['GITHUB_RUN_ID'],target_commitish=os.environ['GITHUB_SHA'],name='Orlando MX — realistic tree prototype review',draft=False,prerelease=True,make_latest='false',body='Two actual textured 3D tree prototypes for style approval: A airy pine; B dense evergreen woodland. Same-light Blender model renders, detail views, bike-height woodland views, orbit videos, editable source scene, FBX assets and reproducible scripts. The old generic example is reconstructed from the current builder. These are offline model previews, not MX Bikes screenshots. No track, dirt, geometry, scenery placement or gameplay files have been changed. Native shader, scale and performance validation remains pending after selection.'))
names=['Orlando_Tree_Prototypes_Review.zip','Orlando_Tree_Comparison.png','Orlando_Tree_Woodline_Comparison.png','Tree_A_Turntable.mp4','Tree_B_Turntable.mp4','A_front.png','B_front.png','A_detail.png','B_detail.png','A_side.png','B_side.png','prototype_validation.json','README_Tree_Prototypes.txt']
assets=[]
for name in names:
    p=O/name;url=rel['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':name})
    with p.open('rb') as stream:
        req=urllib.request.Request(url,data=stream,method='POST',headers=headers|{'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)})
        with urllib.request.urlopen(req,timeout=900) as response:asset=json.load(response)
    assert asset['size']==p.stat().st_size and asset['digest']=='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
    assets.append(dict(name=name,url=asset['browser_download_url'],bytes=asset['size'],sha256=asset['digest'].split(':')[1]))
    print('SAVED_TREE_PREVIEW',name,asset['size'],flush=True)
(O/'delivery.json').write_text(json.dumps(dict(release_id=rel['id'],url=rel['html_url'],commit=os.environ['GITHUB_SHA'],assets=assets),indent=2)+'\n')
print('TREE_REVIEW_RELEASE',rel['id'],rel['html_url'],flush=True)
