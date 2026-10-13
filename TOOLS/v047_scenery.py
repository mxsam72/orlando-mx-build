"""Replace only tree meshes with the user's approved A/B prototypes.

Transforms the exact approved FBX geometry, per-corner UVs and custom normals.
All near-course trees remain. Distant density is reduced before assigning an
exact rounded 85/15 mix. No filled low-detail crown or new collision is added.
"""
import copy,re,struct
from collections import Counter
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from v047_common import *
from v027_scenery import parse,encode,values,child,vertices,geometry_records,fingerprint
from rebind_scenery import array,encoded_array
from v037_fbx import node,setvalues
from scene_texture_bindings_v044 import actual_diffuse_bindings

def encode_linear(nodes,tail):
    """Same FBX 7400 records without repeatedly copying a whole forest buffer."""
    sizes={}
    def size(n):
        total=13+len(n['name'])+len(n['props'])+len(n['sentinel'])+sum(size(c) for c in n['children'])
        sizes[id(n)]=total;return total
    length=27+sum(size(n) for n in nodes)+13
    footer=tail[:20]+bytes(16-((length+20)%16))+tail[-140:]
    out=bytearray(length+len(footer));out[:27]=b'Kaydara FBX Binary  \x00\x1a\x00'+struct.pack('<I',7400)
    def write(n,start):
        end=start+sizes[id(n)];struct.pack_into('<IIIB',out,start,end,n['count'],len(n['props']),len(n['name']))
        pos=start+13;out[pos:pos+len(n['name'])]=n['name'];pos+=len(n['name'])
        out[pos:pos+len(n['props'])]=n['props'];pos+=len(n['props'])
        for c in n['children']:pos=write(c,pos)
        out[pos:end]=n['sentinel'];return end
    pos=27
    for n in nodes:pos=write(n,pos)
    assert pos==length-13;out[length:]=footer;return out

def tree_key(name):
    if re.fullmatch(r'tree_\d+',name):return name
    if re.fullmatch(r'v044_scan_tree_\d+_[012]',name):return name.rsplit('_',1)[0]
    if re.fullmatch(r'oak_.+_(?:bark|leaf[123])',name):return name.rsplit('_',1)[0]
    if re.fullmatch(r'v028_(?:staging|practice)_oak_.+_(?:bark|leaf[123])',name):return name.rsplit('_',1)[0]
    return None

def polygon_counts(g):
    ix=array(child(g,b'PolygonVertexIndex'));ends=np.flatnonzero(ix<0)
    sizes=np.diff(np.r_[-1,ends]);assert sizes.sum()==len(ix)
    return len(ends),int(np.sum(sizes-2))

def normal_alignment(g):
    # FBX's negative-Z conversion reverses handedness. Inspect face/normal
    # alignment in raw FBX space, then preserve its exact polygon winding.
    v=array(child(g,b'Vertices')).reshape(-1,3)
    ids=array(child(g,b'PolygonVertexIndex')).astype(np.int64);ends=np.flatnonzero(ids<0)
    ids[ids<0]=-ids[ids<0]-1;starts=np.r_[0,ends[:-1]+1]
    layer=child(g,b'LayerElementNormal')
    normal=array(child(layer,b'Normals')).reshape(-1,3)
    if values(child(layer,b'ReferenceInformationType'))[0]==b'IndexToDirect':
        normal=normal[array(child(layer,b'NormalsIndex'))]
    geom=np.cross(v[ids[starts+1]]-v[ids[starts]],v[ids[starts+2]]-v[ids[starts]])
    length=np.linalg.norm(geom,axis=1);assert np.all(length>1e-10)
    dot=np.sum(geom/length[:,None]*normal[starts],axis=1)
    assert np.min(dot)>.09,('Incorrect leaf face/custom-normal orientation',float(np.min(dot)))
    return float(np.min(dot))

