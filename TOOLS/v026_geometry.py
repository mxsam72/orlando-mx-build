"""Local R10/T09 revision over the accepted v025 heightmap.

Only a bounded corridor changes. Native distance is recomputed after relocating
the corner, and unrelated physical world geometry remains byte-for-byte exact.
Dimensions are tuning estimates; real riding remains required.
"""
from pathlib import Path
import json, math, hashlib
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.interpolate import CubicHermiteSpline
from scipy.spatial import cKDTree
from PIL import Image
from jump_v024 import make_profile, envelope
from refine_jumps import supports
from reference_route import native_segments, sample_native, write_tcl
from v024_common import ease

R=Path(__file__).resolve().parents[1];O=R/'V026_OUTPUT';S=R/'V026_SOURCE'
N=2049;SIZE=600.;SCALE=18.;DX=SIZE/(N-1)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def point(q,s):return np.array([np.interp(s,q[:,3],q[:,k]) for k in range(3)])
def projection(q,pts):
    tree=cKDTree(q[:-1,:2]);distance,i=tree.query(pts,workers=2)
    d=pts-q[i,:2];th=q[i,2]
    lateral=-d[:,0]*np.sin(th)+d[:,1]*np.cos(th)
    station=q[i,3]+d[:,0]*np.cos(th)+d[:,1]*np.sin(th)
    return distance,i,lateral,station

def adjusted_route(old,w,turn,cfg):
    a,b=turn['arc_start'],turn['arc_end'];end=cfg['T09_exit_rejoin_old_station_m'];shift=cfg['T09_forward_translation_m']
    pa=point(old,a);pb=point(old,b);pc=point(old,end)
    direction=np.array([math.cos(pa[2]),math.sin(pa[2])]);translation=shift*direction
    before=old[old[:,3]<a,:2]
    extension=pa[:2]+np.linspace(0,shift,int(shift/.10)+1)[:,None]*direction
    ss=np.linspace(a,b,int((b-a)/.10)+1)
    arc=np.column_stack([np.interp(ss,old[:,3],old[:,k]) for k in [0,1]])+translation
    origin=pb[:2]+translation;chord=np.linalg.norm(pc[:2]-origin)
    tangent0=np.array([math.cos(pb[2]),math.sin(pb[2])]);tangent1=np.array([math.cos(pc[2]),math.sin(pc[2])])
    spline=CubicHermiteSpline([0,chord],np.array([origin,pc[:2]]),np.array([tangent0,tangent1]))
    rejoin=spline(np.linspace(0,chord,int(chord/.10)+1))
    after=old[old[:,3]>end,:2]
    xz=np.vstack([before,extension,arc,rejoin,after])
    labels=np.r_[old[old[:,3]<a,3],np.full(len(extension),a),ss,np.linspace(b,end,len(rejoin)),old[old[:,3]>end,3]]
    keep=np.r_[True,np.linalg.norm(np.diff(xz,axis=0),axis=1)>1e-7];xz=xz[keep];labels=labels[keep]
    xz[-1]=xz[0];arc_s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xz,axis=0),axis=1))]
    s=np.linspace(0,arc_s[-1],int(np.ceil(arc_s[-1]/.20))+1)
    xy=np.column_stack([np.interp(s,arc_s,xz[:,k]) for k in [0,1]])
    heading=np.unwrap(np.arctan2(np.gradient(xy[:,1],s),np.gradient(xy[:,0],s)))
    q=np.column_stack([xy,heading,s,np.zeros(len(s))])
    oldtree=cKDTree(old[:-1,:2]);_,oi=oldtree.query(q[:,:2]);width=w[oi]
    moved=(s>float(cKDTree(q[:,:2]).query(pa[:2])[1])*np.median(np.diff(s)))&(s<np.interp(end,old[:,3],old[:,3])+70)
    width[moved]=turn['width'];width[-1]=width[0]
    def nearest_s(xz):return float(s[cKDTree(q[:,:2]).query(xz)[1]])
    newturn=dict(turn,arc_start=nearest_s(pa[:2]+translation),arc_end=nearest_s(pb[:2]+translation),mid=nearest_s(point(old,turn['mid'])[:2]+translation))
    mapping=np.interp(old[:,3],labels,arc_s)
    return q,width,newturn,mapping,translation

