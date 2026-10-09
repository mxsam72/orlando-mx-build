"""Start/practice-only revision from immutable tested v033; main lap frozen."""
from pathlib import Path
import io,json,re,shutil,os
import numpy as np
from PIL import Image,ImageDraw
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from v033_common import atomic,save,sha,image_file,copy_exact
from v024_common import ease,start_path,route_point
from v028_common import sample_polyline
from reference_route import write_tcl

R=Path(__file__).resolve().parents[1];B=R/'V033_OUTPUT';O=R/'V035_OUTPUT';S=R/'V035_SOURCE';NAME='orlandomx_2026_v035'
def config():return json.loads((S/'start_fix.json').read_text())
def width(st,cfg=None):return np.interp(st,*np.array((cfg or config())['start_width_knots']).T)
def arrays(path,**data):
    b=io.BytesIO();np.savez_compressed(b,**data);atomic(path,b.getvalue())
def practice(sa,cfg):
    ss=np.linspace(0,cfg['practice_merge_start_station_m'],541)
    p=np.c_[[np.interp(ss,sa[:,3],sa[:,k]) for k in range(3)]].T
    taper=1-ease((ss-cfg['practice_offset_fade_start_station_m'])/(ss[-1]-cfg['practice_offset_fade_start_station_m']))
    offset=(width(ss,cfg)/2+cfg['practice_start_outer_clearance_m'])*taper
    xz=p[:,:2]+np.c_[np.sin(p[:,2]),-np.cos(p[:,2])]*offset[:,None]
    return sample_polyline(np.vstack([[440,168],xz]),.2)
def geometry():
    cfg=config();d=dict(np.load(B/'route.npz'));q=d['q'];sa,segs,th=start_path(cfg,q)
    assert np.linalg.norm(sa[-1,:2]-route_point(q,cfg['merge_station_m'])[:2])<1e-7
    write_tcl(O/'start.tcl',sa[0,:2],th,segs);d['start']=sa;arrays(O/'route.npz',**d)
    lane=practice(sa,cfg);arrays(O/'practice_access.npz',lane=lane,connector=np.load(B/'practice_access.npz')['connector'])
    save(O/'holeshot_layout.json',dict(**cfg,main_lap_length_m=float(q[-1,3]),start_length_m=float(sa[-1,3]),gate_to_first_curve_m=float(segs[0][1]-12),start_merge_xz_m=sa[-1,:2].tolist(),main_track_translation_m=0,main_native_tcl_byte_exact=sha(O/'main.tcl')==sha(B/'main.tcl')))
    return q,d['width'],sa,lane
def fields(n):
    cfg=config();old=np.load(B/'route.npz');new=np.load(O/'route.npz');q=old['q'];sa=new['start'];pl=np.load(O/'practice_access.npz')['lane'];oldpl=np.load(B/'practice_access.npz')['lane']
    axis=np.linspace(0,600,n);cols=np.flatnonzero((axis>=312)&(axis<=454));rows=np.flatnonzero((600-axis>=172)&(600-axis<=298))
    xx,zz=np.meshgrid(axis[cols],600-axis[rows]);rr,cc=np.meshgrid(rows,cols,indexing='ij');idx=(rr*n+cc).ravel();pts=np.c_[xx.ravel(),zz.ravel()]
    def along(route,knots):
        dd,ii=cKDTree(route[:,:2]).query(pts,workers=2);dv=pts-route[ii,:2];th=route[ii,2];st=route[ii,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th)
        ww=np.interp(st,*np.array(knots).T) if np.ndim(knots)==2 else np.broadcast_to(knots,len(st))
        return dd,ii,st,ww
    md,mi=cKDTree(q[:,:2]).query(pts,workers=2);mw=old['width'][mi];ms=q[mi,3]
    hp=mw/2+cfg['main_height_margin_m'];mp=mw/2+cfg['main_mask_margin_m']
    a,b=cfg['corner_protected_station_bounds_m'];corner=(ms>=a)&(ms<=b);hp[corner]=np.maximum(hp[corner],cfg['corner_protected_halfwidth_m']);mp[corner]=np.maximum(mp[corner],10.0)
    profiles=json.loads((B/'jump_profiles.json').read_text())
    for p in profiles:
        if p.get('crest_height_m',0)<=0:continue
        m=(ms>=p['station_start_m']-3)&(ms<=p['station_end_m']+3);hp[m]=np.maximum(hp[m],mw[m]/2+cfg['jump_extra_protection_m'])
    protect_h=md<=hp;protect_m=md<=mp;soft_h=ease((md-hp)/5);soft_m=ease((md-mp)/3)
    sd,si,st,sw=along(sa,cfg['start_width_knots']);od,oi,ost,ow=along(old['start'],json.loads((R/'V024_SOURCE/facilities.json').read_text())['start_width_knots'])
    pd,pi,pst,pw=along(pl,cfg['practice_width_m']);opd,opi,opst,opw=along(oldpl,cfg['practice_width_m'])
    def lane(dd,st,ww,L,feather=1.5):return (1-ease((dd-ww/2+.15)/feather))*ease((st+1)/2)*(1-ease((st-L)/2))
    start=lane(sd,st,sw,sa[-1,3]);oldstart=lane(od,ost,ow,old['start'][-1,3]);pract=lane(pd,pst,pw,pl[-1,3]);oldpract=lane(opd,opst,opw,oldpl[-1,3]);retire=np.maximum(oldstart,oldpract)
    region=np.maximum.reduce([start,pract,retire])>1e-8
    return dict(n=n,idx=idx,rows=rows,cols=cols,pts=pts,md=md,mi=mi,ms=ms,hp=hp,protect_h=protect_h,protect_m=protect_m,soft_h=soft_h,soft_m=soft_m,start=start,practice=pract,retire=retire,region=region,sd=sd,st=st,sw=sw)