def main():
    spec=read(R/'V047_SOURCE/trees.json')
    assert spec['approved_mix']=={'A':.85,'B':.15}
    assert sha(BASE/'scenery.fbx')==SCENERY_SHA and sha(BASE/'terrain.raw')==TERRAIN_SHA
    O.mkdir(parents=True,exist_ok=True);F.mkdir(parents=True,exist_ok=True)
    nodes,tail=parse((BASE/'scenery.fbx').read_bytes())
    objs=next(n for n in nodes if n['name']==b'Objects')
    links=next(n for n in nodes if n['name']==b'Connections')
    defs=next(n for n in nodes if n['name']==b'Definitions')
    rec=geometry_records(nodes);byid={values(n)[0]:n for n in objs['children']}
    baseline={i:fingerprint(n) for i,n in byid.items()}
    unaffected={n['name']:fingerprint(n) for n in nodes if n['name'] not in (b'Objects',b'Connections',b'Definitions')}
    groups={}
    for name,(g,mid) in rec.items():
        key=tree_key(name)
        if key:groups.setdefault(key,[]).append((name,g,mid))
    assert len(groups)==369,('Unexpected baseline tree inventory',len(groups))
    route=dict(np.load(BASE/'route.npz'));q=route['q'];width=route['width'];rt=cKDTree(q[:,:2])
    height=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    def ground(pos):return map_coordinates(height,[(600-pos[:,1])/600*2048,pos[:,0]/600*2048],order=1,mode='nearest')
    rows=[]
    for key,parts in sorted(groups.items()):
        trunk=next((g for name,g,_ in parts if name.endswith(('_bark','_2'))),parts[0][1])
        v=vertices(trunk);low=v[v[:,1]<v[:,1].min()+.15];anchor=low[:,[0,2]].mean(0)
        allv=np.concatenate([vertices(g) for _,g,_ in parts]);dist,ix=rt.query(anchor)
        facility='oak_' in key
        band='near' if dist<=spec['near_view_distance_m'] or facility else 'middle' if dist<=spec['middle_view_distance_m'] else 'far'
        rows.append(dict(original=key,parts=[n for n,_,_ in parts],anchor_xz_m=anchor.tolist(),distance_to_route_m=float(dist),route_station_m=float(q[ix,3]),band=band,facility_tree=facility,height_m=float(np.ptp(allv[:,1])),old_radius_m=float(np.max(np.linalg.norm(allv[:,[0,2]]-anchor,axis=1))),retained=band=='near'))
    rng=np.random.default_rng(spec['placement_seed'])
    kept=[r for r in rows if r['retained']]
    # Stable, spatially distributed thinning avoids retaining a dense far patch
    # while emptying its neighbor. This changes static density, not draw-distance LOD.
    for band,fraction in [('middle',spec['middle_view_retention_fraction']),('far',spec['far_view_retention_fraction'])]:
        candidates=[r for r in rows if r['band']==band];order=rng.permutation(len(candidates));target=round(len(candidates)*fraction)
        accepted=[]
        for ix in order:
            r=candidates[ix];a=np.array(r['anchor_xz_m'])
            if any(np.linalg.norm(a-np.array(k['anchor_xz_m']))<spec['minimum_retained_distant_spacing_m'] for k in kept+accepted):continue
            r['retained']=True;accepted.append(r)
            if len(accepted)>=target:break
        kept+=accepted
    kept.sort(key=lambda r:r['original'])
    nb=round(len(kept)*spec['approved_mix']['B'])
    # Spread B around the circuit, with exactly the approved rounded count.
    by_station=sorted(kept,key=lambda r:(r['route_station_m'],r['distance_to_route_m']))
    bkeys={by_station[int(ix)]['original'] for ix in np.floor((np.arange(nb)+.5)*len(kept)/nb)} if nb else set()
    prototypes={};prototype_stats={}
    for which in ['A','B']:
        path=TREES/'review'/('Tree_'+which+'_LOD0.fbx');assert sha(path)==TREE_SHA[which]
        n,_=parse(path.read_bytes());parts=[]
        for name,(g,mid) in geometry_records(n).items():
            is_leaf=name.endswith('_Foliage');polys,tris=polygon_counts(g)
            if is_leaf:alignment=normal_alignment(g)
            else:alignment=None
            parts.append(dict(g=g,v=vertices(g),normal=array(child(child(g,b'LayerElementNormal'),b'Normals')).reshape(-1,3)*[1,1,-1],material='CK_pine_foliage' if is_leaf and which=='A' else 'CK_woodland_foliage' if is_leaf else 'pine_bark',kind='foliage' if is_leaf else 'wood',triangles=tris,alignment=alignment))
        assert len(parts)==2
        prototypes[which]=parts
        prototype_stats[which]=dict(fbx_sha256=TREE_SHA[which],triangles=sum(p['triangles'] for p in parts),vertices=sum(len(p['v']) for p in parts))
    uid=max(byid)+1000
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'white')
    matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in links['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    mats={};textures=[]
    native_names={'pine_bark':'pine_bark','CK_pine_foliage':'CK_TREE_v047_pine','CK_woodland_foliage':'CK_TREE_v047_woodland'}
    for source_stem,stem in native_names.items():
        # PiBoSo's documented TREE texture marker gives foliage less harsh
        # shading; the native aliases retain the approved image bytes exactly.
        fname=stem+'.tga';raw=(TREES/'textures'/(source_stem+'.tga')).read_bytes();(F/fname).write_bytes(raw)
        for suffix in ['.shd','_n.tga']:
            p=TREES/'textures'/(source_stem+suffix)
            if p.is_file():(F/(stem+suffix)).write_bytes(p.read_bytes())
        with Image.open(F/fname) as im:
            if stem.startswith('CK_'):
                assert im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255)
                alpha=np.asarray(im.getchannel('A'));assert .01<np.mean(alpha>114)<.75
        ids=[newid(),newid(),newid()];mats[source_stem]=ids[0]
        for src,nid,kind in zip([base_mat,byid[texid],byid[vidid]],ids,['Material','Texture','Video']):
            n=copy.deepcopy(src);old=values(n);setvalues(n,nid,stem.encode()+b'\0\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                elif c['name']==b'Media':setvalues(c,stem.encode()+b'\0\x01Video')
                elif c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(raw))+raw
                elif c['name']==b'Properties70':
                    for pp in c['children']:
                        vv=values(pp)
                        if vv and vv[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(pp,*vv[:4],1.,1.,1.)
                        elif vv and vv[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(pp,*vv[:4],fname)
            objs['children'].append(n)
        connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1])
        textures.append(dict(file=fname,sha256=sha(F/fname),approved_source_file=source_stem+'.tga',approved_pixels_unchanged=True))
    removed={i for parts in groups.values() for _,g,mid in parts for i in [values(g)[0],mid]}
    old_tree_triangles=sum(polygon_counts(g)[1] for parts in groups.values() for _,g,_ in parts)
    retained_links=[fingerprint(n) for n in links['children'][:-(3*2)] if not any(v in removed for v in values(n)[1:3])]
    # Keep shared and legacy material/media records exact. The native exporter
    # resolves active model bindings, so old unbound tree images are not required.
    objs['children']=[n for n in objs['children'] if values(n)[0] not in removed]
    links['children']=[n for n in links['children'] if not any(v in removed for v in values(n)[1:3])]
    probes=[];newnames=[];newtri=0;adjusted=0
    for ti,row in enumerate(kept):
        which='B' if row['original'] in bkeys else 'A';parts=prototypes[which]
        allv=np.concatenate([p['v'] for p in parts]);ph=float(np.ptp(allv[:,1]));pr=float(np.max(np.linalg.norm(allv[:,[0,2]],axis=1)))
        sy=float(np.clip(row['height_m']/ph*rng.uniform(.94,1.04),*spec['vertical_scale_range']))
        sx=float(rng.uniform(*spec['horizontal_scale_range']));sz=sx*float(rng.uniform(.92,1.08))
        scale=np.array([sx,sy,sz]);scale[[0,2]]*=min(1,row['old_radius_m']/(pr*max(sx,sz)))
        yaw=float(rng.uniform(0,2*np.pi));c,s=np.cos(yaw),np.sin(yaw);rot=np.array([[c,0,s],[0,1,0],[-s,0,c]])
        anchor=np.array(row['anchor_xz_m']);base=np.array([anchor[0],float(ground(anchor[None,:])[0])-spec['root_embed_m'],anchor[1]])
        def transformed():return [(p['v']*scale)@rot.T+base for p in parts]
        for attempt in range(12):
            vv=transformed();allnew=np.concatenate(vv);d,ix=rt.query(allnew[:,[0,2]]);low=allnew[:,1]-ground(allnew[:,[0,2]])<spec['rider_headroom_m']
            unsafe=low&(d<width[ix]/2+spec['minimum_low_branch_track_margin_m'])
            if not np.any(unsafe):break
            scale[[0,2]]*=.90;adjusted+=attempt==0
        assert not np.any(unsafe),('New tree infringes rider corridor',row['original'])
        row.update(style=which,yaw_radians=yaw,scale_xyz=scale.tolist(),base_xyz_m=base.tolist(),low_branches_clear=True)
        for part,v in zip(parts,vv):
            name=f'v047_tree_{which}_{ti:03d}_{part["kind"]}';gid,mid=newid(),newid();g=copy.deepcopy(part['g']);old=values(g);setvalues(g,gid,name.encode()+b'\0\x01Geometry',*old[2:])
            child(g,b'Vertices')['props']=encoded_array(v*[100,100,-100])
            normal=(part['normal']/scale)@rot.T;normal/=np.linalg.norm(normal,axis=1)[:,None]
            child(child(g,b'LayerElementNormal'),b'Normals')['props']=encoded_array(normal*[1,1,-1])
            if part['kind']=='foliage':normal_alignment(g)
            model=copy.deepcopy(template);old=values(model);setvalues(model,mid,name.encode()+b'\0\x01Model',*old[2:])
            objs['children'] += [g,model];connect(gid,mid);connect(mats[part['material']],mid);connect(mid,0)
            newnames.append(name);newtri+=part['triangles']
            for ix in [0,len(v)//2,len(v)-1]:probes.append(dict(object=name,style=which,expected_xyz_m=v[ix].tolist()))
    counts=Counter(n['name'] for n in objs['children']);total=0
    for d in defs['children']:
        if d['name']==b'ObjectType':
            typ=values(d)[0];ct=child(d,b'Count');ct['props']=b'I'+struct.pack('<i',counts[typ]);total+=counts[typ]
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',total)
    print('Tree meshes transformed and clearance checked; encoding source forest.',flush=True)
    (O/'scenery.fbx').write_bytes(encode_linear(nodes,tail));outnodes,_=parse((O/'scenery.fbx').read_bytes());outobjects=next(n for n in outnodes if n['name']==b'Objects')
    after={values(n)[0]:fingerprint(n) for n in outobjects['children']}
    assert all(after.get(i)==fp for i,fp in baseline.items() if i not in removed)
    assert all(fingerprint(n)==unaffected[n['name']] for n in outnodes if n['name'] in unaffected)
    outrec=geometry_records(outnodes);assert not any(tree_key(name) for name in outrec)
    preserved=[]
    for name,(g,mid) in rec.items():
        if tree_key(name):continue
        assert fingerprint(outrec[name][0])==fingerprint(g)
        v=vertices(g);valid=np.flatnonzero(np.isfinite(v).all(1)&(v[:,0]>.001)&(v[:,2]>.001))
        if len(valid):preserved.append(dict(object=name,expected_xyz_m=v[valid[len(valid)//2]].tolist()))
    native_links=[fingerprint(n) for n in next(n for n in outnodes if n['name']==b'Connections')['children']]
    assert native_links[:len(retained_links)]==retained_links
    bindings=actual_diffuse_bindings(outnodes)
    assert {'pine_bark.tga','CK_TREE_v047_pine.tga','CK_TREE_v047_woodland.tga'}<=set(bindings['actual_diffuse_textures'])
    dormant=[n for n in bindings['actual_diffuse_textures'] if n.startswith(('CK_v044_scan','v044_scan')) or n in ['v024_leaf1.tga','v024_leaf2.tga','v024_leaf3.tga','v028_leaf1.tga','v028_leaf2.tga','v028_leaf3.tga']]
    assert not dormant,('Old tree textures still bound to geometry',dormant)
    save(O/'v047_native_probes.json',dict(retained_geometry=preserved,new_trees=probes))
    styles=Counter(r['style'] for r in kept);assert styles=={'A':len(kept)-nb,'B':nb}
    qa=dict(checks_pass=True,version='v047',baseline_version='v046',source_scenery_sha256=SCENERY_SHA,scenery_sha256=sha(O/'scenery.fbx'),approved_prototype_sha256=TREE_SHA,
        tree_count_before=len(groups),tree_count_after=len(kept),tree_count_removed_for_distance=len(groups)-len(kept),style_counts=dict(styles),style_percent={k:100*v/len(kept) for k,v in styles.items()},
        source_tree_meshes_removed=sum(len(p) for p in groups.values()),near_tree_count=sum(r['band']=='near' for r in rows),all_near_trees_preserved=True,all_facility_tree_placements_preserved=True,
        distant_density_by_band={b:dict(before=sum(r['band']==b for r in rows),after=sum(r['band']==b and r['retained'] for r in rows)) for b in ['near','middle','far']},
        static_distant_thinning=True,native_lod_switching=False,old_tree_triangles=old_tree_triangles,new_tree_triangles=newtri,prototype_stats=prototype_stats,
        all_retained_geometry_exact=True,non_tree_geometry_count=len(preserved),retained_object_records_exact=len(baseline)-len(removed),retained_connections_exact=len(retained_links),global_axes_metadata_exact=True,
        all_low_branches_clear_of_riding_corridor=True,tree_horizontal_clearance_adjustments=adjusted,custom_normals_preserved_and_transformed=True,foliage_face_normal_alignment_pass=True,
        source_native_alpha_test_prefix=True,native_tree_soft_shading_marker=True,leaf_alpha_has_real_gaps=True,new_tree_textures=textures,active_diffuse_textures=bindings['actual_diffuse_textures'],
        new_geometry_is_visual_only=True,terrain_modified=False,dirt_modified=False,physical_track_modified=False,lighting_modified=False,in_game_visual_check=False,performance_test=False,placements=rows)
    save(O/'v047_scenery_validation.json',qa)
    print('V047_TREE_SUMMARY',len(groups),'old;',len(kept),'new;',dict(styles),'distant bands',qa['distant_density_by_band'],'tree triangles',old_tree_triangles,'->',newtri,flush=True)
    return qa

if __name__=='__main__':main()
