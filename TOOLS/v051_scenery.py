"""Replace legacy scrub and botanical cards with small photographic grass.

Real Bermuda blade shapes and alpha textures; front/back faces and correct
normals. SKIDS prefix excludes these visual-only meshes from native shadow
casting. All non-grass records, including every approved tree, stay exact.
"""
import copy, json, struct
from collections import Counter
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,distance_transform_edt
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from v051_surface import R, BASE, O, sha, save
from v027_scenery import parse, values, child, vertices, geometry_records, fingerprint
from v047_scenery import encode_linear, normal_alignment
from v037_fbx import node, setvalues, mapped_geometry
from v044_scenery import gltf
from scene_texture_bindings_v044 import actual_diffuse_bindings

F=O/'facility_textures'; SOURCE=R/'V047_OUTPUT/scenery.fbx'
TEXTURE='CK_CONSTS_v051_bermuda.tga'
TINT=[.78,1.38,.78]
def is_grass(name):return name.startswith(('scrub_','v044_bermuda_patch_'))

def main():
    F.mkdir(parents=True,exist_ok=True); baseline_qa=json.loads((R/'V047_OUTPUT/v047_scenery_validation.json').read_text())
    assert sha(SOURCE)==baseline_qa['scenery_sha256']=='e075d70f4ac156764b05de185092fbb8d0aaabafd94ea9cf368c8a3af5d548df'
    nodes,tail=parse(SOURCE.read_bytes()); objs=next(n for n in nodes if n['name']==b'Objects')
    links=next(n for n in nodes if n['name']==b'Connections'); defs=next(n for n in nodes if n['name']==b'Definitions')
    rec=geometry_records(nodes); byid={values(n)[0]:n for n in objs['children']}
    before={i:fingerprint(n) for i,n in byid.items()}; original_links=[fingerprint(n) for n in links['children']]
    grass={name:r for name,r in rec.items() if is_grass(name)}
    assert sum(n.startswith('scrub_') for n in grass)==53 and sum(n.startswith('v044_bermuda') for n in grass)==10
    route=dict(np.load(BASE/'route.npz')); q=route['q']; widths=route['width']; route_tree=cKDTree(q[:,:2])
    height=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float64)/65535*18
    def ground(p):return map_coordinates(height,[(600-p[:,1])/600*2048,p[:,0]/600*2048],order=1,mode='nearest')
    # Reconstruct organic cluster roots from the exact delivered grass. Their
    # old flat panels are discarded, including their baked rectangular shadows.
    roots=[]; scrub=[]
    for name,(g,mid) in grass.items():
        v=vertices(g)
        if name.startswith('scrub_'):
            scrub.append(dict(original=name,anchor=v[:,[0,2]].mean(0),low=v[:,[0,2]].min(0),high=v[:,[0,2]].max(0)))
        else:
            low=v[:,1]-ground(v[:,[0,2]])<.028; roots.append(v[low][:,[0,2]])
    roots=np.unique(np.round(np.concatenate(roots),3),axis=0)
    pairs=cKDTree(roots).query_pairs(.34,output_type='ndarray'); edges=np.r_[pairs,pairs[:,::-1]]
    graph=coo_matrix((np.ones(len(edges),np.uint8),(edges[:,0],edges[:,1])),shape=(len(roots),len(roots))).tocsr()
    count,labels=connected_components(graph,directed=False)
    counts=np.bincount(labels); centers=np.stack([np.bincount(labels,weights=roots[:,k])/counts for k in [0,1]],1)
    centers=centers[counts>=3]; assert 400<len(centers)<2000,('unexpected grass root inventory',len(centers))
    path=R/'BUILD/v044_assets/grass_bermuda_01/grass_bermuda_01.gltf'; doc,a=gltf(path); parts=[]
    for mi in [3,4,5,6,7,8,15,16,17,18,19,20]:
        p=doc['meshes'][mi]['primitives'][0]; v=a(p['attributes']['POSITION']).astype(np.float64)
        v[:,1]-=v[:,1].min(); base=v[v[:,1]<.003][:,[0,2]].mean(0); v[:,[0,2]]-=base
        f=a(p['indices']).reshape(-1,3).astype(np.int32); uv=a(p['attributes']['TEXCOORD_0']).copy(); uv[:,1]=1-uv[:,1]
        # Use explicit front/back triangles, never a one-sided giant billboard.
        f=np.concatenate([f,f[:,::-1]]); parts.append(dict(v=v,f=f,uv=uv,height=float(v[:,1].max())))
    # Renderer import preprocessing: extrude photographed edge RGB through
    # transparent texels without changing any opaque photo or alpha pixel.
    # Straight-alpha mip filtering must not blend leaf colour with black.
    source_texture=BASE/'facility_textures/CK_v044_bermuda.tga'
    rgba=np.array(Image.open(source_texture).convert('RGBA'));source_rgba=rgba.copy()
    edge=rgba[:,:,3]>=128
    # Use opaque leaf interiors as padding seeds. The photographed cutout's
    # outermost edge pixels include nearly black antialiasing; propagating
    # those through the atlas would preserve the same distant dark fringe.
    seeds=(rgba[:,:,3]>=224)&(rgba[:,:,1]>=60)
    assert np.count_nonzero(seeds)>10000
    nearest=distance_transform_edt(~seeds,return_distances=False,return_indices=True)
    rgba[:,:,:3][~edge]=rgba[:,:,:3][nearest[0][~edge],nearest[1][~edge]]
    assert np.array_equal(rgba[:,:,3],source_rgba[:,:,3]) and np.array_equal(rgba[:,:,:3][edge],source_rgba[:,:,:3][edge])
    Image.fromarray(rgba).save(F/TEXTURE,format='TGA');raw=(F/TEXTURE).read_bytes()
    im=Image.open(F/TEXTURE); alpha=np.asarray(im.getchannel('A'))
    assert im.mode=='RGBA' and im.size==(1024,1024) and alpha.min()==0 and alpha.max()==255
    assert .01<np.mean(alpha>=128)<.45
    uid=max(byid)+1000
    def newid():
        nonlocal uid; uid+=1; return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'white'); matid=values(mat)[0]
    tex=byid[next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')]
    video=byid[next(values(n)[1] for n in links['children'] if values(n)[2]==values(tex)[0] and byid.get(values(n)[1],{}).get('name')==b'Video')]
    mids=[newid(),newid(),newid()]; stem=TEXTURE[:-4]
    for source,nid,kind in zip([mat,tex,video],mids,['Material','Texture','Video']):
        n=copy.deepcopy(source); vv=values(n); setvalues(n,nid,stem.encode()+b'\0\x01'+kind.encode(),*vv[2:])
        for c in n['children']:
            if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,TEXTURE)
            elif c['name']==b'Media':setvalues(c,stem.encode()+b'\0\x01Video')
            elif c['name']==b'Content':c['count']=1; c['props']=b'R'+struct.pack('<I',len(raw))+raw
            elif c['name']==b'Properties70':
                for pp in c['children']:
                    v=values(pp)
                    if v and v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(pp,*v[:4],*TINT)
                    elif v and v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(pp,*v[:4],TEXTURE)
        objs['children'].append(n)
    connect(mids[1],mids[0],'DiffuseColor'); connect(mids[2],mids[1])
    removed={i for g,mid in grass.values() for i in [values(g)[0],mid]}
    kept_links=[fingerprint(n) for n in links['children'][:-2] if not any(v in removed for v in values(n)[1:3])]
    objs['children']=[n for n in objs['children'] if values(n)[0] not in removed]
    links['children']=[n for n in links['children'] if not any(v in removed for v in values(n)[1:3])]
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    rng=np.random.default_rng(510051); blades=[]; replaced=[]
    from v051_coverage import Verge
    verge=Verge()
    def make(p,target_height):
        dist,ix=route_tree.query(p)
        if dist<widths[ix]/2+.65:return False
        part=parts[int(rng.integers(len(parts)))]; scale=target_height/part['height']
        angle=rng.uniform(0,2*np.pi); c,s=np.cos(angle),np.sin(angle); rot=np.array([[c,0,s],[0,1,0],[-s,0,c]])
        shaped=part['v'].copy();shaped[:,[0,2]]*=1.38
        v=(shaped*scale)@rot.T; v+=np.array([p[0],float(ground(p[None,:])[0])-.010,p[1]])
        blades.append((p,v,part['f'],part['uv'])); return True
    for center in centers:
        dist,_=route_tree.query(center); amount=14 if dist<22 else 10
        for _ in range(amount):make(center+rng.normal(0,.18,2),rng.uniform(.18,.33))
    for item in scrub:
        count=0
        for _ in range(54):
            p=item['anchor']+rng.normal(0,.43,2); p=np.clip(p,item['low']+.1,item['high']-.1)
            count+=make(p,rng.uniform(.21,.40))
        replaced.append(dict(original=item['original'],new_clumps=count,anchor_xz_m=item['anchor'].tolist()))
    # Populate the open green verges too, rather than only the historic sparse
    # roots. Deterministic shuffled anchors avoid visible rows of plant tufts.
    xx,zz=np.meshgrid(np.arange(q[:,0].min()-28,q[:,0].max()+28,2.25),np.arange(q[:,1].min()-28,q[:,1].max()+28,2.25))
    anchors=np.stack([xx.ravel(),zz.ravel()],1)+rng.uniform(-.65,.65,(xx.size,2))
    anchors=anchors[verge.sample(anchors)>.64];rng.shuffle(anchors);new_field_clumps=0
    for p in anchors:
        if len(blades)>=18000:break
        for _ in range(2):
            if len(blades)>=18000:break
            point=p+rng.normal(0,.15,2)
            if verge.sample(point[None,:])[0]>.60:new_field_clumps+=make(point,rng.uniform(.17,.30))
    print('Grass roots/clumps',len(centers),len(blades),'new verge clumps',new_field_clumps,flush=True)
    assert 12000<len(blades)<=18000
    # Spatial 12 m cells keep mesh bounds local, improving culling granularity.
    groups={}
    for b in blades:groups.setdefault(tuple(np.floor(b[0]/12).astype(int)),[]).append(b)
    new_names=[]; probes=[]; newtri=0
    for cell,items in sorted(groups.items()):
        name=f'SKIDS_v051_grass_{cell[0]}_{cell[1]}'; vv=[]; ff=[]; uu=[]; cursor=0
        for p,v,f,uv in items:vv.append(v); ff.append(f+cursor); uu.append(uv); cursor+=len(v)
        v=np.concatenate(vv); f=np.concatenate(ff); uv=np.concatenate(uu)
        gid,mid=newid(),newid(); g=mapped_geometry(gid,dict(name=name,vertices=v,faces=f,uv=uv[f],material=stem))
        assert normal_alignment(g)>.99
        mdl=copy.deepcopy(template); old=values(mdl); setvalues(mdl,mid,name.encode()+b'\0\x01Model',*old[2:])
        objs['children'] += [g,mdl]; connect(gid,mid); connect(mids[0],mid); connect(mid,0)
        new_names.append(name); newtri+=len(f)
        probes.extend([dict(geometry=name,expected_xyz_m=v[i].tolist()) for i in sorted(set([0,len(v)//2,len(v)-1]))])
    counts=Counter(n['name'] for n in objs['children']); total=0
    for d in defs['children']:
        if d['name']==b'ObjectType':
            typ=values(d)[0]; child(d,b'Count')['props']=b'I'+struct.pack('<i',counts[typ]); total+=counts[typ]
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',total)
    output=O/'scenery.fbx'; output.write_bytes(encode_linear(nodes,tail)); got,_=parse(output.read_bytes())
    after={values(n)[0]:fingerprint(n) for n in next(n for n in got if n['name']==b'Objects')['children']}
    assert all(after[i]==f for i,f in before.items() if i not in removed)
    gotrec=geometry_records(got); retained=[]; trees=0
    for name,(g,mid) in rec.items():
        if is_grass(name):assert name not in gotrec; continue
        assert fingerprint(g)==fingerprint(gotrec[name][0]),name
        if name.startswith('v047_tree_'):trees+=1
        v=vertices(g); retained.extend(dict(geometry=name,expected_xyz_m=v[i].tolist()) for i in sorted(set([0,len(v)//2,len(v)-1])))
    gotlinks={fingerprint(n) for n in next(n for n in got if n['name']==b'Connections')['children']}
    assert all(k in gotlinks for k in kept_links)
    active=actual_diffuse_bindings(got)['actual_diffuse_textures']; assert TEXTURE in active and 'foliage_light.tga' not in active and 'CK_v044_bermuda.tga' not in active
    assert newtri<650000,('Grass triangle budget exceeded',newtri)
    mips=[]
    for n in [256,64,16,4,1]:
        # Check straight RGB filtering, not PIL's alpha-premultiplied resize.
        rgb=np.asarray(Image.fromarray(rgba[:,:,:3]).resize((n,n),Image.Resampling.BOX),np.float32)*np.array(TINT)
        mean=rgb.mean((0,1));assert mean[1]>mean[0]*1.35 and mean[1]>mean[2]*1.6 and mean[1]>75
        mips.append(dict(size=n,tinted_rgb_mean=mean.tolist(),green_dominant=True))
    save(O/'v051_scenery_validation.json',dict(version='v051',checks_pass=True,baseline_scenery_sha256=sha(SOURCE),scenery_sha256=sha(output),
        removed_legacy_scrub_clusters=53,removed_old_botanical_batches=10,all_non_grass_records_exact=True,all_approved_tree_records_exact=True,
        approved_tree_mix=baseline_qa['style_counts'],replaced_scrub=replaced,reconstructed_existing_grass_clusters=len(centers),
        grass_clumps=len(blades),grass_batches=len(groups),grass_triangles=newtri,grass_height_m=[.17,.40],grass_mesh_front_back_normals_verified=True,
        clump_count_vs_v050_ratio=len(blades)/4546,new_verge_clumps=new_field_clumps,blade_width_multiplier=1.38,
        photographic_material_tint_rgb=TINT,transparent_rgb_edge_extruded=True,photo_opaque_rgb_unchanged=True,photo_alpha_unchanged=True,
        distance_mip_colour_validation=mips,
        grass_names=new_names,all_grass_no_shadow_native_prefix=True,all_grass_visual_only=True,small_spatial_batch_m=12,
        photographic_texture_file=TEXTURE,photographic_texture_sha256=sha(F/TEXTURE),photographic_source_sha256=sha(source_texture),photographic_texture_pixels_identical_to_CC0_scan=False,
        alpha_covered_fraction=float(np.mean(alpha>=128)),active_diffuse_textures=active,retained_geometry_count=len(rec)-len(grass),
        ground_collision_modified=False,in_game_visual_check=False))
    save(O/'v051_native_probes.json',dict(retained_geometry=retained,new_grass=probes))
    print('Grass ready:',len(blades),'photographic clumps;',len(groups),'local batches;',newtri,'front/back triangles; all non-grass exact.',flush=True)
if __name__=='__main__':main()