def terrain():
    f=fields(2049);raw=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049);h=raw.ravel()[f['idx']].astype(float)/65535*18
    amount=np.maximum.reduce([f['start'],f['practice'],f['retire']])*f['soft_h'];target=h*(1-amount)+3*amount
    encoded=raw.ravel().copy();encoded[f['idx']]=np.rint(target/18*65535).astype('<u2');encoded=encoded.reshape(2049,2049);changed=encoded!=raw
    assert not changed.ravel()[f['idx']][f['protect_h']].any()
    atomic(O/'terrain.raw',encoded.tobytes());image_file(Image.fromarray(encoded),O/'terrain_16bit.png');b=io.BytesIO();np.save(b,encoded.astype(np.float32)/65535*18);atomic(O/'height_metres.npy',b.getvalue())
    allowed=np.zeros(raw.size,bool);allowed[f['idx']]=f['region'];assert not changed.ravel()[~allowed].any();image_file(Image.fromarray(allowed.reshape(raw.shape).astype(np.uint8)*255),O/'local_patch_region.png')
    gy,gx=np.gradient(encoded/65535*18,600/2048);grade=np.hypot(gx,gy);flat=(f['start']>.95)&(f['st']<82)&(f['sd']<f['sw']/2-1)
    qa=dict(checks_pass=True,baseline='v033',terrain_sha256=sha(O/'terrain.raw'),changed_samples=int(changed.sum()),main_riding_height_changes=0,full_T05_hill_and_bank_height_changes=0,jump_height_changes=0,corner_translation_m=0,start_runup_grade_max=float(grade.ravel()[f['idx']][flat].max()),only_start_and_practice_apron_terrain_changed=True,in_game_riding=False)
    assert qa['start_runup_grade_max']<.3;save(O/'holeshot_terrain_validation.json',qa);print('Terrain:',qa,flush=True)
def masks():
    cfg=config();reports=[]
    for n in [2048,4096]:
        f=fields(n);sm=f['soft_m'];start=f['start']*sm;pr=f['practice']*sm;retire=f['retire']*sm
        targets={'racing':255,'shoulder':255,'start':255,'visual_racing':250,'visual_worked':2,'visual_grass':0,'visual_sand':0,'off':0,'grass':0,'worked':0,'sand':0,'pits':0,'v032_packed':0,'v032_groom_0':0,'v032_groom_45':0,'v032_groom_90':0,'v032_groom_135':0,'v032_damp':0,'v032_face':0,'v032_pits':0}
        for folder in ['masks','materials']:
            for p in sorted((B/folder).glob('*.tga')):
                if folder=='materials' and not p.name.startswith('mask_'):continue
                key=p.stem.removeprefix('mask_')
                if key not in targets:continue
                with Image.open(p) as im:
                    if im.size!=(n,n):continue
                    arr=np.array(im.convert('RGBA'));orig=arr[:,:,3].ravel()[f['idx']].astype(float)
                background=255 if key=='off' else (170 if key=='visual_grass' else 0)
                v=orig*(1-retire)+background*retire;v=v*(1-start)+targets[key]*start
                pt=255 if key in ['pits','v032_pits','shoulder'] else (0 if key in ['racing','start','visual_racing','visual_worked'] else targets[key])
                v=v*(1-pr)+pt*pr;v[f['protect_m']]=orig[f['protect_m']];v[~f['region']]=orig[~f['region']]
                new=np.uint8(np.clip(np.rint(v),0,255));changed=new!=orig
                if changed.any():arr[:,:,3].flat[f['idx']]=new;image_file(Image.fromarray(arr),O/folder/p.name)
                assert not changed[f['protect_m']].any();reports.append(dict(file=folder+'/'+p.name,size=n,changed_pixels=int(changed.sum()),main_course_changed_pixels=0))
        print('Start-only alpha masks updated',n,flush=True)
    # Each retained atlas keeps its own baseline pixels outside the local edit.
    # Native materials override the unused similarly named mask copies at staging.
    for row in reports:row['sha256']=sha(O/row['file'])
    assert all(sha(p)==sha(O/'materials'/p.name) for p in (B/'materials').glob('v032_*.tga'))
    save(O/'holeshot_mask_validation.json',dict(checks_pass=True,masks=reports,all_color_tiles_byte_exact_v033=True,all_main_corner_material_masks_preserved=True))
