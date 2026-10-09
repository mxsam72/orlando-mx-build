"""Independent checks against the immutable user-tested v036 source."""
from collections import Counter
import struct
import numpy as np
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon, box
from v037_common import *
from v027_scenery import parse, values, child, fingerprint, geometry_records, vertices
from rebind_scenery import array

def faces(g):
    raw=array(child(g,b'PolygonVertexIndex')).astype(int);out=[];face=[]
    for i in raw:
        face.append(-i-1 if i<0 else i)
        if i<0:out.append(face);face=[]
    assert not face;return out

def main():
    cfg=read(S/'oval.json');old=parse((BASE/'scenery.fbx').read_bytes())[0];new=parse((O/'scenery.fbx').read_bytes())[0]
    rec0=geometry_records(old);rec1=geometry_records(new)
    a=next(n for n in old if n['name']==b'Objects')['children'];b=next(n for n in new if n['name']==b'Objects')['children']
    by0={values(n)[0]:n for n in a};by1={values(n)[0]:n for n in b}
    assert all(i in by1 and fingerprint(n)==fingerprint(by1[i]) for i,n in by0.items())
    l0=next(n for n in old if n['name']==b'Connections')['children'];l1=next(n for n in new if n['name']==b'Connections')['children']
    assert [fingerprint(n) for n in l0]==[fingerprint(n) for n in l1[:len(l0)]]
    assert all(n in rec1 and fingerprint(g)==fingerprint(rec1[n][0]) for n,(g,mid) in rec0.items())
    exact=[]
    for fn in ['terrain.raw','main.tcl','start.tcl','route.npz','jump_profiles.json','compiled_track.hmf','v024_pit_gravel.tga','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
        assert sha(BASE/fn)==sha(O/fn),fn;exact.append(dict(file=fn,sha256=sha(O/fn)))
    assert sha(BASE/'orlandomx_2026_v036.rdf')==sha(O/(NAME+'.rdf'))
    tiles=[]
    for folder in ['masks','materials','facility_textures']:
        for p in (BASE/folder).rglob('*'):
            if not p.is_file():continue
            q=O/folder/p.relative_to(BASE/folder);assert sha(p)==sha(q),str(q);tiles.append(dict(file=str(q.relative_to(O)),sha256=sha(q)))
    road=rec1['TRKASPH_v037_oval_surface'][0];vv=vertices(road);ff=np.asarray(faces(road));assert ff.shape[1]==3
    bind_road_mesh(vv)
    xz=vv[:,[0,2]];local=xz-cfg['centre_xz_m'];norm=np.cross(vv[ff[:,1]]-vv[ff[:,0]],vv[ff[:,2]]-vv[ff[:,0]])
    # The FBX polygon winding is reflected during native Z conversion.
    assert np.all(norm[:,1]<-1e-10),'Native front-face winding regression'
    tri=shapely.polygons(local[ff]);union=shapely.union_all(tri);assert union.is_valid
    holes=list(union.interiors) if union.geom_type=='Polygon' else [];assert len(holes)==2,(union.geom_type,len(holes))
    assert union.covers(shapely.Point(0,0)),'Crossover is missing'
    for z in cfg['infield_centres_local_z_m']:assert not union.covers(shapely.Point(0,z)),'Infield grass filled by pavement'
    # Check every native height-field vertex under the entire paved area,
    # including the waist where the first draft exposed grass through the road.
    xx,zz=np.meshgrid(np.arange(1590,2017)/2048*600,600-np.arange(575,1230)/2048*600)
    nativepoints=np.c_[xx.ravel(),zz.ravel()];localp=nativepoints-cfg['centre_xz_m'];inside=shapely.contains_xy(union,localp[:,0],localp[:,1]);nativepoints=nativepoints[inside]
    clearance=road_height(height_field(),nativepoints,cfg)-ground(height_field(),nativepoints)
    # The apron smoothly returns to grass at its open end; require clearance
    # over the oval proper, allowing the deliberate zero-height entrance seam.
    proper=nativepoints[:,0]>cfg['centre_xz_m'][0]-55
    assert clearance[proper].min()>.025,('Grass penetrates asphalt',clearance[proper].min())
    bounds=[float(xz[:,0].min()),float(xz[:,1].min()),float(xz[:,0].max()),float(xz[:,1].max())];assert bounds[0]>460 and bounds[2]<596 and bounds[1]>240 and bounds[3]<440
    q=np.load(BASE/'route.npz');main=q['q'];start=q['start']
    dist,ix=cKDTree(main[:,:2]).query(xz);main_edge=float(np.min(dist-q['width'][ix]/2))
    sd,si=cKDTree(start[:,:2]).query(xz);knots=np.asarray(read(BASE/'holeshot_layout.json')['start_width_knots']);sw=np.interp(start[si,3],knots[:,0],knots[:,1]);start_edge=float(np.min(sd-sw/2));assert main_edge>50 and start_edge>35,(main_edge,start_edge)
    treeconflicts=[]
    for name,(g,mid) in rec0.items():
        if not (name.startswith(('tree_','scrub_')) or '_oak_' in name):continue
        tv=vertices(g)[:,[0,2]]-cfg['centre_xz_m'];bb=box(*[tv[:,0].min(),tv[:,1].min(),tv[:,0].max(),tv[:,1].max()])
        if union.intersects(bb):treeconflicts.append(name)
    assert not treeconflicts,treeconflicts
    trucks=[]
    for asset in cfg['vehicles']:
        prefix=asset['id']+'_';names=[n for n in rec1 if n.startswith(prefix)];assert len(names)==11
        vv2=[]
        for n in names:
            suffix=n.removeprefix(prefix);g=rec1[n][0];src=rec0[cfg['vehicle_reference']+'_'+suffix][0]
            assert child(g,b'PolygonVertexIndex')['props']==child(src,b'PolygonVertexIndex')['props']
            assert fingerprint(child(g,b'LayerElementUV'))==fingerprint(child(src,b'LayerElementUV'))
            vv2.append(vertices(g))
        tv=np.concatenate(vv2);assert np.all(shapely.covers(union,shapely.points(tv[:,[0,2]]-cfg['centre_xz_m'])))
        front=vertices(rec1[prefix+'headlight'][0])[:,[0,2]].mean(0);rear=vertices(rec1[prefix+'red_light'][0])[:,[0,2]].mean(0);f=front-rear;angle=np.degrees(np.arctan2(f[1],f[0]));err=abs((angle-asset['heading_degrees']+180)%360-180)
        # Headlights and rear lights have different heights: pitching/rolling
        # the rigid asset onto the camber slightly shifts this projected vector.
        assert err<.15,(asset['id'],'truck heading drift',err)
        trucks.append(dict(id=asset['id'],parts=11,topology_and_UV_exact_source=True,all_vertices_inside_paved_course=True,forward_heading_error_degrees=float(err)))
    defs=next(n for n in new if n['name']==b'Definitions');decl=[]
    for d in defs['children']:
        if d['name']!=b'ObjectType':continue
        typ=values(d)[0];cnt=values(child(d,b'Count'))[0];olddef=next(t for t in next(n for n in old if n['name']==b'Definitions')['children'] if t['name']==b'ObjectType' and values(t)[0]==typ)
        expected=values(child(olddef,b'Count'))[0]+sum(n['name']==typ for n in b)-sum(n['name']==typ for n in a);assert cnt==expected;decl.append(cnt)
    assert values(child(defs,b'Count'))[0]==sum(decl)
    qa=dict(checks_pass=True,baseline_version='user-tested v036',heightmap_and_MX_route_byte_exact=True,protected_files=exact,retained_texture_and_mask_files=len(tiles),retained_files=tiles,baseline_object_records_byte_exact=len(a),baseline_connections_byte_exact=len(l0),baseline_geometry_records_byte_exact=len(rec0),new_geometry_count=len(rec1)-len(rec0),road_bounds_xz_m=bounds,grass_infields=2,paved_crossover_present=True,asphalt_native_prefix='TRKASPH',concrete_wall_native_prefix='WLLCONC',native_height_samples_under_road_checked=len(nativepoints),minimum_oval_heightmap_clearance_m=float(clearance[proper].min()),main_riding_edge_clearance_m=main_edge,start_riding_edge_clearance_m=start_edge,trees_moved_or_removed=0,road_tree_conflicts=treeconflicts,static_cybertruck_count=2,trucks=trucks,all_existing_signs_pit_displays_and_fences_preserved=True)
    save(O/'oval_independent_validation.json',qa);print('v037 independent checks passed:',len(a),'baseline object records and',len(tiles),'material/mask files unchanged; two Cybertrucks on asphalt.',flush=True)
if __name__=='__main__':main()
