"""Rebind the baseline scenery, move spectator fence, clear new start corridor."""
import math, re
import numpy as np
from scipy.spatial import cKDTree
from v015_common import *
from apply_scenery_patch import parse, encode, property_values
from rebind_scenery import array, encoded_array

def values(n): return property_values(n['props'],n['count'])
def child(n,name): return next(x for x in n['children'] if x['name']==name)
def normals(geom, vertices):
    indices=array(child(geom,b'PolygonVertexIndex')); faces=[]; face=[]; per=[]
    for k in indices:
        face.append(int(-k-1 if k<0 else k))
        if k<0:
            p=vertices[face]; n=np.cross(p[1]-p[0],p[2]-p[0]); n/=max(np.linalg.norm(n),1e-12)
            per.extend([n]*len(face)); face=[]
    per=np.asarray(per)
    for layer in geom['children']:
        if layer['name']!=b'LayerElementNormal':continue
        node=child(layer,b'Normals'); reference=values(child(layer,b'ReferenceInformationType'))[0]
        assert values(child(layer,b'MappingInformationType'))[0]==b'ByPolygonVertex'
        if reference==b'IndexToDirect':
            inds=array(child(layer,b'NormalsIndex')); out=np.zeros_like(array(node).reshape(-1,3)); np.add.at(out,inds,per)
            lengths=np.linalg.norm(out,axis=1); good=lengths>1e-12;out[good]/=lengths[good,None]
            out[~good]=array(node).reshape(-1,3)[~good]
        else:
            assert reference==b'Direct';out=per
        node['props']=encoded_array(out)

