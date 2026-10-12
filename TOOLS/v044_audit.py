"""Read the restored source, expose a bounded diagnostic snapshot, change nothing."""
import collections, io, base64, re
from PIL import Image, ImageDraw
from v044_common import *
from v044_source import blob
from v027_scenery import parse,values,child,vertices,geometry_records
from rebind_scenery import array
def main():
    raw=(BASE/'scenery.fbx').read_bytes();nodes,_=parse(raw)
    objs=next(n for n in nodes if n['name']==b'Objects')['children'];byid={values(n)[0]:n for n in objs}
    links=[values(n) for n in next(n for n in nodes if n['name']==b'Connections')['children']]
    mats={i:n for i,n in byid.items() if n['name']==b'Material'}
    geom=[]
    for name,(g,mid) in geometry_records(nodes).items():
        v=vertices(g);inds=array(child(g,b'PolygonVertexIndex'))
        materials=[values(mats[c[1]])[1].split(b'\0')[0].decode() for c in links if c[2]==mid and c[1] in mats]
        low=v[v[:,1]<v[:,1].min()+.6]
        geom.append(dict(name=name,vertices=len(v),faces=int((inds<0).sum()),materials=materials,
            bounds=[v.min(0).round(4).tolist(),v.max(0).round(4).tolist()],anchor=low[:,[0,2]].mean(0).round(4).tolist()))
    images=[]
    for folder in ['materials','facility_textures']:
        for p in sorted((BASE/folder).glob('*.tga')):
            with Image.open(p) as im:
                mean=np.asarray(im.resize((32,32)).convert('RGB')).mean((0,1)).round(2).tolist()
                images.append(dict(folder=folder,name=p.name,size=list(im.size),mode=im.mode,mean=mean))
    text={}
    for folder in ['materials','facility_textures']:
        for p in sorted((BASE/folder).glob('*.shd')):text[folder+'/'+p.name]=p.read_text()
    text['compiled_track.hmf']=(BASE/'compiled_track.hmf').read_text()
    release=R/'12_RELEASE/orlandomx_2026_v043'
    text['amb']=(release/'orlandomx_2026_v043.amb').read_text()
    route=dict(np.load(BASE/'route.npz'));route_view={k:np.asarray(v)[::max(1,len(v)//120)].round(4).tolist() if np.asarray(v).ndim else v.item() for k,v in route.items()}
    qa=read(R/'BUILD/v044_baseline_native_validation.json')
    audit=dict(version='v043',native_baseline_verified=True,scenery_sha256=sha(BASE/'scenery.fbx'),terrain_sha256=sha(BASE/'terrain.raw'),
        source_files=[str(p.relative_to(BASE)) for p in sorted(BASE.rglob('*')) if p.is_file()],textures=images,
        shaders_and_environment=text,geometry=geom,route=route_view,materials_properties={str(i):str(values(n)[1]) for i,n in mats.items()},
        native_qa_summary={k:qa[k] for k in ['source_commit','pkz_bytes','pkz_sha256','native_trh_identical_to_v042'] if k in qa})
    save(R/'DOCUMENTATION/v044_baseline_audit.json',audit)
    print('CODEX_V044_AUDIT_BLOB '+blob(json.dumps(audit)),flush=True)
    # Small lossless texture contact sheets for internal visual QA.
    for label,folder,names in [
        ('soil','materials',[x['name'] for x in images if x['folder']=='materials' and x['name'].startswith('v032_') and not any(s in x['name'] for s in ['_n.','_wet'])]),
        ('scenery','facility_textures',[x['name'] for x in images if x['folder']=='facility_textures' and any(s in x['name'] for s in ['tree','leaf','bark','grass','white','timber','green','alloy','steel','v041_'])][:35])]:
        sheet=Image.new('RGB',(768,((len(names)+3)//4)*220),(32,36,39));d=ImageDraw.Draw(sheet)
        for j,name in enumerate(names):
            with Image.open(BASE/folder/name) as im:
                im.thumbnail((185,185));x=j%4*192;y=j//4*220;sheet.paste(im.convert('RGB'),(x,y));d.text((x+2,y+188),name[:29],fill='white')
        b=io.BytesIO();sheet.save(b,format='PNG')
        print('CODEX_V044_'+label.upper()+'_SHEET_BLOB '+blob(base64.b64encode(b.getvalue()).decode()),flush=True)
    print('Audit textures:',len(images),'geometry records:',len(geom),flush=True)
if __name__=='__main__':main()
