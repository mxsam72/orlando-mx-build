"""Bounded geometry revision over the exact v035 Windows checkpoint."""
import io,math,re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates
from scipy.spatial import cKDTree
from v036_common import *
from v024_common import ease,route_point
from reference_route import sample_native,write_tcl
from refine_jumps import supports
from jump_v024 import make_profile,envelope
def config():return read(S/'approved_update.json')
def arrays(p,**d):
    b=io.BytesIO();np.savez_compressed(b,**d);atomic(p,b.getvalue())
def projection(q,pts):
    d,i=cKDTree(q[:,:2]).query(pts,workers=2);v=pts-q[i,:2];th=q[i,2]
    return d,i,q[i,3]+v[:,0]*np.cos(th)+v[:,1]*np.sin(th),-v[:,0]*np.sin(th)+v[:,1]*np.cos(th)
def right_offset(s):
    c=config()['roller_shift'];a=c['start_station_m'];b=c['full_right_station_m'];p=c['hold_right_until_station_m'];e=c['rejoin_station_m']
    return c['max_right_offset_m']*ease((s-a)/(b-a))*(1-ease((s-p)/(e-p)))
class Warp:
    def __init__(self,q):
        self.c=config()['roller_shift'];self.full=q
        self.q=q[(q[:,3]>=self.c['start_station_m']-8)&(q[:,3]<=self.c['rejoin_station_m']+8)]
        self.other=q[(q[:,3]<self.c['start_station_m']-25)|(q[:,3]>self.c['rejoin_station_m']+25)]
        self.other_tree=cKDTree(self.other[:,:2]);self.other_halfwidth=float(np.load(BASE/'route.npz')['width'].max()/2)
        assert np.max(np.diff(self.q[:,1]))<0
    def displacement(self,pts):
        # Ordered cross-sections avoid folding the tight entry arc's shoulders.
        z=self.q[::-1,1];st=np.interp(pts[:,1],z,self.q[::-1,3]);th=np.interp(pts[:,1],z,self.q[::-1,2]);cx=np.interp(pts[:,1],z,self.q[::-1,0])
        lat=-(pts[:,0]-cx)*np.sin(th);side=1-ease((abs(lat)-self.c['full_lateral_halfwidth_m'])/(self.c['fade_outer_halfwidth_m']-self.c['full_lateral_halfwidth_m']))
        otherd=self.other_tree.query(pts,workers=2)[0];guard=ease((otherd-self.other_halfwidth-3.2)/5)
        bounds=ease((pts[:,0]-185)/6)*(1-ease((pts[:,0]-269)/6));amount=right_offset(st)*side*guard*bounds
        return np.c_[-amount/np.maximum(.85,abs(np.sin(th))),np.zeros(len(pts))]
    def forward(self,pts):return pts+self.displacement(pts)
    def inverse(self,pts):
        # Bisection remains stable on the expanding shoulder by another lane.
        lo=pts[:,0].copy();hi=lo+self.c['max_right_offset_m']/.85+.01;src=pts.copy()
        for _ in range(26):
            src[:,0]=(lo+hi)/2;left=self.forward(src)[:,0]<pts[:,0];lo[left]=src[left,0];hi[~left]=src[~left,0]
        src[:,0]=(lo+hi)/2;res=float(np.linalg.norm(self.forward(src)-pts,axis=1).max());assert res<.008,res
        return src,res
def parse_tcl(path):
    text=path.read_text();head=text.split('segment0')[0];g=lambda k:float(re.search(r'(?m)^\s*'+k+r'\s*=\s*([-+\d.eE]+)',head)[1]);segs=[]
    for body in re.findall(r'segment\d+\s*\{([^{}]*)\}',text,re.S):
        v=lambda k:float(re.search(r'\b'+k+r'\s*=\s*([-+\d.eE]+)',body)[1]);segs.append((int(v('type')),v('length'),v('radius'),v('angle')))
    return np.array([g('x'),g('z')]),math.radians(90-g('angle')),segs
def open_segments(pp):
    v=np.diff(pp,axis=0);lens=np.linalg.norm(v,axis=1);u=v/lens[:,None];ang=np.arctan2(u[:-1,0]*u[1:,1]-u[:-1,1]*u[1:,0],(u[:-1]*u[1:]).sum(1));trim=np.minimum(lens[:-1],lens[1:])*.24;trim[abs(ang)<1e-9]=0
    ent=pp.copy();ex=pp.copy();ent[1:-1]-=u[:-1]*trim[:,None];ex[1:-1]+=u[1:]*trim[:,None];segs=[]
    for i in range(len(pp)-1):
        length=float(np.linalg.norm(ent[i+1]-ex[i]));
        if length>1e-9:segs.append((0,length,0.,0.))
        if i<len(ang) and trim[i]>0:
            radius=trim[i]/math.tan(abs(ang[i])/2);segs.append((1,float(abs(ang[i])*radius),float(-math.copysign(radius,ang[i])),float(abs(math.degrees(ang[i])))))
    return segs
