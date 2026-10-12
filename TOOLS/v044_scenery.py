"""Scan-derived near-view trees, botanical grass and photographic structural materials."""
import copy,struct
from collections import Counter
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from v044_common import *
from v044_assets import material,model,metadata,get,CACHE
from v027_scenery import parse,encode,values,child,vertices,geometry_records,fingerprint
from rebind_scenery import array,encoded_array
from v037_fbx import node,arr,integer,setvalues,mapped_geometry

def gltf(path):
    doc=read(path);buffers=[(path.parent/b['uri']).read_bytes() for b in doc['buffers']]
    def accessor(i):
        a=doc['accessors'][i];b=doc['bufferViews'][a['bufferView']];typ={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];cols={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        out=np.frombuffer(buffers[b['buffer']],dtype=typ,count=a['count']*cols,offset=b.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],cols)
        return out[:,0] if cols==1 else out
    return doc,accessor

def import_tree():
    import fast_simplification
    path=model('tree_small_02');doc,a=gltf(path);parts=[]
    for p in doc['meshes'][0]['primitives']:
        mi=p['material'];mat=doc['materials'][mi];tex=mat['pbrMetallicRoughness']['baseColorTexture'];coord=tex.get('texCoord',0)
        v=np.asarray(a(p['attributes']['POSITION']),np.float64);f=np.asarray(a(p['indices']),np.int32).reshape(-1,3);uv=a(p['attributes']['TEXCOORD_'+str(coord)]);norm=a(p['attributes']['NORMAL'])
        target=[4000,50000,3000][mi]
        vv,ff=fast_simplification.simplify(v,f,target_count=target,agg=5)
        nearest=cKDTree(v).query(vv,workers=2)[1];uu=uv[nearest].copy();nn=norm[nearest].copy()
        tr=tex.get('extensions',{}).get('KHR_texture_transform',{});uu=uu*np.array(tr.get('scale',[1,1]))+np.array(tr.get('offset',[0,0]))
        uu[:,1]=1-uu[:,1]
        fname=['v044_scan_branch','CK_v044_scan_leaves','v044_scan_trunk'][mi]
        image=Image.open(path.parent/doc['images'][doc['textures'][tex['index']]['source']]['uri']).convert('RGB')
        arm=mat['pbrMetallicRoughness']['metallicRoughnessTexture'];ao=np.asarray(Image.open(path.parent/doc['images'][doc['textures'][arm['index']]['source']]['uri']).getchannel('R').resize(image.size),np.float32)/255
        col=np.asarray(image,np.float32)*(.80+.20*ao[:,:,None]);image=Image.fromarray(np.uint8(np.rint(np.clip(col,0,255))))
        if mi==1:
            entry=metadata('tree_small_02')['leaves_alpha']['1k'];fmt='png' if 'png' in entry else next(iter(entry));ap=get(entry[fmt],CACHE/'tree_small_02/leaves_alpha.png')
            image=image.convert('RGBA');image.putalpha(Image.open(ap).convert('L').resize(image.size,Image.Resampling.LANCZOS))
        image_file(image,F/(fname+'.tga'))
        # Matte native normal maps; RGB tangent detail with explicit low specular alpha.
        no=mat['normalTexture'];normal=Image.open(path.parent/doc['images'][doc['textures'][no['index']]['source']]['uri']).convert('RGBA');normal.putalpha(Image.new('L',normal.size,2));image_file(normal,F/(fname+'_n.tga'))
        (F/(fname+'.shd')).write_text('bump\n{\n map = '+fname+'_n.tga\n}\nspecular\n{\n shininess = 8\n}\n')
        cross=np.cross(vv[ff[:,1]]-vv[ff[:,0]],vv[ff[:,2]]-vv[ff[:,0]]);ok=np.linalg.norm(cross,axis=1)>1e-10;ff=ff[ok]
        if mi==1 and len(ff)>75000:
            # Disconnected botanical leaf pieces have an irreducible triangle floor.
            # Keep complete components distributed across the crown, never isolated face fragments.
            from scipy.sparse import coo_matrix
            from scipy.sparse.csgraph import connected_components
            edges=np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]])
            graph=coo_matrix((np.ones(len(edges),np.uint8),(edges[:,0],edges[:,1])),shape=(len(vv),len(vv))).tocsr()
            count,labels=connected_components(graph,directed=False)
            face_labels=labels[ff[:,0]];counts=np.bincount(face_labels,minlength=count)
            ids=np.flatnonzero(counts);random=np.random.default_rng(440011);random.shuffle(ids)
            chosen=ids[np.cumsum(counts[ids])<=75000]
            ff=ff[np.isin(face_labels,chosen)]
            used=np.unique(ff);lookup=np.full(len(vv),-1,np.int32);lookup[used]=np.arange(len(used));ff=lookup[ff];vv=vv[used];uu=uu[used];nn=nn[used]
            print('Whole leaf-component budget:',len(ff),'triangles',flush=True)
        parts.append(dict(v=vv,f=ff,uv=uu,norm=nn,material=fname))
        print('Scan tree part',mi,'original',len(f),'native candidate',len(ff),flush=True)
    # Scan ground origin derives from its low trunk, not the canopy center.
    trunk=parts[2]['v'];low=trunk[trunk[:,1]<trunk[:,1].min()+.1];origin=np.array([low[:,0].mean(),trunk[:,1].min(),low[:,2].mean()])
    for p in parts:p['v']-=origin
    return parts