def main():
    # Use the existing tested FBX property rewriter to bind every retained mesh.
    source=(R/'TOOLS/rebind_v009_scenery.py').read_text(encoding='utf-8')
    source=source.replace('V009_OUTPUT','V015_OUTPUT').replace('v009_scenery_validation','v015_rebind_validation')
    ns={'__name__':'v015_rebind','__file__':__file__};exec(compile(source,str(R/'TOOLS/rebind_v009_scenery.py'),'exec'),ns,ns);ns['main']()
    data=(O/'scenery.fbx').read_bytes();nodes,tail=parse(data);assert encode(nodes,tail)==data
    objects=next(n for n in nodes if n['name']==b'Objects');connections=next(n for n in nodes if n['name']==b'Connections')
    models={values(n)[0]:values(n)[1].split(b'\x00')[0].decode() for n in objects['children'] if n['name']==b'Model'}
    geometry_to_model={values(n)[1]:values(n)[2] for n in connections['children'] if len(values(n))>2 and values(n)[2] in models}
    geometries={models[geometry_to_model[values(n)[0]]]:n for n in objects['children'] if n['name']==b'Geometry' and values(n)[0] in geometry_to_model}
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE; cfg=read(O/'facility_layout.json')
    points=np.array(cfg['fence_polyline_xz']);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    posts=sorted([name for name in geometries if name.startswith('fence_post_')],key=lambda n:int(n.rsplit('_',1)[1]))
    assert len(posts)>10
    positions=np.c_[np.interp(np.linspace(0,ss[-1],len(posts)),ss,points[:,0]),np.interp(np.linspace(0,ss[-1],len(posts)),ss,points[:,1])]
    elev=ground(H,positions);changed=[]
    for name,geom in geometries.items():
        if not name.startswith(('fence_post_','fence_rail_')):continue
        vn=child(geom,b'Vertices');v=array(vn).reshape(-1,3);native=v*np.array([.01,.01,-.01]); center=native.mean(0)
        if name.startswith('fence_post_'):
            i=int(name.rsplit('_',1)[1]); native[:,0]+=positions[i,0]-center[0];native[:,2]+=positions[i,1]-center[2]
            native[:,1]+=elev[i]-native[:,1].min()
        else:
            m=re.match(r'fence_rail_(\d+)_(.+)',name);i=int(m[1]);level=float(m[2]);assert i>0
            a=np.array([positions[i-1,0],elev[i-1]+level,positions[i-1,1]]);b=np.array([positions[i,0],elev[i]+level,positions[i,1]])
            _,_,vh=np.linalg.svd(native-center,full_matrices=False);old_axis=vh[0];old_up=np.cross(old_axis,[0,1,0]);old_up/=np.linalg.norm(old_up);old_third=np.cross(old_axis,old_up)
            basis=np.array([old_axis,old_up,old_third]).T;local=(native-center)@basis;length=np.ptp(local[:,0]);local[:,0]*=np.linalg.norm(b-a)/length
            new_axis=(b-a)/np.linalg.norm(b-a);new_up=np.cross(new_axis,[0,1,0]);new_up/=np.linalg.norm(new_up);new_third=np.cross(new_axis,new_up)
            native=(a+b)/2+local@np.array([new_axis,new_up,new_third])
        v=native*np.array([100,100,-100]);vn['props']=encoded_array(v);normals(geom,v);changed.append(name)
    # Remove only trees/track stakes intruding on the newly opened route. Keep
    # buildings and other fixed assets; fail for review if any block the apron.
    sa=np.load(O/'route.npz')['start'];tree=cKDTree(sa[:,:2]);remove=set();removed=[];blocked=[]
    for name,geom in geometries.items():
        if name in changed:continue
        v=array(child(geom,b'Vertices')).reshape(-1,3)*np.array([.01,.01,-.01]);low=v[v[:,1]<v[:,1].min()+.5]
        anchor=low[:,[0,2]].mean(0);dist,i=tree.query(anchor);half=np.interp(sa[i,3],*np.array(cfg['start_width_knots']).T)/2
        if dist>half+3 or sa[i,3]>sa[-1,3]-12:continue
        if name.startswith(('tree_','SOFTCPLAS_marker_','tuft_','grass_','brush_')):
            gid=values(geom)[0];remove.update([gid,geometry_to_model[gid]]);removed.append(name)
        elif name.startswith(('WLLCONC_','canopy_','utility_pole_','crossarm_')):blocked.append(name)
    if blocked:raise RuntimeError('New start corridor intersects fixed objects: '+str(blocked))
    objects['children']=[n for n in objects['children'] if not (n['count'] and values(n)[0] in remove)]
    connections['children']=[n for n in connections['children'] if not any(v in remove for v in values(n)[1:3])]
    # Definitions counts describe object records; keep them consistent after removals.
    import struct
    definitions=next(n for n in nodes if n['name']==b'Definitions')
    for item in definitions['children']:
        if item['name']==b'Count':item['props']=b'I'+struct.pack('<i',len(objects['children']))
        elif item['name']==b'ObjectType':
            typ=values(item)[0];count=sum(n['name']==typ for n in objects['children']);cn=child(item,b'Count');cn['props']=b'I'+struct.pack('<i',count)
    output=encode(nodes,tail);parse(output);(O/'scenery.fbx').write_bytes(output)
    # Include relocated fence vertices among the compiler coordinate probes.
    probes=[]
    for name in posts[::max(1,len(posts)//8)]:
        v=array(child(geometries[name],b'Vertices')).reshape(-1,3)[0]*np.array([.01,.01,-.01]);probes.append(v.tolist())
    original=read(O/'native_coordinate_probes.json')['expected_xyz_metres'];probes+=original[:24]
    save(O/'native_coordinate_probes.json',dict(expected_xyz_metres=probes))
    q,w=route();qt=cKDTree(q[:,:2]);dist,idx=qt.query(positions);clear=dist-w[idx]/2
    gate_left=min(g['x'] for g in cfg['grid']); assert positions[:,0].max()<gate_left and clear.min()>2
    qa=dict(source_sha256=sha(R/'BUILD/v009_baseline/scenery.fbx'),output_sha256=sha(O/'scenery.fbx'),fence_models_moved=len(changed),fence_posts=len(posts),fence_length_m=float(ss[-1]),fence_min_track_edge_clearance_m=float(clear.min()),fence_frontage='T14 -> R01 -> T01; gate to right',removed_start_obstructions=removed,fixed_object_conflicts=blocked,coordinate_probes=len(probes),native_compilation=False,in_game_riding=False,scenery_checks_pass=True)
    save(R/'DOCUMENTATION/v015_scenery_validation.json',qa);print(qa)
if __name__=='__main__':main()
