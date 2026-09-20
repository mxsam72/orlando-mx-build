#!/usr/bin/env python3
"""Reshape v006 jumps while preserving its route, surroundings and exact source RAW.

All dimensions are authoring choices, not surveyed Orlando measurements.
This performs geometry QA only; the game and rider must validate the result.
"""
from pathlib import Path
import hashlib, json, math, shutil
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates, gaussian_filter
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
N, SIZE, SCALE = 2049, 600., 18.
SOURCE = ROOT / 'V007_SOURCE'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def smooth(u):
    u = np.clip(u, 0, 1)
    return u*u*(3-2*u)

def smoother(u):
    u = np.clip(u, 0, 1)
    return u**3*(10-15*u+6*u*u)

def add_grade_segment(xs, hs, ds, length, g0, g1):
    """Integrate an eased grade. Both endpoint curvature values are zero."""
    t = np.linspace(0, 1, max(2, math.ceil(length/.20)+1))[1:]
    start, height = xs[-1], hs[-1]
    xs.extend((start+length*t).tolist())
    hs.extend((height+length*(g0*t+(g1-g0)*(t**3-.5*t**4))).tolist())
    ds.extend((g0+(g1-g0)*smooth(t)).tolist())

def tabletop(old, angle, deck, down_grade, shift=0):
    crest = old['height_m']+.15
    grade = math.tan(math.radians(angle))
    rollover = 2.4 if crest >= 2.2 else 2.7
    lip_height = crest-grade*rollover/2
    # A curved toe followed by at least 1.5 m at the takeoff grade.
    toe = min(5.2, max(3.0, 2*(lip_height/grade-1.5)))
    face = lip_height/grade+toe/2
    assert face-toe >= 1.49
    xs, hs, ds = [-face-2, -face], [0.,0.], [0.,0.]
    add_grade_segment(xs,hs,ds,toe,0,grade)
    add_grade_segment(xs,hs,ds,face-toe,grade,grade)
    add_grade_segment(xs,hs,ds,rollover,grade,0)
    add_grade_segment(xs,hs,ds,deck,0,0)
    land_entry, runout = 2.4, 4.2
    linear = crest/down_grade-(land_entry+runout)/2
    assert linear > 1
    add_grade_segment(xs,hs,ds,land_entry,0,-down_grade)
    add_grade_segment(xs,hs,ds,linear,-down_grade,-down_grade)
    add_grade_segment(xs,hs,ds,runout,-down_grade,0)
    hs[-1] = 0.
    add_grade_segment(xs,hs,ds,2,0,0)
    return dict(id=old['id'],kind='tabletop',lip_s=old['lip_s']+shift,
                previous_lip_s=old['lip_s'],height_m=lip_height,crest_height_m=crest,
                face_m=face,top_m=deck,landing_m=land_entry+linear+runout,
                toe_transition_m=toe,lip_rollover_m=rollover,landing_runout_m=runout,
                takeoff_angle_deg=angle,landing_angle_deg=math.degrees(math.atan(down_grade)),
                profile_s=xs,profile_h=hs,profile_derivative=ds,
                status='v007 estimated geometry; game riding validation required')

def roller(old):
    # The crest has zero grade and curvature on both sides, with no short flat table.
    crest = old['height_m']+.15
    rise, fall = float(old['face_m']), float(old['landing_m'])
    xs, hs, ds = [-rise-2,-rise], [0.,0.], [0.,0.]
    up, down = 2*crest/rise, 2*crest/fall
    add_grade_segment(xs,hs,ds,rise/2,0,up)
    add_grade_segment(xs,hs,ds,rise/2,up,0)
    add_grade_segment(xs,hs,ds,fall/2,0,-down)
    add_grade_segment(xs,hs,ds,fall/2,-down,0)
    hs[-1] = 0.
    add_grade_segment(xs,hs,ds,2,0,0)
    return dict(id=old['id'],kind='roller',lip_s=old['lip_s']+1.2,
                previous_lip_s=old['lip_s'],height_m=crest,crest_height_m=crest,
                face_m=rise,top_m=0,landing_m=fall,
                takeoff_angle_deg=math.degrees(math.atan(up)),
                landing_angle_deg=math.degrees(math.atan(down)),
                profile_s=xs,profile_h=hs,profile_derivative=ds,
                status='Rounded low crest; estimated geometry; game riding validation required')