def main():
    raw=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(raw);objs=next(n for n in nodes if n['name']==b'Objects');links=next(n for n in nodes if n['name']==b'Connections');defs=next(n for n in nodes if n['name']==b'Definitions')
    byid={values(n)[0]:n for n in objs['children']};rec=geometry_records(nodes);uid=max(byid)+1000
    def newid():
        nonlocal uid;uid+=1;return uid
    def connect(a,b,p=None):links['children'].append(node('C','OP' if p else 'OO',a,b,*([p] if p else [])))
    baseline={i:fingerprint(n) for i,n in byid.items()};baseline_links=[fingerprint(n) for n in links['children']]
    source_counts=Counter(n['name'] for n in objs['children']);changed=[];newnames=[];probes=[]
    # Photographic grain for timber, bark and concrete at existing UV mappings and color means.
    updates={}
    for fn,asset in [('v024_timber.tga','rough_wood'),('v028_timber.tga','rough_wood'),('v024_bark.tga','pine_bark'),('v028_bark.tga','pine_bark'),('v032_concrete.tga','concrete_floor_worn_001'),('v033_qwikchute_concrete.tga','concrete_floor_worn_001')]:
        if not (F/fn).exists():continue
        old=np.asarray(Image.open(F/fn).convert('RGB'),np.float32);ph=np.asarray(material(asset,'Diffuse','2k').convert('RGB').resize((1024,1024)),np.float32);target=old.mean((0,1));ph=ph-ph.mean((0,1))+target
        image_file(Image.fromarray(np.uint8(np.rint(np.clip(ph,0,255)))),F/fn);updates[fn]=sha(F/fn)
        normal=material(asset,'nor_gl','2k').convert('RGBA').resize((1024,1024));normal.putalpha(Image.new('L',normal.size,2));stem=fn[:-4];image_file(normal,F/(stem+'_n.tga'));(F/(stem+'.shd')).write_text('bump\n{\n map = '+stem+'_n.tga\n}\nspecular\n{\n shininess = 8\n}\n')
    # Native FBX embedded Video payloads must agree with the authored external textures.
    for n in objs['children']:
        if n['name']!=b'Video':continue
        fns=[values(c)[0].decode() for c in n['children'] if c['name'] in [b'Filename',b'FileName',b'RelativeFilename']]
        names=[s.replace('\\','/').split('/')[-1] for s in fns];fn=next((s for s in names if s in updates),None)
        if fn:
            for c in n['children']:
                if c['name']==b'Content':b=(F/fn).read_bytes();c['count']=1;c['props']=b'R'+struct.pack('<I',len(b))+b
            changed.append(values(n)[0])
    template=next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    base_mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'white');matid=values(base_mat)[0]
    texid=next(values(n)[1] for n in links['children'] if values(n)[2]==matid and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vidid=next(values(n)[1] for n in links['children'] if values(n)[2]==texid and byid.get(values(n)[1],{}).get('name')==b'Video')
    mats={}
    def newmaterial(stem):
        if stem in mats:return mats[stem]
        ids=[newid(),newid(),newid()];mats[stem]=ids[0];fname=stem+'.tga';b=(F/fname).read_bytes()
        for src,nid,kind in zip([base_mat,byid[texid],byid[vidid]],ids,['Material','Texture','Video']):
            n=copy.deepcopy(src);old=values(n);setvalues(n,nid,stem.encode()+b'\0\x01'+kind.encode(),*old[2:])
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,fname)
                elif c['name']==b'Media':setvalues(c,stem.encode()+b'\0\x01Video')
                elif c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(b))+b
                elif c['name']==b'Properties70':
                    for pp in c['children']:
                        vv=values(pp)
                        if vv and vv[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(pp,*vv[:4],1.,1.,1.)
                        elif vv and vv[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(pp,*vv[:4],fname)
            objs['children'].append(n)
        connect(ids[1],ids[0],'DiffuseColor');connect(ids[2],ids[1]);return ids[0]
    def add(name,v,f,uv,material_name,normals=None):
        gid,mid=newid(),newid();m=dict(name=name,vertices=v,faces=f,uv=uv[f],material=material_name);g=mapped_geometry(gid,m)
        if normals is not None:
            nn=child(child(g,b'LayerElementNormal'),b'Normals');nn['props']=encoded_array((normals[f[:,::-1]].reshape(-1,3)*[1,1,-1]).ravel())
        mdl=copy.deepcopy(template);old=values(mdl);setvalues(mdl,mid,name.encode()+b'\0\x01Model',*old[2:]);objs['children'] += [g,mdl];connect(gid,mid);connect(newmaterial(material_name),mid);connect(mid,0)
        newnames.append(name);probes.extend(v[np.linspace(0,len(v)-1,3,dtype=int)].tolist())
    route=dict(np.load(O/'route.npz'));q=route['q'];width=route['width'];rt=cKDTree(q[:,:2]);h=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18
    def ground(pos):return map_coordinates(h,[(SIZE-pos[:,1])/SIZE*2048,pos[:,0]/SIZE*2048],order=1,mode='nearest')
    rng=np.random.default_rng(440044);trees=[]
    for name,(g,mid) in rec.items():
        if not name.startswith('tree_'):continue
        v=vertices(g);low=v[v[:,1]<v[:,1].min()+.55];anchor=low[:,[0,2]].mean(0);d,i=rt.query(anchor)
        if d-width[i]/2>8 and d<36:trees.append((float(d),name,anchor,float(q[i,3]),v,g,mid))
    selected=[]
    for item in sorted(trees):
        if all(np.linalg.norm(item[2]-s[2])>20 for s in selected):selected.append(item)
        if len(selected)>=28:break
    assert len(selected)>=12
    parts=import_tree();allv=np.concatenate([p['v'] for p in parts]);ext=np.max(np.abs(allv[:,[0,2]]),0);scanheight=allv[:,1].max();removed=[];checks=[]
    for ti,item in enumerate(selected):
        _,name,anchor,station,old,g,mid=item
        # Whole new crown fits inside the old footprint; no enlargement into riding corridors.
        radius=np.minimum(anchor-old[:,[0,2]].min(0),old[:,[0,2]].max(0)-anchor)
        horizontal=float(radius.min()/np.linalg.norm(ext))*.95
        scale=np.array([horizontal,(old[:,1].max()-old[:,1].min())/scanheight,horizontal])
        angle=rng.uniform(0,2*np.pi);c,s=np.cos(angle),np.sin(angle);rot=np.array([[c,0,s],[0,1,0],[-s,0,c]])
        base=np.array([anchor[0],float(ground(anchor[None,:])[0])-.035,anchor[1]])
        for pi,part in enumerate(parts):
            vv=(part['v']*scale)@rot.T+base;nn=(part['norm']/scale)@rot.T;nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-8)
            d,i=rt.query(vv[:,[0,2]]);lowmask=vv[:,1]-ground(vv[:,[0,2]])<4.5
            assert not np.any(lowmask&(d<width[i]/2+1.5)),name
            add('v044_scan_tree_'+str(ti)+'_'+str(pi),vv,part['f'],part['uv'],part['material'],nn)
        removed.extend([values(g)[0],mid]);checks.append(dict(original_tree=name,anchor_xz_m=anchor.tolist(),scan_scale=scale.tolist(),low_crown_clear_of_riding_corridor=True))
    objs['children']=[n for n in objs['children'] if values(n)[0] not in removed]
    links['children']=[n for n in links['children'] if not any(v in removed for v in values(n)[1:3])]
    # Grass includes several real Bermuda growth shapes. Native alpha-test prevents sorted-card artifacts.
    gp=model('grass_bermuda_01');doc,a=gltf(gp);grassparts=[]
    for mi in [3,4,5,6,7,8,15,16,17,18,19,20]:
        p=doc['meshes'][mi]['primitives'][0];v=a(p['attributes']['POSITION']).astype(float);v[:,1]-=v[:,1].min();v[:,[0,2]]-=v[:,[0,2]].mean(0);ff=a(p['indices']).reshape(-1,3);uv=a(p['attributes']['TEXCOORD_0']).copy();uv[:,1]=1-uv[:,1];grassparts.append((v,ff,uv))
    image=Image.open(gp.parent/'textures/grass_bermuda_01_diff_1k.jpg').convert('RGBA');entry=metadata('grass_bermuda_01')['Alpha']['1k'];fmt='png' if 'png' in entry else next(iter(entry));ap=get(entry[fmt],CACHE/'grass_bermuda_01/alpha.png');image.putalpha(Image.open(ap).convert('L').resize(image.size));image_file(image,F/'CK_v044_bermuda.tga')
    grass=np.asarray(Image.open(M/'mask_visual_grass.tga').getchannel('A'),float)/255;road=vertices(rec['TRKASPH_v037_oval_surface'][0]);roadtree=cKDTree(road[:,[0,2]])
    exclusions=[]
    for name,(g,mid) in rec.items():
        if name.startswith(('tree_','oak_')):continue
        v=vertices(g)
        if np.ptp(v[:,0])<100 and np.ptp(v[:,2])<100:exclusions.append((v[:,[0,2]].min(0)-.55,v[:,[0,2]].max(0)+.55))
    pos=rng.uniform([100,85],[445,515],(22000,2));d,i=rt.query(pos);gg=map_coordinates(grass,[(SIZE-pos[:,1])/SIZE*(len(grass)-1),pos[:,0]/SIZE*(len(grass)-1)],order=1,mode='constant')
    ok=(gg>.88)&(d>width[i]/2+1.7)&(d<45)&(roadtree.query(pos)[0]>2.5)
    for lo,hi in exclusions:ok &= ~np.all((pos>lo)&(pos<hi),1)
    pos=pos[ok][:5500];batches=[];clumps=0
    for bi in range(0,len(pos),100):
        vv=[];ff=[];uu=[];cursor=0
        for center in pos[bi:bi+100]:
            for _ in range(rng.integers(3,7)):
                v,f,uv=grassparts[rng.integers(len(grassparts))];angle=rng.uniform(0,2*np.pi);c,s=np.cos(angle),np.sin(angle);rot=np.array([[c,0,s],[0,1,0],[-s,0,c]])
                scale=rng.uniform(1.5,2.8);v=v@rot.T*scale;anchor=center+rng.normal(0,.13,2);v+=np.array([anchor[0],float(ground(anchor[None,:])[0])-.014,anchor[1]])
                vv.append(v);ff.append(f+cursor);uu.append(uv);cursor+=len(v);clumps+=1
        v=np.concatenate(vv);f=np.concatenate(ff);uv=np.concatenate(uu);add('v044_bermuda_patch_'+str(bi//100),v,f,uv,'CK_v044_bermuda')
    # Definition counts remain consistent with all object additions and selected tree removals.
    counts=Counter(n['name'] for n in objs['children']);total=0
    for d in defs['children']:
        if d['name']==b'ObjectType':
            typ=values(d)[0];ct=child(d,b'Count');ct['props']=b'I'+struct.pack('<i',counts[typ]);total+=counts[typ]
    child(defs,b'Count')['props']=b'I'+struct.pack('<i',total)
    out=encode(nodes,tail);atomic(O/'scenery.fbx',out);got=parse(out)[0];after={values(n)[0]:fingerprint(n) for n in next(n for n in got if n['name']==b'Objects')['children']}
    assert all(after[i]==fp for i,fp in baseline.items() if i not in removed+changed)
    # All physical and personal asset geometry records remain byte-identical.
    gotrec=geometry_records(got)
    for name,(g,mid) in rec.items():
        if values(g)[0] not in removed:assert fingerprint(g)==fingerprint(gotrec[name][0]),name
    save(O/'v044_scenery_validation.json',dict(checks_pass=True,all_retained_geometry_exact=True,removed_tree_record_ids=removed,modified_embedded_texture_record_ids=changed,photographic_texture_updates=updates,scan_tree_count=len(selected),trees=checks,grass_patch_count=(len(pos)+99)//100,grass_clusters=len(pos),grass_clumps=clumps,new_geometry=newnames,new_geometry_is_visual_only=True,vegetation_native_alpha_test=True,source_geometry_before=len(rec),source_geometry_after=len(gotrec),in_game_visual_check=False))
    save(O/'v044_native_probes.json',dict(expected_xyz_metres=probes))
    print('Scenery authored:',len(selected),'scan-derived trees;',clumps,'Bermuda clumps; all retained objects exact.',flush=True)
if __name__=='__main__':main()
