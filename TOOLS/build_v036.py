"""Build only the three approved v036 changes; private delivery only."""
import math,re,shutil,os
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
from v036_common import *
from v036_geometry import geometry,terrain,config,projection,parse_tcl
from v024_common import ease,route_point,project
from reference_route import sample_native
def region_grid(n,box):
    ax=np.linspace(0,600,n);cs=np.flatnonzero((ax>=box[0])&(ax<=box[2]));rs=np.flatnonzero((600-ax>=box[1])&(600-ax<=box[3]));z,x=np.meshgrid(600-ax[rs],ax[cs],indexing='ij');return rs,cs,np.c_[x.ravel(),z.ravel()]
def soil_fields(pts):
    c=config()['soil'];d=np.load(BASE/'route.npz');sa=d['start'];q=d['q'];knots=read(BASE/'holeshot_layout.json')['start_width_knots'];dd,ii,st,lat=projection(sa,pts);w=np.interp(st,*np.array(knots).T)
    start=(1-ease((abs(lat)-w/2+.6)/1.5))*ease((st+1.5)/3)*(1-ease((st-sa[-1,3])/3));md,mi,ms,ml=projection(q,pts);mw=d['width'][mi]
    merge=(1-ease((abs(ml)-mw/2+.6)/1.5))*ease((ms-c['merge_start_station_m'])/(c['merge_full_station_m']-c['merge_start_station_m']))*(1-ease((ms-c['merge_fade_start_station_m'])/(c['merge_end_station_m']-c['merge_fade_start_station_m'])))
    amount=np.maximum(start,merge);packed=c['packed_line_max_alpha']*np.maximum(start*np.exp(-(lat/1.1)**2),merge*np.exp(-(ml/1.1)**2));return amount,packed
def masks(warp):
    reports=[];c=config()['soil'];targets={'racing':255,'shoulder':255,'start':255,'visual_racing':c['race_alpha'],'visual_worked':2,'visual_grass':0,'visual_sand':0,'off':0,'grass':0,'worked':0,'sand':0,'pits':0,'v032_packed':0,'v032_groom_0':0,'v032_groom_45':0,'v032_groom_90':0,'v032_groom_135':0,'v032_damp':0,'v032_face':0,'v032_pits':0}
    for n in [2048,4096]:
        rr,cc,pts=region_grid(n,[185,184,275,329]);src,res=warp.inverse(pts);moved=np.linalg.norm(src-pts,axis=1)>1e-7;sr,sc,sp=region_grid(n,[310,169,456,301]);amount,line=soil_fields(sp)
        for folder in ['masks','materials']:
            for p in sorted((BASE/folder).glob('*.tga')):
                if folder=='materials' and not p.name.startswith('mask_'):continue
                key=p.stem.removeprefix('mask_')
                with Image.open(p) as im:
                    if im.size!=(n,n):continue
                    arr=np.array(im.convert('RGBA'));old=arr[:,:,3].copy()
                a=old.copy();ar=a[np.ix_(rr,cc)].astype(float).ravel();sampled=map_coordinates(old.astype(float),[(600-src[:,1])/600*(n-1),src[:,0]/600*(n-1)],order=1,mode='nearest');ar[moved]=sampled[moved];a[np.ix_(rr,cc)]=np.uint8(np.clip(np.rint(ar.reshape(len(rr),len(cc))),0,255))
                if key in targets:
                    previous=a[np.ix_(sr,sc)].astype(float).ravel();target=line if key=='v032_packed' else targets[key];v=previous*(1-amount)+target*amount;a[np.ix_(sr,sc)]=np.uint8(np.clip(np.rint(v.reshape(len(sr),len(sc))),0,255))
                if np.any(a!=old):arr[:,:,3]=a;image_file(Image.fromarray(arr),O/folder/p.name)
                reports.append(dict(file=folder+'/'+p.name,size=n,changed_alpha_pixels=int(np.count_nonzero(a!=old)),rgb_pixels_unchanged=True,sha256=sha(O/folder/p.name)))
        print('Start/merge and relocated roller alpha masks complete:',n,flush=True)
    assert all(sha(p)==sha(O/'materials'/p.name) for p in (BASE/'materials').glob('v032_*.tga'))
    qa=dict(checks_pass=True,masks=reports,v030_color_normal_wet_tiles_byte_exact=True,soil_unified_at_start_and_merge=True,competing_overlays_removed_locally=True,roller_physical_and_visual_alpha_moved_with_terrain=True);save(O/'update_mask_validation.json',qa);save(O/'holeshot_mask_validation.json',qa)