def make_profiles(old):
    # Small rises remain rollers. The two short runouts get earlier lips.
    tables = {
        'J01':(23,6,.27,0), 'J02':(20,3.5,.25,0),
        'J04':(24,7,.28,0), 'J06':(25,4.5,.30,-5),
        'J08a':(19,3,.24,0), 'J08b':(23,5.5,.28,0),
        'J09b':(22,3.5,.28,0), 'J10a':(20,3,.25,0),
        'J10b':(23,4.5,.28,0), 'J11b':(24,5.5,.29,0),
        'J12b':(23,4,.30,-8),
    }
    return [tabletop(j,*tables[j['id']]) if j['id'] in tables else roller(j) for j in old]

def supports(jumps,q,w):
    total=q[-1,3]; result=[]
    for j in jumps:
        s=np.linspace(j['lip_s']+j['profile_s'][0]-3,j['lip_s']+j['profile_s'][-1]+3,300)
        p=np.c_[np.interp(s%total,q[:,3],q[:,0]),np.interp(s%total,q[:,3],q[:,1])]
        th=np.interp(s%total,q[:,3],q[:,2]);width=np.interp(s%total,q[:,3],w)
        f=CubicHermiteSpline(j['profile_s'],j['profile_h'],j['profile_derivative'])
        result.append((j,s,p,th,width,cKDTree(p),f))
    return result

def envelope(pts,items):
    output=np.zeros(len(pts))
    for j,s,p,th,width,tree,f in items:
        box=(pts[:,0]>p[:,0].min()-15)&(pts[:,0]<p[:,0].max()+15)&(pts[:,1]>p[:,1].min()-15)&(pts[:,1]<p[:,1].max()+15)
        if not box.any():continue
        _,i=tree.query(pts[box]);d=pts[box]-p[i]
        along=d[:,0]*np.cos(th[i])+d[:,1]*np.sin(th[i])
        lat=-d[:,0]*np.sin(th[i])+d[:,1]*np.cos(th[i])
        x=s[i]+along-j['lip_s']
        y=f(np.clip(x,j['profile_s'][0],j['profile_s'][-1]))
        y*=1-smooth((abs(lat)-width[i]/2+.25)/7)
        output[box]=np.maximum(output[box],np.maximum(y,0))
    return output

