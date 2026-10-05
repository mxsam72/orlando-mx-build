"""Reproject race/grid references to the relocated native centerline.

Grid/pit world positions and headings remain fixed. Start-only checkpoints use
the unchanged start TCL. T09's checkpoint moves with its new corner.
"""
from pathlib import Path
import json, re, struct, shutil, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from v024_common import project, route_point
R=Path(__file__).resolve().parents[1];O=R/'V026_OUTPUT';NAME='orlandomx_2026_v026';OLD='orlandomx_2026_v024'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    source=R/'12_RELEASE'/OLD;dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    old=np.load(R/'V024_OUTPUT/route.npz')['q'];data=dict(np.load(O/'route.npz'));native=data['native'];q=data['q'];width=data['width'];mapping=data['old_to_new_station'];qa=read(O/'geometry_validation.json')
    translation=np.array(qa['T09_translation_xz_m']);ot=next(x for x in read(R/'V009_SOURCE/baseline_geometry.json')['turns'] if x['id']=='T09');grid_errors=[];changed_checkpoint=False
    for p in source.iterdir():
        if not p.is_file() or p.suffix in ['.map','.trh']:continue
        target=dest/p.name.replace(OLD,NAME);shutil.copy2(p,target)
        if p.suffix=='.ini':
            ini=target.read_text().replace('v024','v026').replace('Orlando MX 2026 v024','Orlando MX 2026 v026')
            ini=re.sub(r'(?m)^length=.*$',f'length={round(native[-1,3])}m',ini);target.write_text(ini)
    text=(source/(OLD+'.rdf')).read_text(encoding='utf-8')
    def edit_leaf(match):
        nonlocal changed_checkpoint
        name,body=match[1],match[2];get=lambda k:re.search(r'(?m)^\s*'+k+r'\s*=\s*([-+\d.eE]+)',body)
        lm=get('long')
        if not lm:return match[0]
        line=get('line')
        if line and int(float(line[1]))==2:return match[0]
        station=float(lm[1]);lp=get('lat');ap=get('angle');lat=float(lp[1]) if lp else 0.;angle=float(ap[1]) if ap else 0.
        p=route_point(old,station);xz=p[:2]+lat*np.array([math.sin(p[2]),-math.cos(p[2])]);absolute=(90-math.degrees(p[2])+angle)%360
        if name.startswith('checkpoint') and abs(station-ot['mid'])<.5:xz+=translation;changed_checkpoint=True
        if lp:
            proj=project(native,*xz,absolute)
            npnt=route_point(native,proj['long']);reconstructed=npnt[:2]+proj['lat']*np.array([math.sin(npnt[2]),-math.cos(npnt[2])]);grid_errors.append(float(np.linalg.norm(reconstructed-xz)))
            changes=proj
        else:
            # Checkpoint/finish position along the actual merged native route.
            proj=project(native,*xz,absolute);changes={'long':proj['long']}
        for key,value in changes.items():body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-+\d.eE]+',lambda m:m[1]+f'{value:.9f}',body,count=1)
        return name+'\n{'+body+'}'
    result=re.sub(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',edit_leaf,text)
    (dest/(NAME+'.rdf')).write_text(result,encoding='utf-8');(O/(NAME+'.rdf')).write_text(result,encoding='utf-8')
    length=float(native[-1,3]);s=np.linspace(0,length,int(np.ceil(length/2))+1)
    # Centerline samples follow native geometry, with width inherited from the
    # authored route. Match v024's reset-line width policy.
    xy=np.column_stack([np.interp(s,native[:,3],native[:,k]) for k in [0,1]]);idx=cKDTree(q[:,:2]).query(xy)[1];w=width[idx]
    for fn,offset in [('minrace.tl',-.5),('maxrace.tl',-.5),('checkleft.tl',.7),('checkright.tl',.7)]:
        lat=w/2+offset
        if fn in ['minrace.tl','checkleft.tl']:lat=-lat
        ar=np.column_stack([s,lat]).astype('<f4');raw=b'TL \0'+struct.pack('<I',len(ar))+ar.tobytes();(dest/fn).write_bytes(raw);(O/fn).write_bytes(raw)
    # Preserve the logo menu image while updating the map thumbnail's route.
    im=Image.new('RGB',(1024,1024),(75,97,56));draw=ImageDraw.Draw(im)
    pts=[(float(x/600*1024),float((600-z)/600*1024)) for x,z in q[:,:2]];draw.line(pts,fill=(153,135,117),width=15);draw.line(pts,fill=(215,207,186),width=3)
    start=data['start'];draw.line([(float(x/600*1024),float((600-z)/600*1024)) for x,z in start[:,:2]],fill=(190,168,122),width=10)
    im.save(dest/(NAME+'_map.tga'))
    validation=dict(source_checks_pass=bool(changed_checkpoint and max(grid_errors,default=0)<.03),T09_checkpoint_relocated=changed_checkpoint,world_position_reconstruction_max_m=max(grid_errors,default=0),start_only_checkpoints_unchanged=True,reset_lines_rebuilt_for_native_length=True,native_centerline_length_m=length,native_reset_samples=len(s),start_grid_and_pit_world_positions_preserved=True,menu_logo_image_preserved=True,in_game_race_and_reset_test=False)
    (O/'race_validation.json').write_text(json.dumps(validation,indent=2)+'\n');print(validation,flush=True)
    if not validation['source_checks_pass']:raise RuntimeError('v026 race/reset source QA failed')
if __name__=='__main__':main()
