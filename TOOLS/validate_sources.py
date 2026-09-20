#!/usr/bin/env python3
"""Check actual source consistency; this is not native or in-game validation."""
from pathlib import Path
import math,json,re,struct,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
ROOT=Path(__file__).resolve().parents[1];NAME='orlandomx_2026_v007'
def main():
    info=json.loads((ROOT/'01_GIS_AERIAL/geometry.json').read_text());d=np.load(ROOT/'01_GIS_AERIAL/route.npz');q=d['q'];w=d['width'];sa=d['start'];L=info['model_lap_length_m'];cut=0.
    h=np.fromfile(ROOT/'02_HEIGHTMAP/terrain.raw',dtype='<u2').reshape(2049,2049);height=h/65535*18
    results={'heightmap_bytes':h.nbytes,'raw_png_match':bool(np.array_equal(h,np.asarray(Image.open(ROOT/'02_HEIGHTMAP/terrain_16bit.png')))),'height_range_m':[float(height.min()),float(height.max())]}
    assert results['raw_png_match'] and h.nbytes==8396802
    # Decode native centerline using its documented coordinate convention.
    text=(ROOT/'09_TRACKED/main.tcl').read_text();head=text.split('segment0')[0]
    vals=dict(re.findall(r'^(\w+)\s*=\s*([^\n]+)',head,re.M));x,z=float(vals['x']),float(vals['z']);theta=math.radians(90-float(vals['angle']));s=0;points=[]
    for _,body in re.findall(r'segment(\d+)\s*\{([^}]+)\}',text,re.S):
        v=dict(re.findall(r'(\w+)\s*=\s*([^\n]+)',body));typ=int(v['type']);length=float(v['length']);radius=float(v['radius']);ang=float(v['angle']);p0=np.array([x,z]);oldth=theta
        for f in np.linspace(0,1,20):
            if typ==0:p=p0+np.array([math.cos(oldth),math.sin(oldth)])*length*f;th=oldth
            else:
                sign=-np.sign(radius);th=oldth+sign*math.radians(ang)*f;c=p0+sign*abs(radius)*np.array([-math.sin(oldth),math.cos(oldth)]);p=c-sign*abs(radius)*np.array([-math.sin(th),math.cos(th)])
            source=(s+f*length+cut)%L;expected=np.array([np.interp(source,q[:,3],q[:,k]) for k in range(2)]);points.append(float(np.linalg.norm(p-expected)))
        x,z=p;theta=th;s+=length
    results['native_centerline_length_m']=s;results['centerline_source_difference_max_m']=max(points);results['native_centerline_closure_m']=float(np.linalg.norm(np.array([x,z])-info['native_origin_xz']))
    assert abs(s-L)<.001 and max(points)<.01 and results['native_centerline_closure_m']<.001
    results['start_join_distance_to_main_m']=float(np.linalg.norm(q[:,:2]-sa[-1,:2],axis=1).min());assert results['start_join_distance_to_main_m']<.15
    # Every start/pit location must fall inside its assigned surface.
    rp=json.loads((ROOT/'09_TRACKED/race_positions.json').read_text())
    for kind,maskname in [('pits','pits'),('grid','start')]:
        mask=np.asarray(Image.open(ROOT/f'03_MASKS/{maskname}.png'));xz=np.array([[p['x'],p['z']] for p in rp[kind]])
        values=map_coordinates(mask.astype(float),[(600-xz[:,1])/600*2047,xz[:,0]/600*2047],order=1)
        results[kind+'_count']=len(values);results[kind+'_minimum_mask_alpha']=float(values.min());assert values.min()>200
        spacing=np.linalg.norm(xz[:,None,:]-xz[None,:,:],axis=2)+np.eye(len(xz))*999;results[kind+'_minimum_spacing_m']=float(spacing.min());assert spacing.min()>=1.49
    for p in (ROOT/'03_MASKS').glob('*.tga'):
        img=Image.open(p);assert img.size==(2048,2048) and img.mode=='RGBA';assert np.array_equal(np.array(img)[:,:,3],np.array(Image.open(p.with_suffix('.png'))))
    for p in (ROOT/'04_TEXTURES').glob('*.tga'):
        a,b=Image.open(p).size;assert a>0 and b>0 and a&(a-1)==0 and b&(b-1)==0
    out=ROOT/'12_RELEASE'/NAME
    for p in out.glob('*.tl'):
        b=p.read_bytes();assert b[:4]==b'TL \0';n=struct.unpack_from('<I',b,4)[0];assert len(b)==8+n*8
        ar=np.frombuffer(b[8:],dtype='<f4').reshape(n,2);assert np.all(np.diff(ar[:,0])>0) and abs(ar[-1,0]-L)<.001
        assert np.isfinite(ar).all()
    # Read the RDF again, recovering the world positions it encodes.
    rdf=(out/f'{NAME}.rdf').read_text();reconstructed=[]
    for i,body in re.findall(r'start_stall(\d+)\s*\{([^}]+)\}',rdf,re.S):
        v=dict(re.findall(r'(\w+)\s*=\s*([^\n]+)',body));ss=(float(v['long'])+cut)%L;lat=float(v['lat']);th=np.interp(ss,q[:,3],q[:,2]);xz=np.array([np.interp(ss,q[:,3],q[:,k]) for k in range(2)])+lat*np.array([math.sin(th),-math.cos(th)]);expected=rp['pits'][int(i)];reconstructed.append(float(np.linalg.norm(xz-[expected['x'],expected['z']])))
    results['pit_rdf_reconstruction_error_max_m']=max(reconstructed);assert max(reconstructed)<.04
    jumps=json.loads((ROOT/'02_HEIGHTMAP/jump_profiles.json').read_text());from scipy.interpolate import CubicHermiteSpline
    slopes=[]
    for j in jumps:
        f=CubicHermiteSpline(j['profile_s'],j['profile_h'],j['profile_derivative']);xs=np.linspace(j['profile_s'][0],j['profile_s'][-1],500);slopes.append(float(np.max(np.abs(f(xs,1)))));assert f(xs).min()>-.005
    results['maximum_jump_profile_grade']=max(slopes);results['maximum_jump_profile_angle_deg']=math.degrees(math.atan(max(slopes)));assert max(slopes)<.85
    results['native_compilation']='pending';results['in_game_riding']='not performed';results['geographic_accuracy']='unverified construction estimate'
    (ROOT/'DOCUMENTATION/source_validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()


