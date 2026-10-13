"""Pinned delivered baseline and approved tree assets for v047."""
from pathlib import Path
import hashlib,json

R=Path(__file__).resolve().parents[1]
BASE=R/'V044_OUTPUT'
DIRT=R/'V046_OUTPUT'
TREES=R/'BUILD/v047_approved_trees'
O=R/'V047_OUTPUT'
F=O/'facility_textures'
P=R/'BUILD/v047_stage'
NAME='orlandomx_2026_v047'
DEST=R/'12_RELEASE'/NAME

def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

PINNED_ASSETS={
    'OrlandoMX-v044-source-checkpoint.zip':dict(release=411058375,tag='untagged-281f90b2ce09d3a57800',bytes=1599713927,sha256='1c45844424b0f8e9384a9344f0563b6f108e5003f699c71430dc499166bff881'),
    'OrlandoMX-v046-dirt-source-checkpoint.zip':dict(release=411710729,tag='v046-persistent-dirt-38405384917',bytes=304060299,sha256='ee9f0d2475865f437ac321379708226f3950129bb8901c5c64a1a253a1ee2a8d'),
    'OrlandoMX_v046_Validation.json':dict(release=411710729,tag='v046-persistent-dirt-38405384917',bytes=35757,sha256='137d601415687f7231c46d2b98c29076bd179a8edce8c21130d9fb9ea8868a0b'),
    'OrlandoMX_2026_v046.pkz':dict(release=411710729,tag='v046-persistent-dirt-38405384917',bytes=913440044,sha256='e8452f4ec9fdeed81139a1eb6e52f1881b7d49e5cd32788f1de63aa0c1dc76bb'),
    'Orlando_Tree_Prototypes_Review.zip':dict(release=412025003,tag='tree-prototypes-38452888621',bytes=168626751,sha256='d5d46497967c1ca2c2d9cc158a9438f04d1f2f81d3592e123c93d6c5413ea147')
}
TREE_SHA={
    'A':'f665b82bdca8242fdc254915aa9481df0cd294b202fbd6ffc3fc7d5a451fdef8',
    'B':'0793db41ac0cdcf502809df2302d46c5fc8c208bbbe96b3713fec03d7855d94f'
}
SCENERY_SHA='111af7d07ea3f3fb0e1ac6f3d50d1904977d0e41c0615caa0bcc5912429f49f7'
TERRAIN_SHA='f6ce21f9b1a0ff4ca3a822d92dcba5904eeea860cd95952bd4ba44ac9cb5c4b9'
