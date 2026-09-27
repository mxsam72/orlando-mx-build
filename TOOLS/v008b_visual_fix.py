#!/usr/bin/env python3
"""Orlando MX v008b visual-only correction.

- Neutralizes/darkens the v008 dirt textures toward the real GoPro reference.
- Dulls grass slightly.
- Breaks up the oversized/repetitive tree wall by scaling individual tree meshes
  around their ground-contact anchors. No track terrain, race data, physics masks,
  centerline, or jump geometry is touched.
"""
from pathlib import Path
import hashlib, json, random, shutil, struct, sys, zlib
from array import array

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'V008B_BACKUP'
REPORT = ROOT / 'V008B_EVIDENCE'
NULL = bytes(13)

DIRT = {
    'soil.tga':         dict(hue=-6.0, sat=0.47, val=0.82, contrast=1.05),
    'soil_wet.tga':     dict(hue=-5.0, sat=0.43, val=0.80, contrast=1.05),
    'prepared.tga':     dict(hue=-6.0, sat=0.45, val=0.84, contrast=1.04),
    'prepared_wet.tga': dict(hue=-5.0, sat=0.42, val=0.81, contrast=1.05),
    'worked.tga':       dict(hue=-5.0, sat=0.44, val=0.78, contrast=1.09),
    'worked_wet.tga':   dict(hue=-4.0, sat=0.40, val=0.76, contrast=1.09),
    'grass.tga':        dict(hue=-1.0, sat=0.82, val=0.93, contrast=1.02),
}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def ensure_pillow():
    try:
        from PIL import Image, ImageEnhance
        return Image, ImageEnhance
    except Exception:
        raise SystemExit('Pillow is required. Run: py -3 -m pip install pillow')

def adjust_texture(path, cfg):
    Image, ImageEnhance = ensure_pillow()
    im=Image.open(path).convert('RGB')
    hsv=im.convert('HSV'); h,s,v=hsv.split()
    shift=round(cfg['hue']/360*256)
    h=h.point(lambda x:(x+shift)%256)
    s=s.point(lambda x:max(0,min(255,round(x*cfg['sat']))))
    v=v.point(lambda x:max(0,min(255,round(x*cfg['val']))))
    out=Image.merge('HSV',(h,s,v)).convert('RGB')
    out=ImageEnhance.Contrast(out).enhance(cfg['contrast'])
    out.save(path)

def property_values(raw,count):
    off=0;result=[]
    for _ in range(count):
        typ=raw[off:off+1];off+=1
        if typ in (b'S',b'R'):
            n=struct.unpack_from('<I',raw,off)[0];off+=4
            result.append(raw[off:off+n]);off+=n
        elif typ in (b'd',b'f',b'i',b'l',b'b',b'c'):
            n,en,le=struct.unpack_from('<III',raw,off);off+=12
            data=raw[off:off+le];off+=le
            data=zlib.decompress(data) if en else data
            result.append((typ,n,data))
        else:
            fmt={b'Y':'h',b'C':'?',b'I':'i',b'F':'f',b'D':'d',b'L':'q'}[typ]
            result.append(struct.unpack_from('<'+fmt,raw,off)[0]);off+=struct.calcsize('<'+fmt)
    if off!=len(raw): raise RuntimeError('FBX property decode mismatch')
    return result

def parse(data):
    if data[:23]!=b'Kaydara FBX Binary  \x00\x1a\x00': raise RuntimeError('Unexpected FBX header')
    if struct.unpack_from('<I',data,23)[0]!=7400: raise RuntimeError('Expected FBX 7400')
    def node(off):
        end,n,length,nlen=struct.unpack_from('<IIIB',data,off);off+=13
        if not (end>off and end<=len(data)): raise RuntimeError('Invalid FBX node bounds')
        name=data[off:off+nlen];off+=nlen
        props=data[off:off+length];off+=length
        children=[]
        while off<end and data[off:off+13]!=NULL:
            child,off=node(off);children.append(child)
        sentinel=data[off:end]
        if sentinel not in (b'',NULL): raise RuntimeError('Invalid FBX sentinel')
        return dict(name=name,count=n,props=props,children=children,sentinel=sentinel),end
    nodes=[];off=27
    while data[off:off+13]!=NULL:
        n,off=node(off);nodes.append(n)
    return nodes,data[off+13:]