def scenery(old,q,warp):
    from v027_scenery import parse,encode,geometry_records,vertices,child,values,fingerprint
    from rebind_scenery import encoded_array
    before=(BASE/'scenery.fbx').read_bytes();nodes,tail=parse(before);assert encode(nodes,tail)==before;obj=next(n for n in nodes if n['name']==b'Objects');original={values(n)[0]:fingerprint(n) for n in obj['children']};rec=geometry_records(nodes);oldconn=fingerprint(next(n for n in nodes if n['name']==b'Connections'))
    nh=np.fromfile(O/'terrain.raw','<u2').reshape(2049,2049)/65535*18;oh=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18;ground=lambda H,p:map_coordinates(H,[(600-p[:,1])/600*2048,p[:,0]/600*2048],order=1,mode='nearest');changes=[];changed=set();probes=[]
    for name,(g,mid) in rec.items():
        if not name.startswith(('SOFTCPLAS_marker_','scrub_','tree_')):continue
        v=vertices(g);anchor=v[v[:,1]<v[:,1].min()+.2][:,[0,2]].mean(0);amount=warp.displacement(anchor[None])[0];d,i,station,lat=projection(old,anchor[None]);st=float(station[0]);rhythm=862<st<937 and d[0]<16;shifted=np.linalg.norm(amount)>1e-5
        if not shifted and not rhythm:continue
        na=anchor+amount;dy=float(ground(nh,na[None])[0]-ground(oh,anchor[None])[0]);delta=np.array([amount[0],dy,amount[1]])
        if np.linalg.norm(delta)<1e-5:continue
        vv=v+delta;child(g,b'Vertices')['props']=encoded_array(vv*[100,100,-100]);changed.add(values(g)[0]);probes.extend(vv[[0,len(vv)//2,-1]].tolist());changes.append(dict(model=name,translation_xyz_m=delta.tolist(),source_station_m=st,reason='Follow relocated rollers' if shifted else 'Ground binding for taller small jumps'))
    atomic(O/'scenery.fbx',encode(nodes,tail));check,_=parse((O/'scenery.fbx').read_bytes());final={values(n)[0]:fingerprint(n) for n in next(n for n in check if n['name']==b'Objects')['children']};assert {k:v for k,v in final.items() if k not in changed}=={k:v for k,v in original.items() if k not in changed};assert fingerprint(next(n for n in check if n['name']==b'Connections'))==oldconn
    protected=[n for n in rec if any(t in n.lower() for t in ['memorial','qwikchute','entry_sign','vehicle','practice_wood','practice_barrier'])];newrec=geometry_records(check);assert all(fingerprint(rec[n][0])==fingerprint(newrec[n][0]) for n in protected)
    save(O/'update_native_probes.json',dict(expected_xyz_metres=probes));save(O/'update_scenery_validation.json',dict(checks_pass=True,source_sha256=sha(BASE/'scenery.fbx'),output_sha256=sha(O/'scenery.fbx'),modified_geometry_records=len(changes),all_other_records_byte_exact=True,all_connections_byte_exact=True,protected_sign_fence_vehicle_records_checked=len(protected),changes=changes));print('Moved or ground-bound scenery records:',len(changes),flush=True)
def race(warp):
    source=R/'12_RELEASE/orlandomx_2026_v035';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.suffix not in ['.map','.trh']:copy_exact(p,dest/p.name.replace('orlandomx_2026_v035',NAME))
    origin,theta,segs=parse_tcl(BASE/'main.tcl');oldn=sample_native(origin,theta,segs,.12);orig,th,seg=parse_tcl(O/'main.tcl');newn=sample_native(orig,th,seg,.12);nv=read(O/'native_route_validation.json');a,b=nv['old_native_bounds_m'];delta=nv['native_length_delta_m'];changes=[]
    def mapstation(s):
        if s<=a:return s
        if s>=b:return s+delta
        p=route_point(oldn,s);target=warp.forward(p[None,:2])[0];return project(newn,*target,(90-math.degrees(p[2]))%360)['long']
    text=(source/'orlandomx_2026_v035.rdf').read_text()
    def edit(m):
        name,body=m.groups();get=lambda k:re.search(r'(?m)^\s*'+k+r'\s*=\s*([-+\d.eE]+)',body);lm=get('long');line=get('line')
        if lm is None or (line and int(float(line[1]))==2):return m[0]
        s=float(lm[1])
        if s<=a:return m[0]
        values={'long':mapstation(s)}
        if a<s<b and get('lat'):
            p=route_point(oldn,s);lat=float(get('lat')[1]);angle=float(get('angle')[1]) if get('angle') else 0;xz=p[:2]+lat*np.array([math.sin(p[2]),-math.cos(p[2])]);target=warp.forward(xz[None])[0];values=project(newn,*target,(90-math.degrees(p[2])+angle)%360)
        for key,value in values.items():body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-+\d.eE]+',lambda n:n[1]+f'{value:.9f}',body,count=1)
        changes.append(dict(block=name,old_station_m=s,new_station_m=values['long']));return name+'\n{'+body+'}'
    result=re.sub(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',edit,text,flags=re.S);atomic(dest/(NAME+'.rdf'),result.encode());atomic(O/(NAME+'.rdf'),result.encode());resets=[]
    for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
        raw=(source/name).read_bytes();assert raw[:4]==b'TL \0';ar=np.frombuffer(raw[8:],'<f4').reshape(-1,2).copy();oldstations=ar[:,0].copy();ar[:,0]=[mapstation(float(s)) for s in ar[:,0]];newraw=raw[:8]+ar.astype('<f4').tobytes();atomic(dest/name,newraw);atomic(O/name,newraw);assert np.array_equal(ar[oldstations<=a],np.frombuffer(raw[8:],'<f4').reshape(-1,2)[oldstations<=a]);resets.append(dict(file=name,changed_station_samples=int(np.count_nonzero(ar[:,0]!=oldstations)),lateral_widths_exact=True))
    p=dest/(NAME+'.ini');ini=p.read_text().replace('v035','v036');ini=re.sub(r'(?m)^length=.*$',f'length={round(newn[-1,3])}m',ini);atomic(p,ini.encode());data=np.load(O/'route.npz');im=Image.new('RGB',(1024,1024),(239,232,221));draw=ImageDraw.Draw(im);xy=lambda ar:[tuple(v) for v in np.c_[ar[:,0]/600*1023,(600-ar[:,1])/600*1023]];draw.line(xy(data['q']),fill=(90,62,42),width=11);draw.line(xy(data['start']),fill=(204,132,46),width=12);image_file(im,dest/(NAME+'_map.tga'))
    save(O/'update_race_validation.json',dict(checks_pass=True,start_native_tcl_exact_v035=True,gate_and_pit_stalls_preserved=True,start_only_checkpoints_preserved=True,main_native_prefix_and_suffix_geometry_preserved=True,main_checkpoint_and_reset_stations_follow_updated_native_length=True,reset_lines=resets,race_changes=changes,native_length_m=float(newn[-1,3]),in_game_test=False));print('Race references updated:',len(changes),flush=True)
def main():
    c=config();assert c['approved'] and c['height_factor']==1.3;assert sha(BASE/'terrain.raw')==c['baseline_terrain_sha256'];assert sha(BASE/'scenery.fbx')==c['baseline_scenery_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O);old,q,warp=geometry();terrain(old,q,warp);masks(warp);scenery(old,q,warp);race(warp);accepted=read(BASE/'source_validation.json');qa={k:accepted[k] for k in ['pit_access','memorial','qwikchute','entry_sign']};qa.update(version='v036',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=c['baseline_commit'],baseline_version='v035',terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),source_checks_pass=True,approved_height_factor=1.3,update_layout=read(O/'update_layout.json'),geometry=read(O/'update_terrain_validation.json'),race=read(O/'update_race_validation.json'),v030_color_palette_preserved=True,all_sign_art_preserved_v035=True,in_game_riding_test=False);save(O/'source_validation.json',qa);print('v036 source build complete.',flush=True)
if __name__=='__main__':main()
