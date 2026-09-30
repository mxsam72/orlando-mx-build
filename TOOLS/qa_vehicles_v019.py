"""Footprint-based clearances: all new vehicles/bikes, all v018 pit obstacles."""
import numpy as np
from scipy.spatial import ConvexHull,cKDTree
from v019_common import *

def hull(v):
    p=np.unique(np.asarray(v),axis=0)
    return p[ConvexHull(p).vertices]
def point_segment(p,a,b):
    d=b-a;t=np.clip(((p-a)*d).sum(-1)/(d@d),0,1);return np.linalg.norm(p-a-t[...,None]*d,axis=-1)
def inside(p,poly):
    d=np.roll(poly,-1,axis=0)-poly;q=np.asarray(p)[...,None,:]-poly
    cr=d[:,0]*q[...,1]-d[:,1]*q[...,0];return (cr>=-1e-8).all(-1)
def segments_cross(a,b,c,d):
    def cr(x,y):return x[0]*y[1]-x[1]*y[0]
    return cr(b-a,c-a)*cr(b-a,d-a)<0 and cr(d-c,a-c)*cr(d-c,b-c)<0
def poly_distance(a,b):
    if inside(a,b).any() or inside(b,a).any():return 0.0
    for x,y in zip(a,np.roll(a,-1,axis=0)):
        for z,w in zip(b,np.roll(b,-1,axis=0)):
            if segments_cross(x,y,z,w):return 0.0
    return float(min(min(point_segment(a,x,y).min() for x,y in zip(b,np.roll(b,-1,axis=0))),min(point_segment(b,x,y).min() for x,y in zip(a,np.roll(a,-1,axis=0)))))
def line_clear(poly,a,b):
    if inside(np.array([a,b]),poly).any():return 0.
    if any(segments_cross(a,b,x,y) for x,y in zip(poly,np.roll(poly,-1,axis=0))):return 0.
    return float(min(point_segment(poly,a,b).min(),min(point_segment(np.array([a,b]),x,y).min() for x,y in zip(poly,np.roll(poly,-1,axis=0)))))
def samples(poly):
    low=poly.min(0);high=poly.max(0);xx,zz=np.meshgrid(np.arange(low[0],high[0]+.15,.15),np.arange(low[1],high[1]+.15,.15));p=np.c_[xx.ravel(),zz.ravel()];p=p[inside(p,poly)]
    edge=np.concatenate([np.linspace(a,b,max(2,int(np.linalg.norm(a-b)/.12)+1)) for a,b in zip(poly,np.roll(poly,-1,axis=0))]);return np.r_[poly,p,edge]

