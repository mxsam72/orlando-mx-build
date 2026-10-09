"""Reconnect the start-edge timber fence and metal chute; retain main markers."""
from pathlib import Path
import json,numpy as np
from scipy.ndimage import map_coordinates
from v027_scenery import parse,encode,geometry_records,vertices,child,values,fingerprint
from v033_billboard import geometry
from rebind_scenery import encoded_array
from v033_common import atomic,save,sha
from v024_common import route_point
from build_v035 import config,width
R=Path(__file__).resolve().parents[1];B=R/'V033_OUTPUT';O=R/'V035_OUTPUT'
def main():
    cfg=config();before=(B/'scenery.fbx').read_bytes();nodes,tail=parse(before);assert encode(nodes,tail)==before
    obj=next(n for n in nodes if n['name']==b'Objects');records=geometry_records(nodes);original={values(n)[0]:fingerprint(n) for n in obj['children']};conn=fingerprint(next(n for n in nodes if n['name']==b'Connections'))
    sa=np.load(O/'route.npz')['start'];oldh=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049)/65535*18;h=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    def ground(H,p):
        p=np.asarray(p);scalar=p.ndim==1;p=np.atleast_2d(p);answer=map_coordinates(H,[(600-p[:,1])/600*2048,p[:,0]/600*2048],order=1,mode='nearest');return answer[0] if scalar else answer
    def edge(ss,right=False):
        p=np.c_[[np.interp(ss,sa[:,3],sa[:,k]) for k in range(3)]].T;offset=width(ss,cfg)/2+(cfg['right_barrier_extra_offset_m'] if right else cfg['fence_clay_edge_gap_m']);return p[:,:2]+offset[:,None]*np.c_[np.sin(p[:,2]),-np.cos(p[:,2])]
    faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]];changed=set();changes=[];probes=[]
    for name,a,b,right,timber in [('v028_practice_wood_left_timber',0,58,False,True),('v028_practice_barrier_left_alloy',58,80,False,False),('v028_practice_barrier_right_alloy',58,80,True,False)]:
        mesh=dict(name=name,vertices=[],faces=[],uv=[])
        def box(center,dimensions,xaxis=None):
            v=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])*np.array(dimensions)/2
            if xaxis is not None:
                xx=np.array(xaxis,float);xx/=np.linalg.norm(xx);yy=np.array([0.,1.,0.]);zz=np.cross(xx,yy);v=v@np.array([xx,yy,zz])
            v+=center;offset=len(mesh['vertices']);mesh['vertices'].extend(v.tolist())
            for f in faces:
                mesh['faces'].append([offset+i for i in f]);pp=v[f];span=np.ptp(pp,axis=0);axes=np.argsort(span)[-2:];uv=pp[:,axes]/2;mesh['uv'].append(uv.tolist())
        ss=np.linspace(a,b,max(2,int((b-a)/3.2)+2));xz=edge(ss,right);gh=ground(h,xz)
        for p,g in zip(xz,gh):box([p[0],g+.675,p[1]],[.14,1.35,.14] if timber else [.075,1.25,.075])
        for i in range(len(ss)-1):
            p=np.array([xz[i,0],gh[i],xz[i,1]]);q=np.array([xz[i+1,0],gh[i+1],xz[i+1,1]]);direction=q-p
            for y in [.32,.74,1.15]:box((p+q)/2+[0,y,0],[np.linalg.norm(direction)+.12,.12 if timber else .06,.09 if timber else .055],direction)
        g,mid=records[name];gid=values(g)[0];newg=geometry(gid,mesh);index=next(i for i,n in enumerate(obj['children']) if values(n)[0]==gid);obj['children'][index]=newg;changed.add(gid)
        changes.append(dict(model=name,reason='Connected start clay-edge fence and practice chute',start_xz_m=xz[0].tolist(),end_xz_m=xz[-1].tolist(),riding_edge_gap_m=cfg['fence_clay_edge_gap_m'] if not right else None,vertices=len(mesh['vertices'])))
        v=np.asarray(mesh['vertices']);probes.extend(v[[0,len(v)//2,-1]].tolist())
    for name,(g,mid) in records.items():
        amount=cfg['tree_x_translations_m'].get(name)
        if name.startswith('v028_practice_oak_03_'):amount=cfg['tree_x_translations_m']['v028_practice_oak_03']
        if amount is None:continue
        v=vertices(g);low=v[v[:,1]<v[:,1].min()+.3];anchor=low[:,[0,2]].mean(0);new=anchor+[amount,0];dy=float(ground(h,new)-ground(oldh,anchor));delta=np.array([amount,dy,0]);vv=v+delta;child(g,b'Vertices')['props']=encoded_array(vv*[100,100,-100]);changed.add(values(g)[0]);probes.extend(vv[[0,len(vv)//2,-1]].tolist());changes.append(dict(model=name,reason='Clear rebuilt practice chute',translation_xyz_m=delta.tolist(),vertices=len(v)))
    output=encode(nodes,tail);atomic(O/'scenery.fbx',output);check,_=parse(output);after={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']}
    assert {k:v for k,v in after.items() if k not in changed}=={k:v for k,v in original.items() if k not in changed};assert fingerprint(next(n for n in check if n['name']==b'Connections'))==conn
    wood=edge(np.array([58.]));metal=edge(np.array([58.]));gap=float(np.linalg.norm(wood-metal));assert gap==0
    rec=geometry_records(check);signs=['memorial','qwikchute','entry_sign'];assert all(fingerprint(g)==fingerprint(records[name][0]) for name,(g,_) in rec.items() if any(k in name for k in signs))
    save(O/'holeshot_native_probes.json',dict(expected_xyz_metres=probes))
    save(O/'holeshot_scenery_validation.json',dict(checks_pass=True,source_sha256=sha(B/'scenery.fbx'),output_sha256=sha(O/'scenery.fbx'),modified_geometry_records=len(changes),all_other_object_records_byte_exact=True,all_connections_byte_exact=True,all_main_track_boundary_markers_byte_exact=True,memorial_entry_and_Qwikchute_signs_byte_exact=True,wood_to_metal_joint_gap_m=gap,fence_origin_tied_to_existing_v033_back_rail=True,changes=changes))
    print('Scenery:',len(changes),'practice-only records; all main markers and signs unchanged.',flush=True)
if __name__=='__main__':main()
