"""Inspect official CC0 source metadata and small actual FBX geometry samples."""
import urllib.request, json, base64, io
from PIL import Image,ImageDraw
from v044_common import *
from v044_source import blob
from v027_scenery import parse,values,child,vertices,geometry_records
from rebind_scenery import array
def main():
    metadata={}
    for asset in ['pine_tree_01','tree_small_02','grass_bermuda_01','raked_dirt','dirt','farm_soil','park_dirt','dense_sand','pine_bark','rough_wood','concrete_floor_worn_001']:
        url='https://api.polyhaven.com/files/'+asset
        req=urllib.request.Request(url,headers={'User-Agent':'OrlandoMX-v044-asset-research'})
        with urllib.request.urlopen(req,timeout=120) as r:metadata[asset]=json.load(r)
    save(R/'DOCUMENTATION/v044_asset_options.json',metadata)
    print('CODEX_V044_ASSET_OPTIONS_BLOB '+blob(json.dumps(metadata)),flush=True)
    nodes,_=parse((BASE/'scenery.fbx').read_bytes());records=geometry_records(nodes)
    names=['tree_1','tree_10']+[n for n in records if 'bathroom' in n][:4]
    parts=[]
    for name in names:
        g,mid=records[name]
        uv=child(g,b'LayerElementUV');mat=child(g,b'LayerElementMaterial')
        parts.append(dict(name=name,vertices=vertices(g).round(6).tolist(),polygon_indices=array(child(g,b'PolygonVertexIndex')).astype(int).tolist(),
             uv=array(child(uv,b'UV')).reshape(-1,2).round(6).tolist(),uv_indices=array(child(uv,b'UVIndex')).astype(int).tolist(),
             material_indices=array(child(mat,b'Materials')).astype(int).tolist()))
    print('CODEX_V044_SAMPLE_GEOMETRY_BLOB '+blob(json.dumps(parts)),flush=True)
if __name__=='__main__':main()