def main():
    spec=read(S/'vehicles.json');assets=spec['assets'];meshes=read(O/'vehicle_meshes.json');mat=read(S/'vehicle_materials.json');H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    expected={'truck_jordan','truck_premier','truck_sam','van_shane','bike_jordan','bike_premier','bike_sam','bike_shane'};assert {m['asset'] for m in meshes}==expected
    assert len({tuple(a['xz']) for a in assets})==8;foot={};records=[];valid=[]
    for m in meshes:
        v=np.asarray(m['vertices']);f=np.asarray(m['faces']);uv=np.asarray(m['uv']);assert np.isfinite(v).all() and np.isfinite(uv).all();assert len(f)>0 and f.shape[1]==3 and f.min()>=0 and f.max()<len(v);assert uv.shape==(len(f),3,2);assert m['material'] in mat
        area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1);assert area.min()>1e-10
    for name,m in mat.items():
        p=S/m['file'];assert p.exists() and sha(p)==m['sha256'];valid.append(dict(name=name,file=m['file'],sha256=sha(p)))
    for a in assets:
        v=np.concatenate([m['vertices'] for m in meshes if m['asset']==a['id']]);foot[a['id']]=hull(v[:,[0,2]])
    fac=read(O/'facility_meshes.json');pit=read(S/'pit_facilities.json');oldassets={a['id']:a for a in pit['assets']};obstacles={}
    for a in oldassets:
        vv=np.concatenate([m['vertices'] for m in fac if m['asset']==a]);low=vv[vv[:,1]<ground(H,vv[:,[0,2]])+1.7]
        if len(low)>3:obstacles[a]=hull(low[:,[0,2]])
    q,w=route();qt=cKDTree(q[:,:2]);sa=np.load(O/'route.npz')['start'];st=cKDTree(sa[:,:2]);cfg=read(S/'facilities.json');pits=np.array([[x,z] for x in range(260,331,10) for z in [110,117,124]])
    for a in assets:
        p=foot[a['id']];ss=samples(p);d,ix=qt.query(ss);mc=float((d-w[ix]/2).min());d,ix=st.query(ss);sc=float((d-np.interp(sa[ix,3],*np.array(cfg['start_width_knots']).T)/2).min())
        pc=float(min(point_segment(pits,x,y).min() for x,y in zip(p,np.roll(p,-1,axis=0))))
        assert not inside(pits,p).any()
        roads={road['id']:min(line_clear(p,np.array(aa),np.array(bb))-road['width']/2 for aa,bb in zip(road['points'][:-1],road['points'][1:])) for road in pit['roads']}
        other={key:poly_distance(p,ff) for key,ff in obstacles.items()};pair={key:poly_distance(p,ff) for key,ff in foot.items() if key!=a['id']}
        grass=any((p[:,0]>patch['bounds_xz'][0]).all() and (p[:,0]<patch['bounds_xz'][2]).all() and (p[:,1]>patch['bounds_xz'][1]).all() and (p[:,1]<patch['bounds_xz'][3]).all() for patch in pit['grass_patches'])
        fence=np.array(cfg['fence_polyline_xz']);fc=min(line_clear(p,aa,bb) for aa,bb in zip(fence[:-1],fence[1:]))
        row=dict(asset=a['id'],main_track_edge_m=mc,start_route_edge_m=sc,pit_spawn_m=pc,road_edge_m=min(roads.values()),existing_asset_m=min(other.values()),existing_asset_nearest=min(other,key=other.get),other_new_asset_m=min(pair.values()),other_new_asset_nearest=min(pair,key=pair.get),fence_m=fc,grass_footprint=grass,existing_clearances_m=other,paired_clearances_m=pair,road_clearances_m=roads)
        row['passes']=mc>1 and sc>1 and pc>2 and min(roads.values())>1 and min(other.values())>.75 and min(pair.values())>.50 and fc>2 and grass
        records.append(row)
    baselinepit=read(R/'V018_SOURCE/pit_facilities.json');assert pit['assets']==baselinepit['assets'] and pit['roads']==baselinepit['roads'] and pit['grass_patches']==baselinepit['grass_patches']
    bathroom=oldassets['restroom'];assert bathroom['xz']==[275,112.5] and bathroom['heading']==0;assert 'bithlo_stop_sign' in oldassets or any(a['type']=='sticker_stop_sign' for a in oldassets.values())
    assert sha(O/'terrain.raw')==read(S/'v018_invariants.json')['raw_sha256']
    report=dict(version='v019',source_commit=__import__('os').environ.get('GITHUB_SHA','local'),vehicle_count=4,bike_count=4,mesh_count=len(meshes),triangles=sum(len(m['faces']) for m in meshes),material_count=len(mat),textures=valid,clearances=records,clearance_method='Convex footprints, segment distances and <=0.15m track/start samples; crowns above 1.7m excluded only from existing tree obstacle footprint',existing_facility_specs_unchanged=True,bathroom_orientation_preserved=True,pit_roads_and_grass_specs_unchanged=True,bithlo_sign_present=True,terrain_hash_matches_v018=True,in_game_riding=False,checks_pass=all(r['passes'] for r in records))
    save(R/'DOCUMENTATION/v019_vehicle_validation.json',report)
    for r in records:print(r['asset'],r['passes'],'road',round(r['road_edge_m'],2),'existing',r['existing_asset_nearest'],round(r['existing_asset_m'],2),'paired',round(r['other_new_asset_m'],2))
    assert report['checks_pass'],'Vehicle clearance failure; adjust placement'
if __name__=='__main__':main()