def encode(nodes,tail):
    def node(n,start):
        head=n['name']+n['props']; pos=start+13+len(head); parts=[head]
        for child in n['children']:
            b=node(child,pos); parts.append(b); pos+=len(b)
        parts.append(n['sentinel']); payload=b''.join(parts); end=start+13+len(payload)
        return struct.pack('<IIIB',end,n['count'],len(n['props']),len(n['name']))+payload
    prefix=b'Kaydara FBX Binary  \x00\x1a\x00'+struct.pack('<I',7400); parts=[prefix]; pos=len(prefix)
    for n in nodes:
        b=node(n,pos); parts.append(b); pos+=len(b)
    parts.append(NULL); result=b''.join(parts)
    if struct.unpack_from('<I',tail,len(tail)-140)[0]!=7400: raise RuntimeError('Unexpected FBX footer')
    result+=tail[:20]
    result+=bytes(16-(len(result)%16))
    result+=tail[-140:]
    return result

def array_from_node(n):
    typ,count,data=property_values(n['props'],n['count'])[0]
    if typ!=b'd': raise RuntimeError('Expected double FBX vertex array')
    a=array('d');a.frombytes(data)
    if sys.byteorder!='little': a.byteswap()
    if len(a)!=count: raise RuntimeError('FBX array length mismatch')
    return a

def encoded_double_array(a):
    b=array('d',a)
    if sys.byteorder!='little': b.byteswap()
    raw=b.tobytes();comp=zlib.compress(raw,6)
    return b'd'+struct.pack('<III',len(b),1,len(comp))+comp

