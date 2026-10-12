"""Hash-checked CC0 photographic assets downloaded from official Poly Haven metadata."""
import urllib.request,time,hashlib
from PIL import Image
from v044_common import *
CACHE=R/'BUILD/v044_assets'
PROVENANCE=[]
def get(entry,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or hashlib.md5(path.read_bytes()).hexdigest()!=entry['md5']:
        for attempt in range(4):
            try:
                req=urllib.request.Request(entry['url'],headers={'User-Agent':'OrlandoMX-v044-CC0-authoring'})
                with urllib.request.urlopen(req,timeout=240) as r:atomic(path,r.read())
                assert path.stat().st_size==entry['size'] and hashlib.md5(path.read_bytes()).hexdigest()==entry['md5'];break
            except Exception:
                if attempt==3:raise
                time.sleep(2+attempt)
    PROVENANCE.append(dict(url=entry['url'],file=str(path.relative_to(R)),md5=entry['md5'],sha256=sha(path),license='CC0',provider='Poly Haven'))
    return path

def metadata(asset):
    p=CACHE/(asset+'_metadata.json')
    if not p.exists():
        req=urllib.request.Request('https://api.polyhaven.com/files/'+asset,headers={'User-Agent':'OrlandoMX-v044'})
        with urllib.request.urlopen(req,timeout=120) as r:atomic(p,r.read())
    return read(p)

def material(asset,kind,res='2k'):
    entry=metadata(asset)[kind][res];fmt='png' if 'png' in entry else 'jpg'
    return Image.open(get(entry[fmt],CACHE/asset/(kind+'_'+res+'.'+fmt)))

def model(asset):
    m=metadata(asset)['gltf']['1k']['gltf'];p=get(m,CACHE/asset/(asset+'.gltf'))
    for name,e in m['include'].items():get(e,p.parent/name)
    return p

def finish():save(O/'v044_asset_provenance.json',PROVENANCE)