def berm_values(turn,cfg,lat,s,entry_lead=16):
    extent=(turn['arc_end']-turn['arc_start'])/2;dd=s-turn['mid'];phase=np.clip((dd+extent)/(2*extent),0,1)
    fade=ease((dd+extent+entry_lead)/18)*(1-ease((dd-extent+3)/18))
    out=-np.sign(turn['angle'])*lat;half=cfg['effective_width_m']/2
    peak=np.exp(-((dd-cfg['apex_shift_m'])/max(extent*.75,9))**2)
    load=(cfg['entry_load']*(1-phase)+cfg['exit_load']*phase)*(.62+.38*peak)
    wall=cfg['outer_rise_m']*load*ease((out+.9)/(half+.9))*(1-ease((out-half)/5.5))
    pocket=cfg['pocket_depth_m']*peak*np.exp(-((out+.25)/2.2)**2);groove=np.zeros_like(s)
    for p in cfg['rut_paths']:
        pos=np.where(phase<.5,p['entry_out_m']+(p['apex_out_m']-p['entry_out_m'])*ease(2*phase),p['apex_out_m']+(p['exit_out_m']-p['apex_out_m'])*ease(2*phase-1))
        groove+=p['depth_scale']*(.25+.75*peak)*np.exp(-((out-pos)/p['width_m'])**2)
    core=1-ease((abs(lat)-half+.3)/2)
    entry=np.exp(-((dd+extent+8)/13)**4);exit=np.exp(-((dd-extent-5)/10)**4)
    chop=.045*(entry*np.sin(2*np.pi*(dd+extent)/cfg['braking_spacing_m'])+.6*exit*np.sin(2*np.pi*dd/4.9))*core
    return fade*(wall-pocket-cfg['rut_depth_m']*groove)+chop

