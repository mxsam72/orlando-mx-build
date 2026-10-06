"""Audit complete retained foliage against the corrected practice approach.

FBX positions are the accepted world-bound metre coordinates. Triangles are
subdivided to <=0.5 m edges so a canopy spanning a lane is detected even when
none of its original vertices lands inside it. Only recorded intruders are
removed; retained object records and connections remain byte exact.
"""
from v027_scenery import parse, encode, values, child, fingerprint, geometry_records, vertices, remove_objects
from rebind_scenery import array
from v028_common import *

def dense_geometry(g,step=.5):
    v=vertices(g); idx=array(child(g,b'PolygonVertexIndex')); faces=[]; face=[]
    for item in idx:
        item=int(item);face.append(item if item>=0 else -item-1)
        if item<0:
            faces.extend(v[[face[0],face[k],face[k+1]]] for k in range(1,len(face)-1));face=[]
    tri=np.asarray(faces); chunks=[v]
    for depth in range(10):
        length=np.max(np.linalg.norm(tri-np.roll(tri,1,axis=1),axis=2),axis=1)
        small=tri[length<=step];chunks.append(small.reshape(-1,3));tri=tri[length>step]
        if not len(tri):break
        a,b,c=tri[:,0],tri[:,1],tri[:,2];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
        tri=np.concatenate([np.stack([a,ab,ca],1),np.stack([ab,b,bc],1),np.stack([ca,bc,c],1),np.stack([ab,bc,ca],1)])
    assert not len(tri),'Unbounded scenery triangle'
    return np.concatenate(chunks)

def routes():
    d=dict(np.load(O/'route.npz'));cfg=read(S/'pit_access.json');a=access_layout(d['start'],cfg)
    return [('practice',a['lane'],cfg['practice_width_m']),('pit_connector',a['connector'],cfg['connector_width_m'])]

def scan(nodes):
    cfg=read(S/'pit_access.json');h=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    lines=routes();trees=[cKDTree(q[:,:2]) for _,q,_ in lines];hits=[];audited=[]
    for name,(g,mid) in geometry_records(nodes).items():
        v=vertices(g);center=(v[:,[0,2]].min(0)+v[:,[0,2]].max(0))/2
        radius=np.linalg.norm(v[:,[0,2]]-center,axis=1).max()
        if all(t.query(center)[0]>radius+width/2+cfg['retained_tree_lateral_margin_m']+1 for t,(_,_,width) in zip(trees,lines)):continue
        points=dense_geometry(g);low=points[points[:,1]-ground(h,points[:,[0,2]])<cfg['minimum_rider_headroom_m']]
        conflicts=[]
        for label,q,width in lines:
            dist,lat,station,half,valid=route_projection(low[:,[0,2]],q,np.full(len(q),width),True)
            # Round endpoint caps belong to the pit/practice approach as well.
            dist=np.minimum(dist,np.minimum(np.linalg.norm(low[:,[0,2]]-q[0,:2],axis=1),np.linalg.norm(low[:,[0,2]]-q[-1,:2],axis=1)))
            mask=dist<width/2+cfg['retained_tree_lateral_margin_m']
            if mask.any():
                conflicts.append(dict(route=label,intruding_dense_samples=int(mask.sum()),minimum_headroom_m=float((low[mask,1]-ground(h,low[mask][:,[0,2]])).min()),minimum_centerline_distance_m=float(dist[mask].min())))
        item=dict(name=name,geometry_id=values(g)[0],model_id=mid,dense_samples=len(points),conflicts=conflicts)
        audited.append(item)
        if conflicts:hits.append(item)
    return hits,audited

def main():
    before=(O/'scenery.fbx').read_bytes();nodes,_=parse(before);hits,audited=scan(nodes)
    unexpected=[x for x in hits if not x['name'].startswith(('tree_','SOFTCPLAS_marker_'))]
    assert not unexpected,'Existing custom/facility asset intrudes: '+repr(unexpected)
    spec=read(S/'retained_clearance_selection.json')
    assert sorted(x['name'] for x in hits)==sorted(spec['expected_removals']),'Review the explicit retained-object selection before building'
    after,preservation=remove_objects(before,hits);nodes,_=parse(after);remaining,audit_after=scan(nodes)
    assert not remaining,'Retained low scenery still intersects practice/connector'
    (O/'scenery.fbx').write_bytes(after)
    save(O/'retained_access_clearance_validation.json',dict(version='v028',checks_pass=True,removed=hits,remaining_conflicts=remaining,audited_models=len(audited),audited_after_models=len(audit_after),dense_triangle_max_edge_m=.5,rider_headroom_m=spec['rider_headroom_m'],lateral_margin_m=spec['lateral_margin_m'],**preservation))
    print('v028 retained practice clearance verified:',[x['name'] for x in hits],flush=True)

if __name__=='__main__':main()
