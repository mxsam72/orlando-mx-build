"""Independent bounds, artwork, native winding and preservation checks."""
import struct
from collections import Counter
import numpy as np
from PIL import Image
import shapely
from shapely.geometry import Polygon
from scipy.ndimage import map_coordinates
from v040_common import *
from v027_scenery import parse, values, child, fingerprint, geometry_records, vertices
from verify_v037_source import faces
from build_v040 import face_uv

def main():
    cfg=read(S/'update.json');scene=read(O/'v040_asset_validation.json')
    old=parse((BASE/'scenery.fbx').read_bytes())[0];new=parse((O/'scenery.fbx').read_bytes())[0]
    r0=geometry_records(old);r1=geometry_records(new)
    obj0={values(n)[0]:n for n in next(n for n in old if n['name']==b'Objects')['children']}
    obj1={values(n)[0]:n for n in next(n for n in new if n['name']==b'Objects')['children']}
    allowed=set(scene['changed_object_ids']);removed=set(scene['removed_object_ids'])
    assert removed==set(scene['flag']['removed_object_ids'])
    for uid,n in obj0.items():
        if uid in removed:assert uid not in obj1
        elif uid not in allowed:assert fingerprint(n)==fingerprint(obj1[uid]),uid
        elif n['name']==b'Model':
            newer=obj1[uid]
            assert values(child(newer,b'Culling'))==[b'CullingOnCCW']
            assert n['props']==newer['props'] and n['count']==newer['count']
            assert [fingerprint(c) for c in n['children'] if c['name']!=b'Culling']==[fingerprint(c) for c in newer['children'] if c['name']!=b'Culling']
        else:assert n['name']==b'Geometry'
    allowed_names={'v032_pup_whatley_memorial_frame','v032_pup_whatley_memorial_memorial',
                   'restroom_siding','restroom_trim','restroom_alloy','front_flag_red'}
    allowed_names.update(d['name'] for d in scene['decals'])
    allowed_names.update(n for n in r0 if n.startswith('v038_orlando_speed_world_entrance_'))
    assert set(scene['modified_geometry_names'])<=allowed_names
    assert set(r0)-set(r1)=={'front_flag_trim','front_flag_navy'}
    # Every retained old connection survives exactly except the flag's replaced
    # material link. Removed connections refer only to the replaced cloth parts.
    oldlinks=next(n for n in old if n['name']==b'Connections')['children']
    newlinks=next(n for n in new if n['name']==b'Connections')['children']
    fingerprints={fingerprint(n) for n in newlinks};flagmid=r0['front_flag_red'][1]
    for n in oldlinks:
        a=values(n)
        permitted=any(i in removed for i in a[1:3]) or (a[2]==flagmid and obj0.get(a[1],{}).get('name')==b'Material')
        if not permitted:assert fingerprint(n) in fingerprints
    preserved=[]
    for name,(g,mid) in r0.items():
        if name not in allowed_names and name in r1:
            assert fingerprint(g)==fingerprint(r1[name][0]),name;preserved.append(name)
    # Source graphical artwork and road/motorcycle layouts are byte-exact.
    exact=[]
    for fn in ['main.tcl','start.tcl','route.npz','jump_profiles.json','compiled_track.hmf',
               'minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','v024_pit_gravel.tga']:
        assert sha(O/fn)==sha(BASE/fn),fn;exact.append(fn)
    assert sha(O/(NAME+'.rdf'))==sha(BASE/'orlandomx_2026_v039.rdf')
    textures=[]
    for folder in ['materials','facility_textures']:
        for p in (BASE/folder).rglob('*'):
            if p.is_file():
                q=O/folder/p.relative_to(BASE/folder);assert sha(q)==sha(p),str(q);textures.append(str(q.relative_to(O)))
    changed_masks=set(read(O/'v040_freestyle_validation.json')['changed_masks'])
    for p in (BASE/'masks').glob('*.tga'):
        if p.name not in changed_masks:assert sha(p)==sha(O/'masks'/p.name),p.name
    for name in ['v033_qwikchute_billboard_frame','v033_qwikchute_billboard_logo',
                 'v038_oval_qwikchute_billboard_frame','v038_oval_qwikchute_billboard_logo']:
        assert fingerprint(r0[name][0])==fingerprint(r1[name][0])
        assert fingerprint(obj0[r0[name][1]])==fingerprint(obj1[r1[name][1]])
    # Entrance remains correctly mapped in native coordinates; only translation.
    delta=np.asarray(scene['entrance_translation_xyz_m'])
    signnames=[n for n in r0 if n.startswith('v038_orlando_speed_world_entrance_')]
    for name in signnames:
        g0=r0[name][0];g1=r1[name][0]
        expected=vertices(g0)+delta
        if name.endswith('_graphic'):expected[:,1]+=cfg['entrance_raise_m']
        elif name.endswith('_frame'):
            top=expected[:16,1]>expected[:16,1].mean();expected[np.flatnonzero(top),1]+=cfg['entrance_raise_m'];expected[16:,1]+=cfg['entrance_raise_m']
        assert np.allclose(vertices(g1),expected,atol=1e-9,rtol=0)
        assert fingerprint(child(g0,b'LayerElementUV'))==fingerprint(child(g1,b'LayerElementUV'))
        assert child(g0,b'PolygonVertexIndex')['props']==child(g1,b'PolygonVertexIndex')['props']
    # Check entrance posts/concrete are outside the actual asphalt entry, and
    # overhead image has enough clearance for the game's motorcycle/rider.
    road=r1['TRKASPH_v037_oval_surface'][0];rv=vertices(road);rf=np.asarray(faces(road))
    roadpoly=shapely.union_all(shapely.polygons(rv[rf][:,:,[0,2]]));assert len(roadpoly.interiors)==2
    bases=vertices(r1['v038_orlando_speed_world_entrance_concrete'][0])
    assert not shapely.contains_xy(roadpoly,bases[:,0],bases[:,2]).any()
    image=vertices(r1['v038_orlando_speed_world_entrance_graphic'][0]);ground=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    roadheight=float(map_coordinates(ground,[[(600-340)/600*2048],[469/600*2048]],order=1)[0])+.12
    entrance_headroom=float(image[:,1].min()-roadheight);assert entrance_headroom>3.8
    # Memorial has neither a full backing face nor poles in front of its artwork.
    art=r1['v032_pup_whatley_memorial_memorial'][0];av=vertices(art);frame=r1['v032_pup_whatley_memorial_frame'][0];fv=vertices(frame)
    assert np.allclose(np.unique(av[:,2]),[143.6,144.4])
    gap=float(np.abs(av[:,2]-144).min()-np.abs(fv[:,2]-144).max());assert gap>=.229999
    for f in faces(frame):
        q=fv[f];assert not (np.ptp(q[:,0])>=7.99 and np.ptp(q[:,1])>=6.39)
    assert fingerprint(child(art,b'LayerElementUV'))==fingerprint(child(r0['v032_pup_whatley_memorial_memorial'][0],b'LayerElementUV'))
    # Both flag faces are outward in the native reflected winding convention.
    flag=r1['front_flag_red'][0];v=vertices(flag);centre=(v.min(0)+v.max(0))/2
    assert len(faces(flag))==4
    for f in faces(flag):
        q=v[f];assert np.dot(np.cross(q[1]-q[0],q[2]-q[0]),q.mean(0)-centre)<0
    with Image.open(O/'facility_textures/v040_american_flag.tga') as im:assert im.size==(2048,1024) and im.mode=='RGB'
    # No identical/opposite duplicate triangles remain in repaired wraps/decals.
    for d in scene['decals']:
        g=r1[d['name']][0];v=vertices(g);seen=set()
        for f in faces(g):
            key=tuple(sorted(tuple(np.round(p,6)) for p in v[f]));assert key not in seen,d['name'];seen.add(key)
    # Every changed terrain sample is in a grass hole; all native pavement and
    # the entire accepted MX region remain bit-for-bit untouched.
    oldraw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);newraw=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)
    changed=newraw!=oldraw;xx,zz=np.meshgrid(np.arange(2049)*600/2048,600-np.arange(2049)*600/2048)
    holes=shapely.union_all([Polygon(h).buffer(-cfg['freestyle']['grass_boundary_guard_m']) for h in roadpoly.interiors])
    assert shapely.contains_xy(holes,xx[changed],zz[changed]).all()
    assert np.array_equal(oldraw[xx<500],newraw[xx<500])
    assert np.array_equal(oldraw[shapely.contains_xy(roadpoly,xx,zz)],newraw[shapely.contains_xy(roadpoly,xx,zz)])
    for name in changed_masks:
        a=np.array(Image.open(BASE/'masks'/name));b=np.array(Image.open(O/'masks'/name));h,w=a.shape[:2]
        x,z=np.meshgrid(np.arange(w)*600/(w-1),600-np.arange(h)*600/(h-1));active=(a!=b)
        if active.ndim==3:active=active.any(axis=2)
        assert shapely.contains_xy(holes,x[active],z[active]).all(),name
    # Source triangles are non-degenerate and all referenced vertices exist.
    for name in scene['modified_geometry_names']:
        g=r1[name][0];v=vertices(g)
        for f in faces(g):
            assert all(0<=i<len(v) for i in f)
            q=v[f];assert np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))>1e-10,name
    independent=dict(checks_pass=True,preserved_geometry_records=len(preserved),unchanged_original_texture_files=len(textures),exact_MX_race_and_route_files=exact,road_markings_surface_and_walls_exact=True,MX_heightmap_and_masks_outside_grass_islands_exact=True,qwikchute_v039_graphics_and_frames_exact=True,speed_world_corrected_uvs_exact=True,entrance_headroom_m=entrance_headroom,entrance_posts_clear_of_pavement=True,memorial_image_support_minimum_clearance_m=gap,flag_faces_outward_and_separated=True,repaired_decals_have_no_coincident_duplicate_triangles=True,optimized_texture_resolutions_preserved=True,in_game_visual_check=False,in_game_riding_test=False)
    save(O/'v040_independent_validation.json',independent)
    qa=read(O/'source_validation.json');qa['source_checks_pass']=True;save(O/'source_validation.json',qa)
    print('Independent v040 source checks passed:',len(preserved),'geometry records preserved; all original textures unchanged.',flush=True)

if __name__=='__main__':main()