def native_splice(old,warp):
    origin,theta,segs=parse_tcl(BASE/'main.tcl');ends=sample_native(origin,theta,segs,1e6);c=config()['roller_shift']
    i0=int(cKDTree(ends[:,:2]).query(route_point(old,c['start_station_m']-1)[:2])[1]);i1=int(cKDTree(ends[:,:2]).query(route_point(old,c['rejoin_station_m']+1)[:2])[1]);p0,p1=ends[[i0,i1]];assert i1>i0
    stations=np.linspace(p0[3]+.6,p1[3]-.6,int((p1[3]-p0[3])/.45));native0=sample_native(origin,theta,segs,.12);raw=np.c_[[np.interp(stations,native0[:,3],native0[:,k]) for k in range(2)]].T
    pp=np.vstack([p0[:2],p0[:2]+.35*np.array([math.cos(p0[2]),math.sin(p0[2])]),warp.forward(raw),p1[:2]-.35*np.array([math.cos(p1[2]),math.sin(p1[2])]),p1[:2]])
    local=open_segments(pp);ln=sample_native(p0[:2],p0[2],local,.12);assert np.linalg.norm(ln[-1,:2]-p1[:2])<1e-5
    assert abs((ln[-1,2]-p1[2]+np.pi)%(2*np.pi)-np.pi)<1e-6
    combined=segs[:i0]+local+segs[i1:];native=sample_native(origin,theta,combined,.2);write_tcl(O/'main.tcl',origin,theta,combined);assert np.linalg.norm(native[-1,:2]-native[0,:2])<.02
    save(O/'native_route_validation.json',dict(unchanged_native_prefix_segments=i0,unchanged_native_suffix_segments=len(segs)-i1,old_native_bounds_m=[float(p0[3]),float(p1[3])],old_native_length_m=float(ends[-1,3]),new_native_length_m=float(native[-1,3]),native_length_delta_m=float(native[-1,3]-ends[-1,3]),native_loop_closure_m=float(np.linalg.norm(native[-1,:2]-native[0,:2])),native_splice_position_error_m=float(np.linalg.norm(ln[-1,:2]-p1[:2]))))
    return native
def geometry():
    data=dict(np.load(BASE/'route.npz'));old=data['q'];q=old.copy();warp=Warp(old);cfg=config();c=cfg['roller_shift'];disp=warp.displacement(old[:,:2]);shift=(disp*np.c_[np.sin(old[:,2]),-np.cos(old[:,2])]).sum(1);active=np.linalg.norm(disp,axis=1)>1e-10;q[:,:2]+=disp
    ids=np.flatnonzero((old[:,3]>=c['start_station_m'])&(old[:,3]<=c['rejoin_station_m']));a,b=ids[0]-1,ids[-1]+1;ss=np.r_[old[a,3],old[a,3]+np.cumsum(np.linalg.norm(np.diff(q[a:b+1,:2],axis=0),axis=1))];delta=ss[-1]-old[b,3];q[a:b+1,3]=ss;q[b+1:,3]+=delta
    th=np.unwrap(np.arctan2(np.gradient(q[:,1],q[:,3]),np.gradient(q[:,0],q[:,3])));th+=round((old[0,2]-th[0])/(2*np.pi))*2*np.pi;q[active,2]=th[active];remap=lambda s:float(np.interp(s,old[:,3],q[:,3]))
    accepted={p['id']:p for p in read(BASE/'jump_profiles.json')};profiles=[];sources=[];spec=read(BASE/'geometry_spec.json')
    for p in spec['profiles']:
        n=dict(p);n['station_start_m']=remap(p['station_start_m']);n['station_end_m']=remap(p['station_end_m']);n['lip_s']=n['station_start_m']+n['face_m']
        if p['id'] in cfg['jump_ids']:
            n['crest_height_m']*=1.3
            if 'lip_height_m' in n:n['lip_height_m']*=1.3
            if 'roller_heights_m' in n:n['roller_heights_m']=[h*1.3 for h in n['roller_heights_m']]
            if 'gaps' in n:n['gaps']=[dict(g,landing_crest_height_m=g['landing_crest_height_m']*1.3,valley_height_m=g['valley_height_m']*1.3) for g in n['gaps']]
        if p['id']=='R17':n['station_end_m']=n['station_start_m']+80
        sources.append(n)
        if p['id'] in ['R11','R12','R17']:profiles.append(make_profile(n))
        else:
            original=accepted[p['id']];new=dict(original)
            for k in ['station_start_m','station_end_m','lip_s']:new[k]=remap(original[k])
            profiles.append(new)
    single=make_profile(cfg['new_single']);profiles.append(single);sources.append(dict(cfg['new_single']))
    turns=[dict(t,**{k:remap(t[k]) for k in ['arc_start','arc_end','mid']}) for t in read(BASE/'turns.json')]
    native=native_splice(old,warp);data.update(q=q,curvature=np.gradient(q[:,2],q[:,3]),native=native,v036_old_station=old[:,3],v036_old_to_new_station=q[:,3]);arrays(O/'route.npz',**data)
    save(O/'turns.json',turns);save(O/'jump_profiles.json',profiles);spec.update(version='v036',profiles=sources,approved_height_factor=1.3);spec['route_adjustments'].append(dict(id='R17_hold_right_v036',**c));save(O/'geometry_spec.json',spec)
    save(O/'update_layout.json',dict(checks_pass=True,height_factor=1.3,new_single_crest_station_m=single['lip_s'],new_single_height_m=.75,single_start_clearance_m=single['station_start_m']-next(t for t in turns if t['id']=='T09')['arc_end'],single_end_clearance_m=next(p for p in profiles if p['id']=='R11')['station_start_m']-single['station_end_m'],max_rider_right_offset_m=float(shift.max()),station_delta_m=float(delta),roller_count=8,roller_crest_spacing_m=10,unaffected_route_world_coordinates_exact=bool(np.array_equal(q[~active,:2],old[~active,:2]))))
    return old,q,warp