def main():
    SOURCE.mkdir(exist_ok=True)
    baseline=ROOT/'BUILD/v006_terrain.raw'
    expected=next(x['sha256'] for x in json.loads((ROOT/'BUILD_INPUTS/manifest.json').read_text())['files'] if x['path']=='02_HEIGHTMAP/terrain.raw')
    if not baseline.exists():
        assert sha(ROOT/'02_HEIGHTMAP/terrain.raw')==expected,'Restore v006 native inputs before reshaping.'
        shutil.copy2(ROOT/'02_HEIGHTMAP/terrain.raw',baseline)
    assert sha(baseline)==expected
    for a,b in [('02_HEIGHTMAP/jump_profiles.json','v006_jump_profiles.json'),('01_GIS_AERIAL/route.npz','route.npz'),('01_GIS_AERIAL/geometry.json','geometry.json')]:
        if not (SOURCE/b).exists():shutil.copy2(ROOT/a,SOURCE/b)
    old=json.loads((SOURCE/'v006_jump_profiles.json').read_text())
    new=make_profiles(old)
    d=np.load(SOURCE/'route.npz');q=d['q'];w=d['width'];tree=cKDTree(q[:-1,:2])
    H=np.fromfile(baseline,dtype='<u2').reshape(N,N).astype(float)/65535*SCALE
    base=H.copy();old_support=supports(old,q,w);new_support=supports(new,q,w)
    axes=np.linspace(0,SIZE,N);blend=np.zeros_like(H)
    for row in range(0,N,48):
        zz,xx=np.meshgrid(SIZE-axes[row:row+48],axes,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()]
        dist,i=tree.query(pts,workers=2)
        # Rebuild the full earthen support, including its seven-metre shoulders.
        # Trackside scenery is rebound to this terrain in a separate FBX patch.
        weight=(dist < w[i]/2-.15).astype(float)
        delta=envelope(pts,new_support)-envelope(pts,old_support)
        H[row:row+len(xx)]+=delta.reshape(xx.shape)
        blend[row:row+len(xx)]=weight.reshape(xx.shape)
        if row%384==0:print('jump terrain row',row,flush=True)
    ideal=H.copy();passes=0
    changed=abs(H-base)>.001
    for _ in range(32):
        dy,dx=np.gradient(H,SIZE/(N-1))
        bad=(np.hypot(dx,dy)>.70)&(blend>.5)&changed
        if not bad.any():break
        weight=np.clip(gaussian_filter(bad.astype(float),2)*6,0,1)
        H=H*(1-weight)+gaussian_filter(H,2)*weight
        passes+=1
    raw=np.round(H/SCALE*65535).astype('<u2')
    raw.tofile(ROOT/'02_HEIGHTMAP/terrain.raw')
    Image.fromarray(raw).save(ROOT/'02_HEIGHTMAP/terrain_16bit.png')
    H=raw.astype(float)/65535*SCALE
    np.save(ROOT/'02_HEIGHTMAP/height_metres.npy',H.astype(np.float32))
    (ROOT/'02_HEIGHTMAP/jump_profiles.json').write_text(json.dumps(new,indent=2)+'\n')
    elev=map_coordinates(H,[(SIZE-q[:,1])/SIZE*(N-1),q[:,0]/SIZE*(N-1)],order=1)
    np.savetxt(ROOT/'02_HEIGHTMAP/centerline_elevation.csv',np.c_[q[:,3],elev],delimiter=',',header='source_s_m,height_m',comments='')
    scene=json.loads((ROOT/'07_OBJECTS_SOURCE/scene_spec.json').read_text());scene['jumps']=new
    (ROOT/'07_OBJECTS_SOURCE/scene_spec.json').write_text(json.dumps(scene,indent=2)+'\n')
    dy,dx=np.gradient(H,SIZE/(N-1))
    qa=dict(version='v007',baseline_raw_sha256=expected,raw_sha256=sha(ROOT/'02_HEIGHTMAP/terrain.raw'),
            raw_bytes=raw.nbytes,raw_png_identical=bool(np.array_equal(raw,np.array(Image.open(ROOT/'02_HEIGHTMAP/terrain_16bit.png')))),
            obstacles=len(new),tabletops=sum(j['kind']=='tabletop' for j in new),rollers=sum(j['kind']=='roller' for j in new),
            maximum_riding_area_grade=float(np.hypot(dx,dy)[blend>.01].max()),
            height_range_m=[float(H.min()),float(H.max())],changed_nodes=int(np.count_nonzero(abs(H-base)>.0002)),
            maximum_raise_m=float((H-base).max()),maximum_lower_m=float((base-H).max()),
            local_grade_relaxation_passes=passes,
            local_grade_relaxation_max_height_change_m=float(abs(H-ideal).max()),
            layout_changed=False,native_compilation=False,in_game_riding=False)
    assert qa['maximum_riding_area_grade']<.80
    assert qa['raw_png_identical'] and np.isfinite(H).all() and H.min()>0 and H.max()<SCALE
    (ROOT/'DOCUMENTATION/v007_terrain_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2),flush=True)

if __name__=='__main__':main()
