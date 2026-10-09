"""Independent validation of final RAW/TGA/FBX/native TCL/race inputs."""
import re,math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v036_common import *
from v024_common import route_point
from v036_geometry import parse_tcl
from reference_route import sample_native
from v027_scenery import parse,geometry_records,vertices,child,fingerprint
from rebind_scenery import array
def main():
    c=read(S/'approved_update.json');assert c['height_factor']==1.3;old=np.load(BASE/'route.npz');new=np.load(O/'route.npz');q=old['q'];nq=new['q'];raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);after=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049);changes=raw!=after
    assert np.array_equal(old['start'],new['start']);assert sha(BASE/'start.tcl')==sha(O/'start.tcl');assert np.array_equal(old['width'],new['width']);untouched=(q[:,3]<=1276)|(q[:,3]>=1390);assert np.array_equal(q[untouched,:2],nq[untouched,:2])
    axis=np.linspace(0,600,2049);z,x=np.meshgrid(600-axis,axis,indexing='ij');pts=np.c_[x.ravel(),z.ravel()];dist,i=cKDTree(q[:,:2]).query(pts,workers=2);st=q[i,3];diff=changes.ravel();t05=(st>=428.5)&(st<=505)&(dist<13);assert not diff[t05].any()
    start=old['start'];sd,si=cKDTree(start[:,:2]).query(pts,workers=2);knots=read(BASE/'holeshot_layout.json')['start_width_knots'];w=np.interp(start[si,3],*np.array(knots).T);assert not diff[sd<w/2+2].any()
    profiles=read(BASE/'jump_profiles.json');updated={p['id']:p for p in read(O/'jump_profiles.json')};jumps=[]
    for p in profiles:
        if p['kind']=='none' or p['id'] in ['R11','R12','R17']:continue
        guard=(st>=p['station_start_m']-2)&(st<=p['station_end_m']+2)&(dist<old['width'][i]/2+2.5);n=int(diff[guard].sum());assert n==0,(p['id'],n);jumps.append(dict(id=p['id'],checked_samples=int(guard.sum()),changed_samples=n))
    h0=raw.astype(float)/65535*18;h1=after.astype(float)/65535*18;sample=lambda H,p:float(map_coordinates(H,[[(600-p[1])/600*2048],[p[0]/600*2048]],order=1)[0]);heights=[]
    for p in profiles:
        if p['id'] not in ['R11','R12']:continue
        n=updated[p['id']];assert n['station_start_m']==p['station_start_m'] and n['station_end_m']==p['station_end_m'];assert np.allclose(n['crest_offsets_m'],p['crest_offsets_m'],rtol=0,atol=1e-8);assert abs(n['crest_height_m']/p['crest_height_m']-1.3)<1e-12
        expected=p.get('roller_heights_m',[p['crest_height_m']]+[g['landing_crest_height_m'] for g in p.get('gaps',[])])
        for off,height in zip(p['crest_offsets_m'],expected):
            station=p['lip_s']+off;point=route_point(q,station);rise=sample(h1,point)-sample(h0,point);error=rise-.3*height;assert abs(error)<.021,(p['id'],station,rise,.3*height);heights.append(dict(id=p['id'],station_m=station,baseline_crest_height_m=height,target_crest_height_m=height*1.3,measured_native_height_increase_m=rise,expected_height_increase_m=.3*height,error_m=error))
    single=updated['R11_ENTRY'];point=route_point(nq,single['lip_s']);single_rise=sample(h1,point)-sample(h0,point);assert .725<single_rise<.765
    p17=updated['R17'];previous=next(p for p in profiles if p['id']=='R17');assert p17['roller_heights_m']==previous['roller_heights_m'];assert len(p17['crest_offsets_m'])==8 and np.allclose(np.diff(p17['crest_offsets_m']),10)
    names=['visual_racing','visual_sand','visual_grass','v032_pits','v032_packed','v032_groom_0','v032_groom_45','v032_groom_90','v032_groom_135','v032_face','v032_damp'];masks={n:np.asarray(Image.open(O/'materials'/('mask_'+n+'.tga')).getchannel('A'),float) for n in names};soil=[]
    for station in [12,30,55,75,90,100,110,120]:
        p=route_point(start,station);width=np.interp(station,*np.array(knots).T);v=p[:2]+np.linspace(-width/2+1.5,width/2-1.5,41)[:,None]*[np.sin(p[2]),-np.cos(p[2])];stats={}
        for name,a in masks.items():
            vals=map_coordinates(a,[(600-v[:,1])/600*(a.shape[0]-1),v[:,0]/600*(a.shape[1]-1)],order=1);stats[name]=[float(vals.min()),float(vals.max())]
        assert stats['visual_racing'][0]>245,(station,stats);assert stats['v032_packed'][1]<=18.01
        for name in names:
            if name not in ['visual_racing','v032_packed']:assert stats[name][1]<1.1,(station,name,stats[name])
        soil.append(dict(station_m=station,width_m=float(width),native_alpha_ranges=stats))
    text0=(R/'12_RELEASE/orlandomx_2026_v035/orlandomx_2026_v035.rdf').read_text();text1=(R/'12_RELEASE'/NAME/(NAME+'.rdf')).read_text();leaf=re.compile(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',re.S);preserved=[]
    for m in leaf.finditer(text0):
        if m[1].startswith(('stall','pit')) or re.search(r'(?m)^\s*line\s*=\s*2\s*$',m[2]):assert m[0] in text1,m[1];preserved.append(m[1])
    assert len(preserved)>=48
    orig,th,segs=parse_tcl(O/'main.tcl');native=sample_native(orig,th,segs,.12);error=float(cKDTree(nq[:,:2]).query(native[:,:2])[0].max());assert error<.16,error
    nodes,_=parse((O/'scenery.fbx').read_bytes());rec=geometry_records(nodes);base_nodes,_=parse((BASE/'scenery.fbx').read_bytes());base_rec=geometry_records(base_nodes);audits=[];blocks=[];sector=nq[(new['v036_old_station']>=1297)&(new['v036_old_station']<=1386)];tree=cKDTree(sector[:,:2])
    for name,(g,_) in rec.items():
        if name.startswith('SOFTCPLAS_marker_'):continue
        v=vertices(g);centre=v[:,[0,2]].mean(0);radius=np.max(np.linalg.norm(v[:,[0,2]]-centre,axis=1))
        if tree.query(centre)[0]>radius+8:continue
        inds=array(child(g,b'PolygonVertexIndex'));tri=[];face=[]
        for val in inds:
            val=int(val);face.append(val if val>=0 else -val-1)
            if val<0:tri.extend(v[[face[0],face[k],face[k+1]]] for k in range(1,len(face)-1));face=[]
        tri=np.asarray(tri);chunks=[v]
        for _ in range(10):
            lengths=np.max(np.linalg.norm(tri-np.roll(tri,1,axis=1),axis=2),axis=1);chunks.append(tri[lengths<=.6].reshape(-1,3));tri=tri[lengths>.6]
            if not len(tri):break
            a,b,c=tri[:,0],tri[:,1],tri[:,2];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2;tri=np.concatenate([np.stack([a,ab,ca],1),np.stack([ab,b,bc],1),np.stack([ca,bc,c],1),np.stack([ab,bc,ca],1)])
        assert not len(tri);dense=np.concatenate(chunks);ground=map_coordinates(h1,[(600-dense[:,2])/600*2048,dense[:,0]/600*2048],order=1,mode='nearest');dense=dense[(dense[:,1]-ground<3.2)&(dense[:,1]-ground>-.15)];dd,ii=tree.query(dense[:,[0,2]],workers=2);p=sector[ii];dv=dense[:,[0,2]]-p[:,:2];along=p[:,3]+dv[:,0]*np.cos(p[:,2])+dv[:,1]*np.sin(p[:,2]);hits=int(((along>sector[0,3])&(along<sector[-1,3])&(dd<4.65)).sum());audits.append(dict(model=name,dense_low_samples=len(dense),intruding_samples=hits))
        if hits:blocks.append(dict(model=name,hits=hits))
    assert not blocks,blocks
    protected=[name for name in base_rec if any(s in name.lower() for s in ['memorial','qwikchute','entry_sign','vehicle','practice_wood','practice_barrier'])];assert all(fingerprint(base_rec[n][0])==fingerprint(rec[n][0]) for n in protected)
    tiles=list((BASE/'materials').glob('v032_*.tga'));assert all(sha(p)==sha(O/'materials'/p.name) for p in tiles);assert all(sha(p)==sha(O/'facility_textures'/p.name) for p in (BASE/'facility_textures').glob('*.tga'))
    qa=dict(checks_pass=True,baseline='v035',height_factor=1.3,T05_checked_samples=int(t05.sum()),T05_changed_samples=0,start_apron_changed_height_samples=0,unchanged_jump_checks=jumps,small_jump_measured_height_checks=heights,new_single_measured_height_m=single_rise,roller_count=8,roller_heights_and_10m_crest_spacing_preserved=True,unaffected_route_world_coordinates_exact=True,soil_cross_sections=soil,preserved_gate_pit_start_blocks=len(preserved),native_to_authored_route_max_m=error,native_closure_m=float(np.linalg.norm(native[-1,:2]-native[0,:2])),dense_scenery_audits=audits,roller_corridor_obstructions=blocks,protected_sign_vehicle_fence_records=len(protected),v030_tiles_byte_exact=len(tiles),facility_art_textures_byte_exact=True,in_game_v036_test=False);save(O/'update_independent_validation.json',qa);print('Independent v036 source checks passed:',len(heights),'small crests;',len(audits),'dense scenery audits.',flush=True)
if __name__=='__main__':main()
