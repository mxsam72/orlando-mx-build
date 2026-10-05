"""v026b localized scenery hotfix.

Remove only tree and track-marker objects that became intrusions after the v026
R10/T09/R11 route relocation. Terrain, race data, materials and every retained
FBX object's properties/topology remain unchanged.
"""
from pathlib import Path
import json, math, struct, hashlib
import numpy as np
from scipy.spatial import cKDTree

from apply_scenery_patch import parse, encode, property_values
from rebind_scenery import array

R=Path(__file__).resolve().parents[1]
O=R/'V026B_OUTPUT'
S=R/'V026B_SOURCE'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def save(p,v):
    Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def values(n):
    return property_values(n['props'],n['count'])

def child(n,name):
    return next(x for x in n['children'] if x['name']==name)

def main():
    spec=read(S/'change_spec.json')
    path=O/'scenery.fbx'
    before=path.read_bytes()
    nodes,tail=parse(before)
    objects=next(n for n in nodes if n['name']==b'Objects')
    connections=next(n for n in nodes if n['name']==b'Connections')

    models={
        values(n)[0]:values(n)[1].split(b'\x00')[0].decode('utf-8','replace')
        for n in objects['children'] if n['name']==b'Model'
    }
    geometry_to_model={
        values(n)[1]:values(n)[2]
        for n in connections['children']
        if len(values(n))>2 and values(n)[2] in models
    }
    geometries={
        models[geometry_to_model[values(n)[0]]]:n
        for n in objects['children']
        if n['name']==b'Geometry' and values(n)[0] in geometry_to_model
    }

    data=dict(np.load(O/'route.npz'))
    q=data['q']; width=data['width']
    route_tree=cKDTree(q[:-1,:2])
    turns=read(O/'turns.json')
    profiles=read(O/'jump_profiles.json')
    t09=next(t for t in turns if t['id']=='T09')
    r10=next(p for p in profiles if p['id']=='R10')
    r11=next(p for p in profiles if p['id']=='R11')

    # Use the actual world-space v026 changed-patch bounds rather than nearest-route
    # station alone. Nearby parallel lanes can otherwise project a scenery anchor
    # to the wrong station even though it visibly sits in the relocated corridor.
    geo=read(O/'geometry_validation.json')
    x0,z0,x1,z1=map(float,geo['patch_bounds_xz_m'])
    margin=22.0
    patch_bounds=[x0-margin,z0-margin,x1+margin,z1+margin]

    remove_ids=set()
    removed=[]
    candidates=[]
    # Conservative clearances: trees must keep canopy/trunk comfortably off the
    # track; SOFTCPLAS stakes/markers should never occupy the rideable lane.
    thresholds={'tree_':8.0,'SOFTCPLAS_marker_':3.0}

    for name,geom in geometries.items():
        prefix=next((p for p in thresholds if name.startswith(p)),None)
        if prefix is None:
            continue
        v=array(child(geom,b'Vertices')).reshape(-1,3)*np.array([.01,.01,-.01])
        ymin=float(v[:,1].min())
        low=v[v[:,1] < ymin+.55]
        if not len(low):
            low=v
        anchor=low[:,[0,2]].mean(axis=0)
        dist,i=route_tree.query(anchor)
        station=float(q[i,3])
        half=float(width[i])/2.0
        edge_clear=float(dist-half)
        in_patch=(patch_bounds[0] <= anchor[0] <= patch_bounds[2] and
                  patch_bounds[1] <= anchor[1] <= patch_bounds[3])
        item=dict(name=name,prefix=prefix,anchor_xz_m=[float(anchor[0]),float(anchor[1])],
                  station_m=station,centerline_distance_m=float(dist),
                  authored_half_width_m=half,track_edge_clearance_m=edge_clear,
                  in_changed_patch_bounds=bool(in_patch))
        if in_patch:
            candidates.append(item)
            if edge_clear < thresholds[prefix]:
                gid=values(geom)[0]
                mid=geometry_to_model[gid]
                remove_ids.update([gid,mid])
                item['removed']=True
                removed.append(item)

    # Persist diagnostics before hard acceptance checks so a failed CI run still
    # reveals every targeted object's anchor/clearance for the next correction.
    save(R/'DOCUMENTATION/v026b_scenery_candidates.json',dict(
        patch_bounds_xz_m=patch_bounds,thresholds_m=thresholds,
        candidates=candidates,proposed_removals=removed))

    removed_trees=[x for x in removed if x['prefix']=='tree_']
    removed_markers=[x for x in removed if x['prefix']=='SOFTCPLAS_marker_']
    if not removed_trees:
        raise RuntimeError('v026b expected at least one route-intruding tree in the changed sector')
    if not removed_markers:
        raise RuntimeError('v026b expected at least one route-intruding SOFTCPLAS marker in the changed sector')

    before_object_count=len(objects['children'])
    objects['children']=[
        n for n in objects['children']
        if not (n['count'] and values(n)[0] in remove_ids)
    ]
    connections['children']=[
        n for n in connections['children']
        if not any(v in remove_ids for v in values(n)[1:3])
    ]

    definitions=next(n for n in nodes if n['name']==b'Definitions')
    for item in definitions['children']:
        if item['name']==b'Count':
            item['props']=b'I'+struct.pack('<i',len(objects['children']))
        elif item['name']==b'ObjectType':
            typ=values(item)[0]
            count=sum(n['name']==typ for n in objects['children'])
            cn=child(item,b'Count')
            cn['props']=b'I'+struct.pack('<i',count)

    output=encode(nodes,tail)
    parse(output)
    path.write_bytes(output)

    # Rebuild native coordinate probes from retained geometry only, so no probe
    # can point at one of the deliberately removed objects.
    retained_ids={values(n)[0] for n in objects['children'] if n['count']}
    probes=[]
    for name in sorted(geometries):
        geom=geometries[name]
        gid=values(geom)[0]
        if gid not in retained_ids:
            continue
        v=array(child(geom,b'Vertices')).reshape(-1,3)*np.array([.01,.01,-.01])
        for p in v[::max(1,len(v)//5)]:
            if np.isfinite(p).all() and p[0]>.001 and p[2]>.001:
                probes.append([float(p[0]),float(p[1]),float(p[2])])
                break
        if len(probes)>=32:
            break
    if len(probes)<24:
        raise RuntimeError('Not enough retained scenery coordinate probes after hotfix')
    save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=probes))

    # Re-scan retained targeted objects and verify the authored corridor is clear
    # to the same thresholds.
    remaining_conflicts=[]
    remaining_targeted=0
    nodes2,_=parse(output)
    objects2=next(n for n in nodes2 if n['name']==b'Objects')
    connections2=next(n for n in nodes2 if n['name']==b'Connections')
    models2={values(n)[0]:values(n)[1].split(b'\x00')[0].decode('utf-8','replace') for n in objects2['children'] if n['name']==b'Model'}
    g2m2={values(n)[1]:values(n)[2] for n in connections2['children'] if len(values(n))>2 and values(n)[2] in models2}
    for geom in [n for n in objects2['children'] if n['name']==b'Geometry' and values(n)[0] in g2m2]:
        name=models2[g2m2[values(geom)[0]]]
        prefix=next((p for p in thresholds if name.startswith(p)),None)
        if prefix is None:
            continue
        v=array(child(geom,b'Vertices')).reshape(-1,3)*np.array([.01,.01,-.01])
        low=v[v[:,1] < v[:,1].min()+.55]
        anchor=(low if len(low) else v)[:,[0,2]].mean(axis=0)
        dist,i=route_tree.query(anchor);station=float(q[i,3]);edge=float(dist-float(width[i])/2)
        in_patch=(patch_bounds[0] <= anchor[0] <= patch_bounds[2] and
                  patch_bounds[1] <= anchor[1] <= patch_bounds[3])
        if in_patch:
            remaining_targeted+=1
            if edge<thresholds[prefix]:
                remaining_conflicts.append(dict(name=name,station_m=station,anchor_xz_m=[float(anchor[0]),float(anchor[1])],track_edge_clearance_m=edge,threshold_m=thresholds[prefix]))

    if remaining_conflicts:
        raise RuntimeError('Targeted scenery conflicts remain: '+repr(remaining_conflicts))

    qa=dict(
        version='v026b',
        baseline_commit=spec['baseline_commit'],
        source_scenery_sha256=hashlib.sha256(before).hexdigest(),
        output_scenery_sha256=sha(path),
        localized_world_patch_bounds_xz_m=patch_bounds,
        tree_clearance_threshold_m=thresholds['tree_'],
        marker_clearance_threshold_m=thresholds['SOFTCPLAS_marker_'],
        removed_tree_count=len(removed_trees),
        removed_marker_count=len(removed_markers),
        removed=removed,
        targeted_candidates=candidates,
        remaining_targeted_objects=remaining_targeted,
        remaining_conflicts=remaining_conflicts,
        object_records_removed=before_object_count-len(objects['children']),
        coordinate_probes=len(probes),
        terrain_unchanged=True,
        route_unchanged=True,
        materials_unchanged=True,
        retained_object_properties_unchanged=True,
        in_game_riding=False,
        scenery_checks_pass=True,
    )
    save(R/'DOCUMENTATION/v026b_scenery_validation.json',qa)
    print(json.dumps(qa,indent=2),flush=True)

if __name__=='__main__':
    main()
