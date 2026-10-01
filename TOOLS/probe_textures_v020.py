"""Small native texture/UV regression probes; exports no game candidate."""
from pathlib import Path
import copy,json,struct,subprocess,urllib.request,zipfile,hashlib,shutil
import numpy as np
from PIL import Image
from build_v019 import materialize_runtime
materialize_runtime()
from append_vehicles_v019 import geometry
from append_facilities_v019 import node,integer,arr,child,values,setvalues,parse,encode
R=Path(__file__).resolve().parents[1];D=R/'DOCUMENTATION/v020_texture_probe';D.mkdir(parents=True,exist_ok=True)

def main():
    subprocess.run(['python',str(R/'TOOLS/materialize_v009_baseline.py')],cwd=R,check=True)
    base=R/'BUILD/v009_baseline/scenery.fbx'
    nodes,tail=parse(base.read_bytes());objects=next(n for n in nodes if n['name']==b'Objects');connections=next(n for n in nodes if n['name']==b'Connections');byid={values(n)[0]:n for n in objects['children'] if n['count']}
    mat=next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0] in [b'marker_white',b'white']);mi=values(mat)[0]
    ti=next(values(n)[1] for n in connections['children'] if values(n)[2]==mi and byid.get(values(n)[1],{}).get('name')==b'Texture')
    vi=next(values(n)[1] for n in connections['children'] if values(n)[2]==ti and byid.get(values(n)[1],{}).get('name')==b'Video')
    model=next(n for n in byid.values() if n['name']==b'Model');mid=values(model)[0];gid=mid+123456789
    def desc(n):
        v=values(n);return dict(name=n['name'].decode(),types=n['props'][:1].decode(),values=[str(x)[:400] for x in v],children=[desc(c) for c in n['children']])
    (D/'template.json').write_text(json.dumps([desc(x) for x in [mat,byid[ti],byid[vi]]],indent=2))
    tex=np.zeros((256,256,3),np.uint8);yy,xx=np.mgrid[:256,:256];tex[:,:,0]=xx;tex[:,:,1]=yy;tex[:,:,2]=(xx^yy);Image.fromarray(tex).save(D/'probe.tga');raw=(D/'probe.tga').read_bytes()
    mesh=dict(name='texture_probe',vertices=[[-1.0,0.0,0.0],[1.0,0.0,0.0],[1.0,2.0,0.0],[-1.0,2.0,0.0]],faces=[[0,1,2],[0,2,3]],uv=[[[0.0,0.0],[1.0,0.0],[1.0,1.0]],[[0.0,0.0],[1.0,1.0],[0.0,1.0]]])
    tools=R/'BUILD/probe_tools';tools.mkdir(exist_ok=True);versions=json.loads((R/'BUILD/tool_versions.json').read_text());key='ct.zip';ver=versions[key]
    data=urllib.request.urlopen(ver['url'],timeout=60).read();assert hashlib.sha256(data).hexdigest()==ver['sha256'];p=tools/key;p.write_bytes(data)
    with zipfile.ZipFile(p) as z:z.extractall(tools)
    exe=tools/'fbx2edf/fbx2edf_x64.exe';results=[]
    for variant in ['legacy','typed_uv','file_properties','all_fixes','diffuse_alias','non_power_of_two']:
        Image.fromarray(tex).resize((256,320) if variant=='non_power_of_two' else (256,256)).save(D/'probe.tga');raw=(D/'probe.tga').read_bytes()
        nn=copy.deepcopy(nodes);oo=next(n for n in nn if n['name']==b'Objects');cc=next(n for n in nn if n['name']==b'Connections');mm=copy.deepcopy(model)
        setvalues(mm,mid,b'texture_probe\0\1Model','Mesh')
        for p in child(mm,'Properties70')['children']:
            v=values(p)
            if v[0] in [b'Lcl Translation',b'Lcl Rotation']:setvalues(p,*v[:4],0.,0.,0.)
            elif v[0]==b'Lcl Scaling':setvalues(p,*v[:4],1.,1.,1.)
        g=geometry(gid,mesh);mt=copy.deepcopy(mat);tx=copy.deepcopy(byid[ti]);vd=copy.deepcopy(byid[vi])
        for n in [tx,vd]:
            for c in n['children']:
                if c['name'] in [b'FileName',b'Filename',b'RelativeFilename']:setvalues(c,'probe.tga')
                elif c['name']==b'Content':c['props']=b'R'+struct.pack('<I',len(raw))+raw;c['count']=1
                elif c['name']==b'Properties70' and variant in ['file_properties','all_fixes','diffuse_alias']:
                    for p in c['children']:
                        v=values(p)
                        if v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],'probe.tga')
                        elif v[0]==b'UVSet':setvalues(p,*v[:4],'UVMap')
        if variant in ['typed_uv','all_fixes','diffuse_alias']:
            for c in g['children']:
                if c['name'].startswith(b'LayerElement') or c['name']==b'Layer':c['props']=b'I'+struct.pack('<i',0);c['count']=1
            uv=child(g,'LayerElementUV');setvalues(child(uv,'Name'),'UVMap');setvalues(child(uv,'ReferenceInformationType'),'IndexToDirect');uv['children'].append(arr('UVIndex',range(6),'i'))
            props=child(tx,'Properties70');p=next((x for x in props['children'] if values(x)[0]==b'UVSet'),None)
            if p:setvalues(p,*values(p)[:4],'UVMap')
            else:props['children'].append(node('P','UVSet','KString','','','UVMap'))
        oo['children']=[mt,tx,vd,g,mm]
        cc['children']=[node('C','OO',gid,mid),node('C','OO',mi,mid),node('C','OO',mid,0),node('C','OO',vi,ti),node('C','OP',ti,mi,'DiffuseColor')]
        if variant=='diffuse_alias':cc['children'].append(node('C','OP',ti,mi,'Diffuse'))
        defs=next(n for n in nn if n['name']==b'Definitions')
        for c in defs['children']:
            if c['name']==b'Count':c['props']=b'I'+struct.pack('<i',5)
            elif c['name']==b'ObjectType':child(c,'Count')['props']=b'I'+struct.pack('<i',sum(n['name']==values(c)[0] for n in oo['children']))
        f=D/(variant+'.fbx');f.write_bytes(encode(nn,tail));edf=D/(variant+'.edf');params=D/'edf_params.ini';params.write_text('[params]\ntype=0\nuse_normals=1\n')
        run=subprocess.run([str(exe),str(f),str(edf),str(params),'-q'],cwd=D,capture_output=True,text=True,timeout=120)
        b=edf.read_bytes() if edf.exists() else b'';results.append(dict(variant=variant,returncode=run.returncode,bytes=len(b),texture_name_offset=b.find(b'probe'),log=run.stdout+run.stderr));print(results[-1],flush=True)
    (D/'results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