def main():
    O.mkdir(exist_ok=True);cfg=read(S/'geometry_changes.json');spec=read(R/'V024_SOURCE/v024_geometry_spec.json')
    data=dict(np.load(R/'V024_OUTPUT/route.npz'));old=data['q'];w=data['width'];base_u=np.fromfile(R/'V024_OUTPUT/terrain.raw','<u2').reshape(N,N)
    assert sha(R/'V024_OUTPUT/terrain.raw')=='4befe79d6820865f4aba34649a5b54ed22472e7a3c1e7f8d3d56f53f3e340d91'
    H=base_u.astype(np.float64)/65535*SCALE
    turns=read(R/'V009_SOURCE/baseline_geometry.json')['turns'];turn=next(t for t in turns if t['id']=='T09');bc=next(t for t in spec['berms'] if t['id']=='T09')
    q,width,nt,mapping,translation=adjusted_route(old,w,turn,cfg)
    # Source stations before/after the changed sector are mapped to the same
    # fixed world locations. The only carried jump is the small exit R11.
    before=read(R/'V024_OUTPUT/jump_profiles.json');profiles=[]
    oldsrc={p['id']:p for p in spec['profiles']};newsrc=[]
    remap=lambda s:float(np.interp(s,old[:,3],mapping))
    for p in spec['profiles']:
        n=dict(p);length=p['station_end_m']-p['station_start_m']
        if p['id']=='R10':
            n['station_start_m']=remap(p['station_start_m']);n['station_end_m']=n['station_start_m']+length
            n['crest_height_m']=n['lip_height_m']=p['crest_height_m']+cfg['R10_lip_raise_m']
        elif p['id']=='R11':
            n['station_start_m']=nt['arc_end']+cfg['R11_exit_gap_m'];n['station_end_m']=n['station_start_m']+length
        else:
            n['station_start_m']=remap(p['station_start_m']);n['station_end_m']=n['station_start_m']+length
        n['lip_s']=n['station_start_m']+n['face_m'];newsrc.append(n);profiles.append(make_profile(n))
    oldprofiles=[p for p in before if p['id'] in ['R10','R11']];newprofiles=[p for p in profiles if p['id'] in ['R10','R11']]
    olds=supports(oldprofiles,old,w);news=supports(newprofiles,q,width)
    axes=np.linspace(0,SIZE,N);oldcomp=np.zeros((N,N));newcomp=np.zeros((N,N));od=np.zeros((N,N));nd=np.zeros((N,N));os=np.zeros((N,N));ns=np.zeros((N,N));nw=np.zeros((N,N))
    for row in range(0,N,64):
        z,x=np.meshgrid(SIZE-axes[row:row+64],axes,indexing='ij');pts=np.c_[x.ravel(),z.ravel()];shape=x.shape;sl=slice(row,row+len(x))
        d,i,lat,s=projection(old,pts);d2,i2,lat2,s2=projection(q,pts)
        oc=envelope(pts,olds)+berm_values(turn,bc,lat,s)*(1-ease((d-w[i]/2-7)/1.5))
        nc=envelope(pts,news)+berm_values(nt,bc,lat2,s2,cfg['T09_entry_lead_m'])*(1-ease((d2-width[i2]/2-7)/1.5))
        oldcomp[sl]=oc.reshape(shape);newcomp[sl]=nc.reshape(shape);od[sl]=d.reshape(shape);nd[sl]=d2.reshape(shape);os[sl]=s.reshape(shape);ns[sl]=s2.reshape(shape);nw[sl]=width[i2].reshape(shape)
    # Match the baseline's subgrid smoothing; smooth only the authored changes.
    oldcomp=gaussian_filter(oldcomp,.65);newcomp=gaussian_filter(newcomp,.65)
    oldzone=(os>739)&(os<891)&(od<14.4)
    newzone=(ns>newprofiles[0]['station_start_m']-4)&(ns<remap(890)+4)&(nd<14.4)
    other_lane=(os<741.3)|(os>891);oldwidth=np.interp(os,old[:,3],w)
    protect_r09=(os<741.3)&(os>680)&(od<14.4)
    region=(oldzone|newzone)&~(other_lane&(od<oldwidth/2+1))&~protect_r09
    local=(np.abs(oldcomp)+np.abs(newcomp)>1e-6)&region
    # Remove the old feature contribution before rebuilding on a consistent
    # gently varying floor. Broad terrain outside this corridor is untouched.
    floor=H-oldcomp;smoothed=gaussian_filter(floor,3.0)
    floor=np.where(local,smoothed,floor)
    target=floor+newcomp;delta=np.where(region,target-H,0)
    # C2 taper at the outside shoulder and longitudinal patch boundaries.
    taper=np.maximum((1-ease((od-12.0)/2.4))*ease((os-739)/4)*(1-ease((os-886)/5)),(1-ease((nd-12.0)/2.4))*ease((ns-newprofiles[0]['station_start_m']+4)/4)*(1-ease((ns-remap(886))/5)))
    taper*=np.where(other_lane,ease((od-oldwidth/2-1)/2),1)
    target=H+delta*taper
    for iteration in range(100):
        gy,gx=np.gradient(target,DX);grade=np.hypot(gx,gy);bad=(grade>.82)&region
        if not bad.any():break
        amount=np.minimum(gaussian_filter(bad.astype(float),1.2)*5,.55)*taper*region
        target=target*(1-amount)+gaussian_filter(target,1.2)*amount
    encoded=base_u.copy();encoded[region]=np.rint(np.clip(target[region]/SCALE*65535,0,65535)).astype('<u2')
    assert np.array_equal(encoded[~region],base_u[~region]);encoded.tofile(O/'terrain.raw');Image.fromarray(encoded).save(O/'terrain_16bit.png')
    Image.fromarray(np.uint8(region)*255).save(O/'local_patch_region.png')
    np.save(O/'height_metres.npy',encoded.astype(np.float32)/65535*SCALE)
    origin,theta,segments=native_segments(q,station_spacing=1.0);native=sample_native(origin,theta,segments,.20);write_tcl(O/'main.tcl',origin,theta,segments)
    data.update(q=q,width=width,curvature=np.gradient(q[:,2],q[:,3]),native=native,old_to_new_station=mapping)
    if 'v005_s' in data:
        _,nearest_old=cKDTree(old[:,:2]).query(q[:,:2]);data['v005_s']=data['v005_s'][nearest_old]
    np.savez_compressed(O/'route.npz',**data)
    updated_turns=[]
    for t in turns:
        if t['id']=='T09':updated_turns.append(nt)
        else:updated_turns.append(dict(t,**{k:remap(t[k]) for k in ['mid','arc_start','arc_end']}))
    save(O/'turns.json',updated_turns);save(O/'jump_profiles.json',profiles);save(O/'geometry_spec.json',dict(spec,version='v026',profiles=newsrc))
    gy,gx=np.gradient(encoded.astype(float)/65535*SCALE,DX);grade=np.hypot(gx,gy)
    extent=(nt['arc_end']-nt['arc_start'])/2;dd=ns-nt['mid'];fade=ease((dd+extent+5)/18)*(1-ease((dd-extent+3)/18))
    effective=8.6+(bc['effective_width_m']-8.6)*fade
    for p in newprofiles:
        active=ease((ns-p['station_start_m']+3)/3)*(1-ease((ns-p['station_end_m'])/3));effective=effective*(1-active)+p['racing_width_m']*active
    ridable=region&(nd<effective/2+1)
    changed=encoded!=base_u;clearance=[]
    subs=q[::5];ww=width[::5];pairs=cKDTree(subs[:,:2]).query_pairs(15,output_type='ndarray')
    for i,j in pairs:
        separation=abs(subs[i,3]-subs[j,3]);separation=min(separation,q[-1,3]-separation)
        if separation<45:continue
        if not (730<subs[i,3]<remap(899) or 730<subs[j,3]<remap(899)):continue
        edge=np.linalg.norm(subs[i,:2]-subs[j,:2])-(ww[i]+ww[j])/2
        clearance.append(float(edge))
    p10=next(p for p in profiles if p['id']=='R10');pold=next(p for p in before if p['id']=='R10')
    qa=dict(version='v026',baseline='v025',source_checks_pass=True,terrain_changed_nodes=int(changed.sum()),outside_local_patch_changed_nodes=int(changed[~region].sum()),raw_sha256=sha(O/'terrain.raw'),
            patch_bounds_xz_m=[float(axes[np.where(changed)[1]].min()),float((SIZE-axes[np.where(changed)[0]]).min()),float(axes[np.where(changed)[1]].max()),float((SIZE-axes[np.where(changed)[0]]).max())],
            R10_old_lip_height_m=pold['crest_height_m'],R10_new_lip_height_m=p10['crest_height_m'],R10_old_designed_angle_deg=pold['takeoff_angle_deg'],R10_new_designed_angle_deg=p10['takeoff_angle_deg'],R10_total_length_m=p10['authored_total_length_m'],
            T09_translation_xz_m=translation.tolist(),T09_forward_translation_m=cfg['T09_forward_translation_m'],old_landing_to_corner_entry_m=turn['arc_start']-oldsrc['R10']['station_end_m'],new_landing_to_corner_entry_m=nt['arc_start']-p10['station_end_m'],
            T09_bank_dimensions_preserved=True,R11_profile_dimensions_preserved=True,R11_carried_to_new_exit=True,
            maximum_local_ridable_grade=float(grade[ridable].max()),maximum_patch_grade=float(grade[region].max()),native_closure_m=float(np.linalg.norm(native[-1,:2]-native[0,:2])),native_to_authored_route_max_m=float(cKDTree(q[:,:2]).query(native[:,:2])[0].max()),
            local_lane_min_clearance_m=min(clearance) if clearance else None,old_model_lap_length_m=float(old[-1,3]),new_model_lap_length_m=float(q[-1,3]),all_unrelated_terrain_exact=True,in_game_riding=False)
    qa['source_checks_pass']=bool(qa['outside_local_patch_changed_nodes']==0 and qa['new_landing_to_corner_entry_m']>4.5 and qa['maximum_local_ridable_grade']<.88 and qa['native_closure_m']<.02 and qa['native_to_authored_route_max_m']<.12 and (not clearance or min(clearance)>.5))
    save(O/'geometry_validation.json',qa);print(json.dumps(qa,indent=2),flush=True)
    if not qa['source_checks_pass']:raise RuntimeError('Local geometry validation failed')
if __name__=='__main__':main()
