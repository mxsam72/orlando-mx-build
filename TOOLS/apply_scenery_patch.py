#!/usr/bin/env python3
"""Lossless FBX 7400 node rewrite with validated, terrain-bound vertex updates.

The input and every replacement property are hash-checked. Untouched FBX
properties, materials, connections, axes and topology remain byte-identical.
Only Python's standard library is needed by the Windows native build.
"""
from pathlib import Path
import base64, hashlib, json, struct, zlib

ROOT=Path(__file__).resolve().parents[1]
NULL=bytes(13)

def digest(data):return hashlib.sha256(data).hexdigest()

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
    assert off==len(raw)
    return result

def parse(data):
    assert data[:23]==b'Kaydara FBX Binary  \x00\x1a\x00'
    assert struct.unpack_from('<I',data,23)[0]==7400
    def node(off):
        end,n,length,nlen=struct.unpack_from('<IIIB',data,off);off+=13
        assert end>off and end<=len(data)
        name=data[off:off+nlen];off+=nlen
        props=data[off:off+length];off+=length
        children=[]
        while off<end and data[off:off+13]!=NULL:
            child,off=node(off);children.append(child)
        sentinel=data[off:end]
        assert sentinel in (b'',NULL)
        return dict(name=name,count=n,props=props,children=children,sentinel=sentinel),end
    nodes=[];off=27
    while data[off:off+13]!=NULL:
        n,off=node(off);nodes.append(n)
    return nodes,data[off+13:]

def encode(nodes,tail):
    def node(n,start):
        payload=n['name']+n['props'];pos=start+13+len(payload)
        for child in n['children']:
            b=node(child,pos);payload+=b;pos+=len(b)
        payload+=n['sentinel'];end=start+13+len(payload)
        return struct.pack('<IIIB',end,n['count'],len(n['props']),len(n['name']))+payload
    result=b'Kaydara FBX Binary  \x00\x1a\x00'+struct.pack('<I',7400)
    for n in nodes:result+=node(n,len(result))
    result+=NULL
    # Blender's footer: unchanged ID, four zero bytes, alignment, version, magic.
    assert struct.unpack_from('<I',tail,len(tail)-140)[0]==7400
    result+=tail[:20]
    result+=bytes(16-(len(result)%16))
    result+=tail[-140:]
    return result

def apply(data,patch):
    assert digest(data)==patch['source_fbx_sha256'],'Unexpected source FBX'
    nodes,tail=parse(data);objects=next(n for n in nodes if n['name']==b'Objects')
    remaining=set(patch['replacements'])
    def visit(node,path):
        key='/'.join(map(str,path))
        if key in remaining:
            item=patch['replacements'][key]
            assert digest(node['props'])==item['before_sha256']
            node['props']=base64.b64decode(item['properties_base64'])
            remaining.remove(key)
        for i,child in enumerate(node['children']):visit(child,path+[i])
    for i,node in enumerate(nodes):visit(node,[i])
    assert not remaining
    out=encode(nodes,tail)
    parse(out)
    if 'result_fbx_sha256' in patch:assert digest(out)==patch['result_fbx_sha256']
    return out

def main():
    patch=json.loads((ROOT/'V007_SOURCE/scenery_patch.json').read_text())
    path=ROOT/'07_OBJECTS_SOURCE/scenery.fbx'
    data=path.read_bytes()
    if digest(data)==patch['result_fbx_sha256']:
        print('Scenery patch already applied and verified.');return
    path.write_bytes(apply(data,patch))
    print('Scenery vertex patch verified and applied:',len(patch['replacements']),'properties',flush=True)

if __name__=='__main__':main()
