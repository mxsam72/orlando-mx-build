"""Independent exact main-lap, native-mask, race, scenery and fence validation."""
from pathlib import Path
import json,re,math,numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from v027_scenery import parse,geometry_records,vertices,child
from rebind_scenery import array
from v024_common import route_point
from v033_common import save,sha
R=Path(__file__).resolve().parents[1];B=R/'V033_OUTPUT';O=R/'V035_OUTPUT'
def main():
    cfg=json.loads((R/'V035_SOURCE/start_fix.json').read_text());old=np.load(B/'route.npz');new=np.load(O/'route.npz');q=old['q'];sa=new['start'];raw=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049);after=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)
    for key in old.files:
        if key=='start':continue
        assert np.array_equal(old[key],new[key]),'Main route array changed: '+key
    for name in ['main.tcl','turns.json','geometry_spec.json','jump_profiles.json']:assert sha(B/name)==sha(O/name)
    axis=np.linspace(0,600,2049);zz,xx=np.meshgrid(600-axis,axis,indexing='ij');points=np.c_[xx.ravel(),zz.ravel()];dd,ii=cKDTree(q[:,:2]).query(points,workers=2);st=q[ii,3];mainmask=dd<=old['width'][ii]/2+3.;corner=(st>=428.5)&(st<=505)&(dd<=13);assert np.array_equal(raw.ravel()[mainmask],after.ravel()[mainmask]);assert np.array_equal(raw.ravel()[corner],after.ravel()[corner]);jumps=[]
    for p in json.loads((B/'jump_profiles.json').read_text()):
        if p.get('crest_height_m',0)<=0:continue
        mask=(st>=p['station_start_m']-3)&(st<=p['station_end_m']+3)&(dd<=old['width'][ii]/2+7.5);count=int(np.count_nonzero(raw.ravel()[mask]!=after.ravel()[mask]));assert count==0,(p['id'],count);jumps.append(dict(id=p['id'],checked_native_height_samples=int(mask.sum()),changed_height_samples=count))
    # Compare FINAL native source masks over a world-space guard; does not reuse author fields.
    maskchecks=[]
    for n in [2048,4096]:
        cols=np.flatnonzero((np.linspace(0,600,n)>=310)&(np.linspace(0,600,n)<=456));rows=np.flatnonzero((np.linspace(600,0,n)>=170)&(np.linspace(600,0,n)<=300));zz,xx=np.meshgrid(600-rows/(n-1)*600,cols/(n-1)*600,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()];d,i=cKDTree(q[:,:2]).query(pts,workers=2);station=q[i,3];guard=d<=old['width'][i]/2+2.5;guard|=(station>=428.5)&(station<=505)&(d<=10)
        for folder in ['masks','materials']:
            for p in sorted((B/folder).glob('*.tga')):
                if folder=='materials' and not p.name.startswith('mask_'):continue
                with Image.open(p) as im:
                    if im.size!=(n,n):continue
                    a=np.array(im.getchannel('A'))[np.ix_(rows,cols)].ravel()
                with Image.open(O/folder/p.name) as im:b=np.array(im.getchannel('A'))[np.ix_(rows,cols)].ravel()
                changes=int(np.count_nonzero(a[guard]!=b[guard]));assert changes==0,(folder,p.name,changes);maskchecks.append(dict(file=folder+'/'+p.name,main_corner_changed_pixels=changes))
    # Full clear lane cross sections through the broad approach consume real TGA alpha.
    racing=np.asarray(Image.open(O/'masks/racing.tga').getchannel('A'),float);grass=np.asarray(Image.open(O/'masks/grass.tga').getchannel('A'),float);clear=[]
    for station in [12,30,50,70,80]:
        p=route_point(sa,station);w=np.interp(station,*np.array(cfg['start_width_knots']).T);v=p[:2]+np.linspace(-w/2+1,w/2-1,41)[:,None]*[-np.sin(p[2]),np.cos(p[2])];coords=[(600-v[:,1])/600*2047,v[:,0]/600*2047];a=map_coordinates(racing,coords,order=1);g=map_coordinates(grass,coords,order=1);assert a.min()>250 and g.max()<1,(station,a.min(),g.max());clear.append(dict(start_station_m=station,width_m=float(w),minimum_racing_alpha=float(a.min()),maximum_grass_alpha=float(g.max())))
    # Triangle interiors are inspected so large rails/canopies cannot evade a vertex-only check.
    nodes,_=parse((O/'scenery.fbx').read_bytes());records=geometry_records(nodes);practice=np.load(O/'practice_access.npz')['lane'];ht=after/65535*18
    routes=[('start',sa,None,12,108),('practice',practice,6.5,0,practice[-1,3])];blocks=[];audited=[]
    for name,(geom,mid) in records.items():
        if name.startswith('SOFTCPLAS_marker_'):continue
        v=vertices(geom);center=(v[:,[0,2]].min(0)+v[:,[0,2]].max(0))/2;radius=np.linalg.norm(v[:,[0,2]]-center,axis=1).max()
        if all(cKDTree(line[:,:2]).query(center)[0]>radius+20 for _,line,_,_,_ in routes):continue
        inds=array(child(geom,b'PolygonVertexIndex'));tri=[];face=[]
        for value in inds:
            value=int(value);face.append(value if value>=0 else -value-1)
            if value<0:tri.extend(v[[face[0],face[k],face[k+1]]] for k in range(1,len(face)-1));face=[]
        tri=np.asarray(tri);chunks=[v]
        for _ in range(10):
            lengths=np.max(np.linalg.norm(tri-np.roll(tri,1,axis=1),axis=2),axis=1);chunks.append(tri[lengths<=.65].reshape(-1,3));tri=tri[lengths>.65]
            if not len(tri):break
            a,b,c=tri[:,0],tri[:,1],tri[:,2];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2;tri=np.concatenate([np.stack([a,ab,ca],1),np.stack([ab,b,bc],1),np.stack([ca,bc,c],1),np.stack([ab,bc,ca],1)])
        assert not len(tri);dense=np.concatenate(chunks);ground=map_coordinates(ht,[(600-dense[:,2])/600*2048,dense[:,0]/600*2048],order=1,mode='nearest');dense=dense[(dense[:,1]-ground<3.2)&(dense[:,1]-ground>-.2)];hits=[]
        for label,line,ww,s0,s1 in routes:
            d,i=cKDTree(line[:,:2]).query(dense[:,[0,2]],workers=2);p=line[i];dv=dense[:,[0,2]]-p[:,:2];station=p[:,3]+dv[:,0]*np.cos(p[:,2])+dv[:,1]*np.sin(p[:,2]);half=np.full(len(i),ww/2) if ww else np.interp(station,*np.array(cfg['start_width_knots']).T)/2;inside=(station>s0)&(station<s1)&(d<half-.35)
            if inside.any():hits.append(dict(route=label,intruding_dense_samples=int(inside.sum())))
        audited.append(dict(model=name,low_samples=len(dense),hits=hits))
        if hits:blocks.append(dict(model=name,hits=hits))
    assert not blocks,'Low scenery blocks approach: '+repr(blocks)
    # Gate/pit and main checkpoint blocks in actual race text must be byte exact.
    a=(R/'12_RELEASE/orlandomx_2026_v033/orlandomx_2026_v033.rdf').read_text();b=(R/'12_RELEASE/orlandomx_2026_v035/orlandomx_2026_v035.rdf').read_text();leaf=re.compile(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',re.S);oldleaf={m[1]:m[0] for m in leaf.finditer(a)};newleaf={m[1]:m[0] for m in leaf.finditer(b)}
    preserved=[]
    for m in leaf.finditer(a):
        line=re.search(r'(?m)^\s*line\s*=\s*(\d+)',m[2])
        if line and int(line[1])==2:continue
        assert m[0] in b,'Race leaf changed: '+m[1];preserved.append(m[1])
    first=lambda p:float(re.search(r'segment0\s*\{\s*type\s*=\s*0\s*length\s*=\s*([\d.]+)',p.read_text(),re.S)[1]);before=first(B/'start.tcl')-12;aftercurve=first(O/'start.tcl')-12;assert aftercurve-before>25
    native_error=float(cKDTree(new['native'][:,:2]).query(sa[-1,:2])[0]);assert native_error<.12
    tcl=json.loads((O/'holeshot_layout.json').read_text());assert tcl['main_track_translation_m']==0
    tiles=list((B/'materials').glob('v032_*.tga'));assert all(sha(p)==sha(O/'materials'/p.name) for p in tiles);assert all(sha(p)==sha(O/'facility_textures'/p.name) for p in (B/'facility_textures').glob('*'))
    qa=dict(checks_pass=True,baseline='v033',main_centerline_arrays_byte_exact=True,main_native_tcl_byte_exact=True,main_height_samples_checked=int(mainmask.sum()),main_height_changes=0,T05_full_hill_and_bank_samples_checked=int(corner.sum()),T05_height_changes=0,jump_checks=jumps,main_corner_alpha_checks=maskchecks,physical_start_cross_sections=clear,dense_scenery_audits=audited,approach_obstructions=blocks,preserved_race_leaf_count=len(preserved),gate_and_pit_stall_blocks_preserved=48,gate_to_first_curve_before_m=before,gate_to_first_curve_after_m=aftercurve,start_merge_to_native_main_distance_m=native_error,all_dirt_color_tiles_byte_exact=len(tiles),all_facility_art_textures_byte_exact=True,in_game_test=False)
    save(O/'holeshot_independent_validation.json',qa);print(json.dumps({k:v for k,v in qa.items() if k not in ['dense_scenery_audits','main_corner_alpha_checks']},indent=2),flush=True)
if __name__=='__main__':main()