def race():
    cfg=config();source=R/'12_RELEASE/orlandomx_2026_v033';dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.suffix in ['.map','.trh']:continue
        copy_exact(p,dest/p.name.replace('orlandomx_2026_v033',NAME))
    text=(source/'orlandomx_2026_v033.rdf').read_text()
    def rewrite(m):
        name,body=m.groups();line=re.search(r'(?m)^\s*line\s*=\s*(\d+)',body)
        if not line or int(line[1])!=2:return m[0]
        idx=int(name.removeprefix('checkpoint'));station=cfg['start_checkpoint_stations_m'][idx];half=width(station,cfg)/2+1
        for key,value in [('long',station),('left',-half),('right',half)]:body=re.sub(r'(?m)(^\s*'+key+r'\s*=\s*)[-\d.]+',lambda a:a[1]+f'{value:.9f}',body)
        return name+'\n{'+body+'}'
    text=re.sub(r'([A-Za-z_0-9]+)\s*\{([^{}]*)\}',rewrite,text,flags=re.S);atomic(dest/(NAME+'.rdf'),text.encode());atomic(O/(NAME+'.rdf'),text.encode())
    p=dest/(NAME+'.ini');text=p.read_text().replace('v033','v035');atomic(p,text.encode())
    d=np.load(O/'route.npz');im=Image.new('RGB',(1024,1024),(239,232,221));draw=ImageDraw.Draw(im)
    xy=lambda a:[tuple(v) for v in np.c_[a[:,0]/600*1023,(600-a[:,1])/600*1023]]
    draw.line(xy(d['q']),fill=(90,62,42),width=11);draw.line(xy(d['start']),fill=(204,132,46),width=12);image_file(im,dest/(NAME+'_map.tga'))
    # Main centerline/reset geometry stays exactly the last tested v033.
    for fn in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:assert sha(dest/fn)==sha(source/fn)
    save(O/'holeshot_race_validation.json',dict(checks_pass=True,all_main_race_references_byte_exact_v033=True,all_48_gate_and_pit_stalls_byte_exact=True,reset_limits_byte_exact_v033=True,start_checkpoint_stations_m=cfg['start_checkpoint_stations_m'],merge_before_first_lap_T05_checkpoint=True,main_native_tcl_byte_exact_v033=True,in_game_test=False))
def main():
    cfg=config();assert sha(B/'terrain.raw')==cfg['baseline_terrain_sha256'];assert sha(B/'scenery.fbx')==cfg['baseline_scenery_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(B,O);geometry();terrain();masks()
    from v035_scenery import main as scenery
    scenery();race();accepted=json.loads((B/'source_validation.json').read_text());qa={key:accepted[key] for key in ['pit_access','memorial','qwikchute','entry_sign']};qa.update(version='v035',source_commit=os.environ.get('GITHUB_SHA','local'),baseline_commit=cfg['baseline_source_commit'],terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),source_checks_pass=True,main_lap_and_all_corners_preserved_v033=True,holeshot=json.loads((O/'holeshot_layout.json').read_text()),geometry=json.loads((O/'holeshot_terrain_validation.json').read_text()),race=json.loads((O/'holeshot_race_validation.json').read_text()),only_local_start_and_practice_inputs_revised=True,all_dirt_color_tiles_byte_exact_v033=True,all_sign_art_preserved_v033=True,accepted_v033_source_validation=accepted)
    for fn in ['main.tcl','turns.json','jump_profiles.json','geometry_spec.json']:assert sha(B/fn)==sha(O/fn)
    save(O/'source_validation.json',qa);print('v035 start-only source complete from v033; main corner unchanged.',flush=True)
if __name__=='__main__':main()
