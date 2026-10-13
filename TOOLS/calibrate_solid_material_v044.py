"""Calibrate constant-material native representation with official small exports."""
import base64, copy, hashlib, json, struct, subprocess, urllib.request, zipfile
from PIL import Image
from v044_common import R, O, sha, save
from v044_source import blob
from inspect_native_bitmap_records import restore_source
from v027_scenery import parse, encode, values, child
from v037_fbx import mapped_geometry, node, setvalues
from validate_native_textures_v024 import bitmap_signature, texture_record

def main():
    restore_source()
    roots, tail = parse((O/'scenery.fbx').read_bytes())
    objects = next(n for n in roots if n['name']==b'Objects')
    connections = next(n for n in roots if n['name']==b'Connections')
    byid = {values(n)[0]:n for n in objects['children']}
    links = [values(n) for n in connections['children']]
    material = next(n for n in byid.values() if n['name']==b'Material' and values(n)[1].split(b'\0')[0]==b'bark')
    mi = values(material)[0]
    ti = next(v[1] for v in links if v[2]==mi and byid.get(v[1],{}).get('name')==b'Texture')
    vi = next(v[1] for v in links if v[2]==ti and byid.get(v[1],{}).get('name')==b'Video')
    template = next(n for n in byid.values() if n['name']==b'Model' and values(n)[1].split(b'\0')[0]==b'covered_stand_timber')
    mid = values(template)[0]; gid = max(byid)+10000
    directory = R/'DOCUMENTATION/v044_material_probe'; directory.mkdir(parents=True,exist_ok=True)
    tools = directory/'tools'; tools.mkdir(exist_ok=True)
    version = json.loads((R/'BUILD/tool_versions.json').read_text())['ct.zip']
    archive = tools/'ct.zip'
    with urllib.request.urlopen(version['url'],timeout=120) as response, archive.open('wb') as output:
        output.write(response.read())
    assert sha(archive)==version['sha256']
    with zipfile.ZipFile(archive) as zipped:zipped.extractall(tools)
    exe = tools/'fbx2edf/fbx2edf_x64.exe'
    report = {'official_tools_sha256':version['sha256'],'cases':[]}
    mesh=dict(name='material_probe',vertices=[[100.,0.,100.],[102.,0.,100.],[102.,2.,100.],[100.,2.,100.]],faces=[[0,1,2],[0,2,3]],uv=[[[0.,0.],[1.,0.],[1.,1.]],[[0.,0.],[1.,1.],[0.,1.]]])
    for variant in ['legacy_constant','modern_constant','modern_pattern','solid_colour_control','solid_colour_changed_control']:
        image = Image.new('RGB',(16,16),(82,58,40))
        if variant=='modern_pattern':image.putpixel((0,0),(83,58,40))
        texture_path=directory/'probe.tga';image.save(texture_path);image_data=texture_path.read_bytes()
        scene=copy.deepcopy(roots)
        oo=next(n for n in scene if n['name']==b'Objects');cc=next(n for n in scene if n['name']==b'Connections')
        mt=copy.deepcopy(material);tx=copy.deepcopy(byid[ti]);vd=copy.deepcopy(byid[vi]);mdl=copy.deepcopy(template)
        setvalues(mt,mi,b'probe_material\0\1Material','')
        setvalues(mdl,mid,b'material_probe\0\1Model','Mesh')
        for p in child(mdl,b'Properties70')['children']:
            v=values(p)
            if v[0] in [b'Lcl Translation',b'Lcl Rotation']:setvalues(p,*v[:4],0.,0.,0.)
            elif v[0]==b'Lcl Scaling':setvalues(p,*v[:4],1.,1.,1.)
        rgb=[1.,1.,1.]
        if variant=='solid_colour_control':rgb=[82/255,58/255,40/255]
        if variant=='solid_colour_changed_control':rgb=[170/255,3/255,223/255]
        for p in child(mt,b'Properties70')['children']:
            v=values(p)
            if v[0] in [b'DiffuseColor',b'AmbientColor']:setvalues(p,*v[:4],*rgb)
            elif v[0]==b'Diffuse':setvalues(p,*v[:4],1.)
        for target in [tx,vd]:
            for c in target['children']:
                if c['name'] in [b'Filename',b'FileName',b'RelativeFilename']:setvalues(c,'probe.tga')
                elif c['name']==b'Content':c['count']=1;c['props']=b'R'+struct.pack('<I',len(image_data))+image_data
                elif c['name']==b'Properties70' and variant.startswith('modern'):
                    for p in c['children']:
                        v=values(p)
                        if v[0] in [b'Path',b'Filename',b'FileName',b'RelativeFilename']:setvalues(p,*v[:4],'probe.tga')
                        elif v[0]==b'UVSet':setvalues(p,*v[:4],'UVMap')
        if variant.startswith('modern'):
            props=child(tx,b'Properties70')
            if not any(values(p)[0]==b'UVSet' for p in props['children']):props['children'].append(node('P','UVSet','KString','','','UVMap'))
        geometry=mapped_geometry(gid,mesh)
        for c in geometry['children']:
            if c['name'].startswith(b'LayerElement') or c['name']==b'Layer':c['count']=1;c['props']=b'I'+struct.pack('<i',0)
        plain=variant.startswith('solid_colour')
        oo['children']=[mt,geometry,mdl] if plain else [mt,tx,vd,geometry,mdl]
        cc['children']=[node('C','OO',gid,mid),node('C','OO',mi,mid),node('C','OO',mid,0)]
        if not plain:cc['children'] += [node('C','OO',vi,ti),node('C','OP',ti,mi,'DiffuseColor')]
        defs=next(n for n in scene if n['name']==b'Definitions')
        for c in defs['children']:
            if c['name']==b'Count':c['count']=1;c['props']=b'I'+struct.pack('<i',len(oo['children']))
            elif c['name']==b'ObjectType':
                count=child(c,b'Count');count['count']=1;count['props']=b'I'+struct.pack('<i',sum(n['name']==values(c)[0] for n in oo['children']))
        fbx=directory/(variant+'.fbx');fbx.write_bytes(encode(scene,tail))
        edf=directory/(variant+'.edf');params=directory/'edf_params.ini';params.write_text('[params]\ntype=0\nuse_normals=1\n')
        run=subprocess.run([str(exe),str(fbx),str(edf),str(params),'-q'],cwd=directory,capture_output=True,text=True,timeout=120)
        assert run.returncode==0 and 'ERROR:' not in (run.stdout+run.stderr).upper(),(variant,run.stdout,run.stderr)
        raw=edf.read_bytes();assert raw[:4]==b'EDF\0'
        row=dict(variant=variant,bytes=len(raw),edf_sha256=sha(edf),source_material_rgb=rgb,
                 normalized_pixel_rgb_offsets=[raw.find(struct.pack('<3f',82/255,58/255,40/255)),raw.find(struct.pack('<3f',170/255,3/255,223/255))],
                 material_rgb_offset=raw.find(struct.pack('<3f',*rgb)),pixel_rgba_offset=raw.find(bytes([82,58,40,255])),pixel_bgra_offset=raw.find(bytes([40,58,82,255])))
        try:row['bitmap_record']=texture_record(raw,texture_path);row['bitmap_present']=True
        except RuntimeError as error:row['bitmap_present']=False;row['bitmap_error']=str(error)
        row['native_edf_base64_blob']=blob(base64.b64encode(raw).decode())
        print('SOLID_MATERIAL_PROBE '+json.dumps(row),flush=True);report['cases'].append(row)
    save(directory/'report.json',report)
    print('CODEX_V044_SOLID_MATERIAL_PROBE_BLOB '+blob(json.dumps(report)),flush=True)

if __name__=='__main__':main()