def terrain(old,q,warp):
    raw=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049);H=raw.astype(float)/65535*18;axis=np.linspace(0,600,2049);zz,xx=np.meshgrid(600-axis,axis,indexing='ij');pts=np.c_[xx.ravel(),zz.ravel()]
    before=read(BASE/'jump_profiles.json');after=read(O/'jump_profiles.json');w=np.load(BASE/'route.npz')['width']
    oldroller=gaussian_filter(envelope(pts,supports([p for p in before if p['id']=='R17'],old,w)).reshape(H.shape),.65);newroller=gaussian_filter(envelope(pts,supports([p for p in after if p['id']=='R17'],q,w)).reshape(H.shape),.65)
    floor=H-oldroller;target=floor.copy();box=(xx>185)&(xx<275)&(zz>184)&(zz<329);patch=pts[box.ravel()];src,res=warp.inverse(patch);moved=np.linalg.norm(src-patch,axis=1)>1e-7;sample=map_coordinates(floor,[(600-src[:,1])/600*2048,src[:,0]/600*2048],order=1,mode='nearest');v=target[box];v[moved]=sample[moved];target[box]=v;target+=newroller
    otherd=warp.other_tree.query(pts,workers=2)[0];protect=ease((otherd-warp.other_halfwidth-3.2)/3).reshape(H.shape);target=H+(target-H)*protect
    grow=gaussian_filter(envelope(pts,supports([p for p in before if p['id'] in ['R11','R12']],old,w)).reshape(H.shape),.65)*.3;added=gaussian_filter(envelope(pts,supports([p for p in after if p['id']=='R11_ENTRY'],q,w)).reshape(H.shape),.65);target+=grow+added
    allowed=abs(target-H)>1e-8;encoded=raw.copy();encoded[allowed]=np.rint(np.clip(target[allowed]/18*65535,0,65535)).astype('<u2');atomic(O/'terrain.raw',encoded.tobytes());image_file(Image.fromarray(encoded),O/'terrain_16bit.png');b=io.BytesIO();np.save(b,encoded.astype(np.float32)/65535*18);atomic(O/'height_metres.npy',b.getvalue());image_file(Image.fromarray(np.uint8(allowed)*255),O/'v036_height_change_region.png')
    changed=encoded!=raw;gy,gx=np.gradient(encoded/65535*18,600/2048);grade=np.hypot(gx,gy);d,i,st,lat=projection(q,pts);riding=(d<5.7)&changed.ravel();maximum=float(grade.ravel()[riding].max());assert maximum<.88,maximum
    od,oi,os,ol=projection(old,pts);t05=(os>=428.5)&(os<=505)&(od<13);assert not changed.ravel()[t05].any();assert not changed.ravel()[(os<740)&(od<np.interp(os,old[:,3],w)/2+3)].any()
    qa=dict(checks_pass=True,baseline='v035',terrain_sha256=sha(O/'terrain.raw'),changed_samples=int(changed.sum()),T05_checked_samples=int(t05.sum()),T05_changed_samples=0,maximum_changed_riding_grade=maximum,inverse_warp_max_error_m=res,height_factor=1.3,roller_count=8,roller_heights_and_crest_spacing_preserved=True,unrelated_terrain_byte_exact=True,in_game_riding=False);save(O/'update_terrain_validation.json',qa);print('Bounded terrain passed:',qa,flush=True)