def tree_fix(path):
    data=path.read_bytes();nodes,tail=parse(data)
    if encode(nodes,tail)!=data: raise RuntimeError('FBX is not byte-identical after no-op parse; aborting')
    objects=next(n for n in nodes if n['name']==b'Objects')
    connections=next(n for n in nodes if n['name']==b'Connections')

    id_to_node={}
    tree_models={}
    for n in objects['children']:
        try: v=property_values(n['props'],n['count'])
        except Exception: continue
        if v and isinstance(v[0],int): id_to_node[v[0]]=n
        if n['name']==b'Model' and len(v)>=3:
            name=v[1].split(b'\x00')[0].decode(errors='ignore')
            if name.startswith('tree_'):
                try: idx=int(name.split('_')[-1])
                except: continue
                tree_models[v[0]]=(name,idx)

    geom_for_model={}
    for n in connections['children']:
        v=property_values(n['props'],n['count'])
        if len(v)>2 and v[0]==b'OO' and v[2] in tree_models:
            child=id_to_node.get(v[1])
            if child is not None and child['name']==b'Geometry':
                geom_for_model[v[2]]=v[1]

    removed_models=set()
    for mid,(name,idx) in sorted(tree_models.items(),key=lambda x:x[1][1]):
        if random.Random(808800+idx).random()<0.30:
            removed_models.add(mid)
    removed_geoms={geom_for_model[mid] for mid in removed_models if mid in geom_for_model}
    removed_ids=removed_models|removed_geoms
    objects['children']=[n for n in objects['children'] if not (
        property_values(n['props'],n['count']) and isinstance(property_values(n['props'],n['count'])[0],int)
        and property_values(n['props'],n['count'])[0] in removed_ids)]
    kept_connections=[]
    for n in connections['children']:
        v=property_values(n['props'],n['count'])
        refs=[x for x in v[1:3] if isinstance(x,int)]
        if any(x in removed_ids for x in refs): continue
        kept_connections.append(n)
    connections['children']=kept_connections

    objects=next(n for n in nodes if n['name']==b'Objects')
    connections=next(n for n in nodes if n['name']==b'Connections')
    models={}
    for n in objects['children']:
        if n['name']==b'Model':
            v=property_values(n['props'],n['count']);models[v[0]]=v[1].split(b'\x00')[0].decode(errors='ignore')
    bound={}
    for n in connections['children']:
        v=property_values(n['props'],n['count'])
        if len(v)>2 and v[2] in models: bound[v[1]]=models[v[2]]

    changed=[];total_vertices=0
    for geom in objects['children']:
        if geom['name']!=b'Geometry': continue
        gv=property_values(geom['props'],geom['count']); name=bound.get(gv[0],'')
        if not name.startswith('tree_'): continue
        try: idx=int(name.split('_')[-1])
        except: continue
        vn=next(n for n in geom['children'] if n['name']==b'Vertices')
        a=array_from_node(vn); nverts=len(a)//3; total_vertices+=nverts
        xs=a[0::3]; ys=a[1::3]; zs=a[2::3]
        miny=min(ys)
        base=[i for i,y in enumerate(ys) if y<miny+3.0]
        if not base: base=[min(range(nverts),key=lambda i:ys[i])]
        ax=sum(xs[i] for i in base)/len(base); az=sum(zs[i] for i in base)/len(base); ay=miny
        rng=random.Random(80081+idx)
        if idx%9==0:
            base_scale=rng.uniform(.58,.70); sy=rng.uniform(.58,.72)
        else:
            base_scale=rng.uniform(.78,.92); sy=rng.uniform(.76,.91)
        sx=base_scale*rng.uniform(.94,1.06); sz=base_scale*rng.uniform(.94,1.06)
        for i in range(nverts):
            j=3*i
            a[j]=ax+(a[j]-ax)*sx
            a[j+1]=ay+(a[j+1]-ay)*sy
            a[j+2]=az+(a[j+2]-az)*sz
        vn['props']=encoded_double_array(a)
        changed.append(dict(model=name,vertices=nverts,scale_x=round(sx,4),scale_y=round(sy,4),scale_z=round(sz,4)))

    out=encode(nodes,tail);parse(out);path.write_bytes(out)
    return dict(original_tree_models=len(tree_models),removed_tree_models=len(removed_models),
                remaining_tree_models=len(changed),remaining_tree_vertices=total_vertices,
                changes=changed,source_sha256=hashlib.sha256(data).hexdigest(),
                result_sha256=hashlib.sha256(out).hexdigest(),source_bytes=len(data),result_bytes=len(out))

def main():
    REPORT.mkdir(exist_ok=True);BACKUP.mkdir(exist_ok=True)
    texture_dir=ROOT/'04_TEXTURES'
    scenery=ROOT/'07_OBJECTS_SOURCE/scenery.fbx'
    if not scenery.is_file(): raise SystemExit('Missing 07_OBJECTS_SOURCE/scenery.fbx')
    before={'textures':{},'scenery_sha256':sha(scenery)}
    for name,cfg in DIRT.items():
        p=texture_dir/name
        if not p.is_file(): raise SystemExit('Missing '+str(p))
        before['textures'][name]=sha(p)
        bp=BACKUP/name
        if not bp.exists(): shutil.copy2(p,bp)
        adjust_texture(p,cfg)
    sb=BACKUP/'scenery.fbx'
    if not sb.exists(): shutil.copy2(scenery,sb)
    tree=tree_fix(scenery)
    after={'textures':{n:sha(texture_dir/n) for n in DIRT},'scenery_sha256':sha(scenery)}
    report={'scope':'visual only; terrain/track.tht/race data untouched', 'before':before,'after':after,'tree_fix':tree,
            'texture_adjustments':DIRT}
    (REPORT/'v008b_visual_fix_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('v008b visual correction complete')
    print('Textures adjusted:',len(DIRT))
    print('Trees:',tree['original_tree_models'],'original;',tree['removed_tree_models'],'removed;',tree['remaining_tree_models'],'remaining')
    print('Remaining tree vertices:',tree['remaining_tree_vertices'])
    print('Scenery FBX bytes:',tree['source_bytes'],'->',tree['result_bytes'])
    print('Backups:',BACKUP)
    print('Report:',REPORT/'v008b_visual_fix_report.json')

if __name__=='__main__': main()
