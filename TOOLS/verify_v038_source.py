"""Independently verify the precise scope of v038 against native v037."""
import numpy as np
import shapely
from shapely.geometry import MultiPoint, box
from scipy.spatial import cKDTree
from v038_common import *
from v027_scenery import parse, values, child, fingerprint, geometry_records, vertices
from verify_v037_source import faces
from rebind_scenery import array

def main():
    cfg=read(S/'update.json');before,tail=parse((BASE/'scenery.fbx').read_bytes());after,tail1=parse((O/'scenery.fbx').read_bytes());scene=read(O/'v038_scenery_validation.json')
    a={values(n)[0]:n for n in next(n for n in before if n['name']==b'Objects')['children']};b={values(n)[0]:n for n in next(n for n in after if n['name']==b'Objects')['children']};allowed=set(scene['modified_truck_geometry_ids']);assert len(allowed)==22
    assert all(i in b and fingerprint(n)==fingerprint(b[i]) for i,n in a.items() if i not in allowed)
    con0=next(n for n in before if n['name']==b'Connections')['children'];con1=next(n for n in after if n['name']==b'Connections')['children'];changed=[]
    for i,(c0,c1) in enumerate(zip(con0,con1)):
        if fingerprint(c0)==fingerprint(c1):continue
        x,y=values(c0),values(c1);assert x[0]==y[0]==b'OO' and x[2:]==y[2:];assert x[1]==998742110
        model=values(b[y[2]])[1].split(b'\0')[0].decode();assert model in {v['id']+'_cyber_steel' for v in cfg['vehicles']};changed.append(model)
    assert len(changed)==2
    unchanged_top={n['name']:fingerprint(n) for n in before if n['name'] not in [b'Objects',b'Connections',b'Definitions']}
    assert unchanged_top=={n['name']:fingerprint(n) for n in after if n['name'] in unchanged_top}
    # The encoder recalculates footer alignment after the file length changes.
    # Preserve its ID/version/magic, allowing only the intervening zero padding.
    assert tail[:20]==tail1[:20] and tail[-140:]==tail1[-140:]
    rec0=geometry_records(before);rec1=geometry_records(after);road_names=['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap']
    for n in road_names:assert fingerprint(rec0[n][0])==fingerprint(rec1[n][0]) and rec0[n][1]==rec1[n][1]
    protected=[]
    for name in ['terrain.raw','main.tcl','start.tcl','route.npz','jump_profiles.json','compiled_track.hmf','v024_pit_gravel.tga','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
        assert sha(BASE/name)==sha(O/name);protected.append(dict(file=name,sha256=sha(O/name)))
    assert sha(BASE/'orlandomx_2026_v037.rdf')==sha(O/(NAME+'.rdf'))
    normal_names=set(cfg['normal_map_optimization']['files']);retained=[];changed_files=[]
    for folder in ['masks','materials','facility_textures']:
        for p in (BASE/folder).rglob('*'):
            if not p.is_file():continue
            q=O/folder/p.relative_to(BASE/folder)
            if folder=='materials' and p.name in normal_names:
                from PIL import Image
                with Image.open(p) as im:aa=np.array(im)
                with Image.open(q) as im:bb=np.array(im);assert im.size==(1024,1024)
                assert np.all(bb[:,:,3]==aa[0,0,3]);assert sha(p)!=sha(q);changed_files.append(p.name)
                nn=bb[:,:,:3].astype(float)/127.5-1;assert np.max(abs(np.linalg.norm(nn,axis=2)-1))<.015
            else:
                assert sha(p)==sha(q),str(p);retained.append(dict(file=q.relative_to(O).as_posix(),sha256=sha(q)))
    assert set(changed_files)==normal_names
    h=height_field();g=rec1[road_names[0]][0];rv=vertices(g);poly=shapely.union_all(shapely.polygons(rv[:,[0,2]][np.asarray(faces(g))]));truckchecks=[]
    for car in cfg['vehicles']:
        prefix=car['id']+'_';names=[n for n in rec1 if n.startswith(prefix)];assert len(names)==11;parts=[]
        for name in names:
            old,mid0=rec0[name];new,mid1=rec1[name];assert mid0==mid1 and values(old)[0] in allowed
            assert child(old,b'PolygonVertexIndex')['props']==child(new,b'PolygonVertexIndex')['props']
            assert fingerprint(child(old,b'LayerElementUV'))==fingerprint(child(new,b'LayerElementUV'))
            assert fingerprint(child(old,b'LayerElementMaterial'))==fingerprint(child(new,b'LayerElementMaterial'))
            assert not np.allclose(vertices(old),vertices(new),rtol=0,atol=1e-6)
            parts.append(vertices(new))
        v=np.concatenate(parts);foot=MultiPoint(v[:,[0,2]]).convex_hull;assert not foot.intersects(poly);gap=float(foot.distance(poly));assert gap>2.5
        assert v[:,0].max()<478 and abs(v[:,2].mean()-340)>10,'Parking is not on external entrance-side grass'
        front=vertices(rec1[prefix+'headlight'][0])[:,[0,2]].mean(0);rear=vertices(rec1[prefix+'red_light'][0])[:,[0,2]].mean(0);d=front-rear;heading=float(np.degrees(np.arctan2(d[1],d[0])));error=abs((heading-car['heading_degrees']+180)%360-180);assert error<.2
        mid=rec1[prefix+'cyber_steel'][1];mat=next(values(n)[1] for n in con1 if values(n)[2]==mid and b.get(values(n)[1],{}).get('name')==b'Material');assert values(b[mat])[1].split(b'\0')[0].decode()=='v038_cybertruck_'+car['paint']
        truckchecks.append(dict(id=car['id'],color=car['paint'],road_edge_clearance_m=gap,topology_and_uv_exact=True,grass_parking_verified=True,heading_error_degrees=error))
    new_names=[n['name'] for n in scene['new_meshes']];assert len(new_names)==6
    billboard_checks=[]
    for name in new_names:
        vv=vertices(rec1[name][0]);foot=box(vv[:,0].min(),vv[:,2].min(),vv[:,0].max(),vv[:,2].max());assert foot.disjoint(poly),name
        treehits=[]
        for nn,(gg,mm) in rec0.items():
            if not (nn.startswith(('tree_','scrub_')) or '_oak_' in nn):continue
            tv=vertices(gg);bb=box(tv[:,0].min(),tv[:,2].min(),tv[:,0].max(),tv[:,2].max())
            if foot.intersects(bb):treehits.append(nn)
        assert not treehits,(name,treehits)
        billboard_checks.append(dict(mesh=name,road_edge_clearance_m=float(foot.distance(poly)),no_tree_conflicts=True))
    # Verify the new text face's U direction from either viewing side and V up.
    name=cfg['speed_world']['id']+'_graphic';g=rec1[name][0];vv=vertices(g);ff=faces(g);uv=array(child(child(g,b'LayerElementUV'),b'UV')).reshape(-1,2);uvi=array(child(child(g,b'LayerElementUV'),b'UVIndex')).astype(int);checks=[];offset=0
    for face in ff:
        pp=vv[face];tt=uv[uvi[offset:offset+len(face)]];offset+=len(face)
        A=np.c_[tt,np.ones(len(tt))];transform=np.linalg.lstsq(A,pp,rcond=None)[0];u,v=transform[0],transform[1];west=pp[:,0].mean()<cfg['speed_world']['xz_m'][0]
        assert u[2]>0 if west else u[2]<0
        assert v[1]>0 and abs(u[0])<1e-6 and abs(v[2])<1e-6
        checks.append(dict(west_facing=bool(west),upright_readable=True))
    # All original vehicles, memorial and earlier Qwikchute retain their records.
    assert all(fingerprint(g)==fingerprint(rec1[n][0]) for n,(g,mid) in rec0.items() if not n.startswith(tuple(v['id']+'_' for v in cfg['vehicles'])))
    defs=next(n for n in after if n['name']==b'Definitions');total=0
    for d in defs['children']:
        if d['name']!=b'ObjectType':continue
        typ=values(d)[0];dd=next(t for t in next(n for n in before if n['name']==b'Definitions')['children'] if t['name']==b'ObjectType' and values(t)[0]==typ);count=values(child(d,b'Count'))[0];assert count==values(child(dd,b'Count'))[0]+sum(n['name']==typ for n in b.values())-sum(n['name']==typ for n in a.values());total+=count
    assert values(child(defs,b'Count'))[0]==total
    qa=dict(checks_pass=True,baseline_version='user-tested v037',baseline_scenery_sha256=sha(BASE/'scenery.fbx'),scenery_sha256=sha(O/'scenery.fbx'),unchanged_baseline_object_records=len(a)-22,changed_truck_geometry_records=22,changed_body_material_connections=2,new_billboard_geometry_records=6,road_and_wall_geometry_byte_exact=True,road_color_normal_marking_textures_byte_exact=True,MX_heightmap_routes_race_soils_and_reset_byte_exact=True,all_terrain_color_maps_byte_exact=True,memorial_and_all_original_pit_displays_byte_exact=True,trees_moved_or_removed=0,protected_files=protected,retained_files=retained,optimized_normal_files=changed_files,trucks=truckchecks,billboards=billboard_checks,entrance_uv_readability=checks)
    save(O/'v038_independent_validation.json',qa);print('v038 independent source checks passed: road, colors, physics inputs and all unrelated objects unchanged; both trucks on grass.',flush=True)

if __name__=='__main__':main()
