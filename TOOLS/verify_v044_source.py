"""Independent source preservation and native input validation."""
import re
from PIL import Image
from v044_common import *
from v027_scenery import parse,values,geometry_records,fingerprint,vertices
from v028_materials import layer_blocks

def main():
    qa=read(O/'v044_scenery_validation.json');surface=read(O/'v044_surface_validation.json');assert qa['checks_pass'] and surface['checks_pass']
    for name in ['terrain.raw','start.tcl','main.tcl','route.npz','v024_pit_gravel.tga']:assert sha(O/name)==sha(BASE/name),name
    for p in (BASE/'masks').rglob('*'):
        if p.is_file():assert sha(p)==sha(O/'masks'/p.relative_to(BASE/'masks')),p.name
    old=parse((BASE/'scenery.fbx').read_bytes())[0];new=parse((O/'scenery.fbx').read_bytes())[0]
    obj=lambda ns:{values(n)[0]:n for n in next(n for n in ns if n['name']==b'Objects')['children']}
    before=obj(old);after=obj(new);allowed=set(qa['removed_tree_record_ids']+qa['modified_embedded_texture_record_ids'])
    assert all(i in after and fingerprint(n)==fingerprint(after[i]) for i,n in before.items() if i not in allowed)
    rec=geometry_records(new);oldrec=geometry_records(old)
    assert all(name.startswith('tree_') for name,(g,mid) in oldrec.items() if name not in rec)
    for name,(g,mid) in oldrec.items():
        if not name.startswith('tree_'):assert name in rec and fingerprint(g)==fingerprint(rec[name][0]),name
    for name,(g,mid) in rec.items():
        if name not in oldrec:assert name.startswith('v044_'),name
    text=(O/'compiled_track.hmf').read_text();assert len(layer_blocks(text))==11 and 'mask_v044_route_detail.tga' in text
    for path in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',text):assert (M/path).exists() or (O/path).exists() or (O/'masks'/path.removeprefix('mask_')).exists() or path=='basemap.tga',path
    altered=qa['photographic_texture_updates'];protected=[]
    for p in (BASE/'facility_textures').glob('*.tga'):
        if p.name not in altered:assert sha(p)==sha(F/p.name),p.name;protected.append(p.name)
    textures=[]
    for folder in [M,F]:
        for p in folder.glob('*.tga'):
            with Image.open(p) as im:w,h=im.size
            assert w>0 and h>0 and not w&(w-1) and not h&(h-1),p.name
            textures.append(dict(file=p.name,size=[w,h],sha256=sha(p)))
    save(O/'v044_source_validation.json',dict(checks_pass=True,version='v044',baseline_version='v043',baseline_source_commit=read(S/'visual_spec.json')['baseline_source_commit'],terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),physics_masks_exact=True,race_route_and_start_inputs_exact=True,all_personalized_assets_and_collision_geometry_exact=True,all_artwork_uv_geometry_exact=True,protected_artwork_textures=protected,textures=textures,weather_focus='standard dry weather',package_size_cap_removed=True,in_game_visual_check=False,performance_test=False))
    print('Independent preservation checks passed: MX geometry, race data, road collision and personal assets exact.',flush=True)
if __name__=='__main__':main()
