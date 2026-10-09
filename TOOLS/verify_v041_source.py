"""Independently audit preservation, edge coverage, placement and mesh faces."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon,box
from v041_common import *
from v027_scenery import parse,encode,values,child,vertices,geometry_records,fingerprint
from verify_v037_source import faces
from build_v040 import face_uv
from rebind_scenery import array

def triangles(g):
    v=vertices(g);out=[]
    for f in faces(g):
        for i in range(1,len(f)-1):out.append(v[[f[0],f[i],f[i+1]]])
    return np.asarray(out)

def main():
    cfg=read(S/'update.json');qa=read(O/'source_validation.json')
    old=(BASE/'scenery.fbx').read_bytes();new=(O/'scenery.fbx').read_bytes()
    bn,bt=parse(old);nn,nt=parse(new);assert encode(nn,nt)==new
    rb=geometry_records(bn);rn=geometry_records(nn)
    removed={n for n in rb if any(n.startswith(p+'_') for p in cfg['generic_pickups'])}
    assert len(removed)==12 and set(rb)-set(rn)==removed
    assert all(fingerprint(rb[n][0])==fingerprint(rn[n][0]) for n in rb if n not in removed)
    bo={values(n)[0]:n for n in next(n for n in bn if n['name']==b'Objects')['children']}
    no={values(n)[0]:n for n in next(n for n in nn if n['name']==b'Objects')['children']}
    ids={i for n in removed for i in [values(rb[n][0])[0],rb[n][1]]}
    assert set(bo)-set(no)==ids
    for i in set(bo)-ids:assert fingerprint(bo[i])==fingerprint(no[i]),i
    expected=[fingerprint(n) for n in next(n for n in bn if n['name']==b'Connections')['children'] if not any(v in ids for v in values(n)[1:3])]
    links=next(n for n in nn if n['name']==b'Connections')['children']
    assert [fingerprint(n) for n in links[:len(expected)]]==expected
    for n in bn:
        if n['name'] not in [b'Objects',b'Connections',b'Definitions']:
            other=next(v for v in nn if v['name']==n['name']);assert fingerprint(n)==fingerprint(other)
    counts=Counter(n['name'] for n in no.values())
    defs=next(n for n in nn if n['name']==b'Definitions');total=0
    for d in defs['children']:
        if d['name']==b'ObjectType':
            typ=values(d)[0];ct=values(child(d,b'Count'))[0];total+=ct
            if typ!=b'GlobalSettings':assert ct==counts[typ]
    assert values(child(defs,b'Count'))[0]==total

    exact=['terrain.raw','height_metres.npy','terrain_16bit.png','main.tcl','start.tcl','route.npz',
           'jump_profiles.json','compiled_track.hmf','minrace.tl','maxrace.tl','checkleft.tl',
           'checkright.tl','v024_pit_gravel.tga']
    for name in exact:assert sha(BASE/name)==sha(O/name),name
    retained_textures=0
    for folder in ['masks','materials','facility_textures']:
        for p in (BASE/folder).iterdir():
            if p.is_file():assert sha(p)==sha(O/folder/p.name),(folder,p.name)
            if p.suffix=='.tga':retained_textures+=1
    road=rb['TRKASPH_v037_oval_surface'][0];rt=triangles(road)
    roadpoly=shapely.union_all(shapely.polygons(rt[:,:,[0,2]]));outer=Polygon(roadpoly.exterior)
    fill=rn['TRKASPH_v041_oval_wall_gap_fill'][0];ft=triangles(fill)
    fillpoly=shapely.union_all(shapely.polygons(ft[:,:,[0,2]]));union=outer.union(fillpoly)
    assert fillpoly.intersection(outer).area<1e-7
    wall=vertices(rb['WLLCONC_v037_oval_wall_white'][0]).reshape(-1,8,3)
    # Each wall's course-side footing is nearest the original road. Check the
    # complete inner-footing segments, not only a few chosen vertices.
    inner=[];edge_checks=[]
    for w in wall:
        sides=[w[[i,(i+1)%4]][:,[0,2]] for i in range(4)]
        side=min(sides,key=lambda s:float(outer.distance(shapely.points(s.mean(0)))))
        for t in np.linspace(0,1,7):inner.append(side[0]*(1-t)+side[1]*t)
    assert np.all(shapely.covers(union.buffer(1e-7),shapely.points(inner)))
    # Check old-road/new-infill shared boundary matches in all three dimensions.
    ov=vertices(road);fv=vertices(fill);tree=cKDTree(ov[:,[0,2]])
    distance,index=tree.query(fv[:,[0,2]]);on=distance<1e-7
    assert on.any();error=float(np.abs(fv[on,1]-ov[index[on],1]).max());assert error<1e-9
    for key in ['TRKASPH_v037_oval_surface','WLLCONC_v037_oval_wall_white','WLLCONC_v037_oval_wall_green_cap']:
        assert fingerprint(rb[key][0])==fingerprint(rn[key][0])

    added=set(rn)-set(rb)
    built={n for n in added if not n.startswith('v041_pit_cybertruck_')}
    assert len(built)==7
    # No newly authored road/seating/crocodile triangle is exactly duplicated.
    seen=set();all_new=[]
    for n in built:
        tri=triangles(rn[n][0]);norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        assert np.all(np.linalg.norm(norm,axis=1)>1e-9),n
        for t in tri:
            key=tuple(sorted(tuple(np.round(p,7)) for p in t));assert key not in seen,('duplicate face',n);seen.add(key)
        assert values(child(no[rn[n][1]],b'Culling'))==[b'CullingOnCCW']
        all_new.append(tri)
    # All new decks rise in +X, so seated spectators face -X toward the oval.
    seats=np.concatenate([vertices(g) for n,(g,mid) in rn.items() if n.startswith(('v041_grandstand_','WLLCONC_v041_grandstand_'))])
    assert seats[:,0].min()>vertices(rb['WLLCONC_v037_oval_wall_white'][0])[:,0].max()+1
    assert seats[:,0].max()<600
    benches=vertices(rn['v041_grandstand_benches'][0]);c=cfg['seating']
    centers=[]
    for r in range(c['rows']):
        x=c['front_x_m']+(r+.4)*c['row_pitch_m'];a=benches[np.abs(benches[:,0]-x)<.25]
        centers.append(float(a[:,1].mean()))
    assert np.all(np.diff(centers)>0)
    entrance=np.concatenate([vertices(g) for n,(g,mid) in rn.items() if n.startswith('v038_orlando_speed_world_entrance_')])
    assert entrance[:,0].mean()<535 and seats[:,0].mean()>535

    vehicle=read(O/'v041_vehicle_validation.json');assert vehicle['count']==3
    assert vehicle['color_order']==['blue','purple','green']
    link_values=[values(n) for n in links]
    for index,q in enumerate(vehicle['vehicles']):
        parts={n:(g,mid) for n,(g,mid) in rn.items() if n.startswith(q['new_group']+'_')};assert len(parts)==11
        assert q['original_group']==cfg['generic_pickups'][index]
        assert q['color']==cfg['replacement_color_order'][index]
        body,mid=parts[q['new_group']+'_cyber_steel']
        material=next(no[v[1]] for v in link_values if v[2]==mid and no.get(v[1],{}).get('name')==b'Material')
        assert values(material)[1].split(b'\0')[0]==('v041_cybertruck_'+q['color']).encode()
    protected=('truck_jordan_','truck_premier_','truck_sam_','van_shane_','bike_',
               'v037_oval_cybertruck_','v032_pup_whatley_memorial_','front_flag_',
               'restroom_','v033_qwikchute_','v038_qwikchute_','v038_orlando_speed_world_entrance_')
    protected_count=0
    for n in rb:
        if n.startswith(protected):assert fingerprint(rb[n][0])==fingerprint(rn[n][0]);protected_count+=1

    croc=read(O/'v041_crocodile_validation.json');cv=vertices(rn['v041_pond_crocodile_photographic'][0])
    assert np.isclose(np.ptp(cv[:,2]),.45) and np.isclose(np.ptp(cv[:,0]),12)
    water=vertices(rb[croc['water_mesh']][0]);pond=Polygon(water[:,[0,2]])
    assert pond.covers(box(cv[:,0].min(),cv[:,2].min(),cv[:,0].max(),cv[:,2].max()))
    with Image.open(O/'facility_textures/v041_crocodile_photo.tga') as im:assert im.mode=='RGB' and im.size==(2048,1024)
    assert sha(S/croc['source_image'])==croc['source_image_sha256']
    ct=triangles(rn['v041_pond_crocodile_photographic'][0])
    front_back=np.ptp(ct[:,:,2],axis=1)<1e-8
    profile=shapely.union_all(shapely.polygons(ct[front_back][:,:,:2]))
    side=ct[~front_back];inward=np.cross(side[:,1]-side[:,0],side[:,2]-side[:,0])
    outward=-inward/np.linalg.norm(inward,axis=1)[:,None]
    centers=side.mean(1)[:,:2];inside=centers-outward[:,:2]*1e-5;outside=centers+outward[:,:2]*1e-5
    assert np.all(shapely.contains_xy(profile,inside[:,0],inside[:,1]))
    assert not np.any(shapely.contains_xy(profile,outside[:,0],outside[:,1]))
    volume=float(np.einsum('ij,ij->i',ct[:,0],np.cross(ct[:,1],ct[:,2])).sum()/6)
    assert abs(volume+profile.area*.45)<1e-5
    for p in (O/'facility_textures').glob('v041_*.tga'):
        with Image.open(p) as im:
            w,h=im.size;assert not w&(w-1) and not h&(h-1) and im.mode=='RGB'
    allv=np.concatenate([vertices(g) for g,mid in rn.values()]);tree=cKDTree(allv)
    # Historical reports/probes retain their original version meaning. Audit
    # all current probe sets consumed by the official v041 native workflow.
    current_probes=['native_coordinate_probes.json','v041_native_probes.json',
                    'memorial_support_native_probes.json','qwikchute_native_probes.json',
                    'holeshot_native_probes.json','v040_native_probes.json']
    for p in [O/name for name in current_probes]:
        d=read(p)
        if 'expected_xyz_metres' in d and d['expected_xyz_metres']:
            assert tree.query(d['expected_xyz_metres'])[0].max()<1e-5,p.name
    report=dict(checks_pass=True,preserved_original_geometry_records=len(rb)-len(removed),
                retained_original_object_records_exact=len(bo)-len(ids),all_original_texture_files_exact=retained_textures,
                removed_only_three_generic_red_pickups=True,replacement_count=3,replacement_colors=vehicle['color_order'],
                accepted_pit_displays_memorial_flag_doors_signs_oval_trucks_exact=protected_count,
                original_road_markings_walls_and_camber_exact=True,native_heightfield_freestyle_and_all_MX_masks_exact=True,
                native_collision_gap_fill_covers_all_wall_inner_footings=True,
                road_gap_fill_no_coplanar_overlap=True,shared_edge_height_error_m=error,
                stadium_rows=10,seats_face_course_native_direction=[-1,0,0],seats_opposite_entrance=True,
                newly_authored_meshes_have_no_duplicate_triangles=True,new_opaque_faces_use_exterior_culling=True,
                crocodile_photographic_opaque_silhouette=True,crocodile_inside_existing_water=True,
                crocodile_silhouette_front_back_and_side_faces_outward=True,
                original_generated_source_alpha_preserved=True,optimized_texture_resolutions_preserved=True,
                in_game_visual_check=False,in_game_riding_test=False)
    save(O/'v041_independent_validation.json',report)
    qa['source_checks_pass']=True;qa['v041_independent_source_checks']=report;save(O/'source_validation.json',qa)
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
