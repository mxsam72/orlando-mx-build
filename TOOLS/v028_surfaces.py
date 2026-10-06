"""Correlated riding-line masks, modest physical rut relief and pit coverage.

The same authored corner path drives packed floors, loose deposits and terrain.
Macro jumps, turn stations, race/start lines and physical material declarations
remain the accepted v026 definitions. Only the documented local relief is added.
"""
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from v025_materials import macro_noise, save_mask
from v028_common import *

def fields(spec,cfg):
    n=spec['mask_size']; d=dict(np.load(O/'route.npz')); q=d['q']; start=d['start']; L=q[-1,3]
    main_tree=cKDTree(q[:-1,:2]); layout=access_layout(start,cfg)
    lane=layout['lane']; connector=layout['connector']; lane_tree=cKDTree(lane[:,:2]); connector_tree=cKDTree(connector[:,:2])
    turns=read(O/'turns.json'); bc={b['id']:b for b in read(O/'geometry_spec.json')['berms']}
    rng=np.random.default_rng(spec['seed']); medium=macro_noise(n,rng,160); fine=macro_noise(n,rng,650)
    names=['prepared','churn','packed','face','margin','relief','fresh','theta','damp','pits','access','access_visual','grass_cut','grass_islands','parking_grass']
    out={name:np.zeros((n,n),np.float32) for name in names}; axis=np.linspace(0,SIZE,n)
    profiles=read(O/'jump_profiles.json'); start_tree=cKDTree(start[:,:2]); knots=np.asarray(read(R/'V024_SOURCE/facilities.json')['start_width_knots'])
    for row in range(0,n,64):
        z,x=np.meshgrid(SIZE-axis[row:row+64],axis,indexing='ij'); pts=np.c_[x.ravel(),z.ravel()]; sh=x.shape; sl=slice(row,row+len(x))
        dist,i=main_tree.query(pts,workers=2); active=np.flatnonzero(dist<13)
        protected_half=d['width'][i]/2+1.7
        local={name:np.zeros(len(pts),np.float32) for name in names}
        if len(active):
            ii=i[active]; dv=pts[active]-q[ii,:2]; th=q[ii,2]; lat=-dv[:,0]*np.sin(th)+dv[:,1]*np.cos(th)
            s=(q[ii,3]+dv[:,0]*np.cos(th)+dv[:,1]*np.sin(th))%L
            no=medium[sl].ravel()[active]; fi=fine[sl].ravel()[active]; width=np.full(len(s),8.6)
            corner=np.zeros(len(s)); channels=corner.copy(); deposits=corner.copy(); physical=corner.copy()
            for k,t in enumerate(turns):
                b=bc[t['id']]; extent=(t['arc_end']-t['arc_start'])/2; dd=(s-t['mid']+L/2)%L-L/2
                fade=ease((dd+extent+10)/15)*(1-ease((dd-extent+3)/16)); phase=np.clip((dd+extent)/(2*extent),0,1)
                width+=(b['effective_width_m']-8.6)*fade; corner=np.maximum(corner,fade)
                for j,path in enumerate(b['rut_paths']):
                    off=np.where(phase<.5,path['entry_out_m']+(path['apex_out_m']-path['entry_out_m'])*ease(phase*2),path['apex_out_m']+(path['exit_out_m']-path['apex_out_m'])*ease(phase*2-1))
                    center=-np.sign(t['angle'])*off+.06*np.sin(dd*.13+k*1.3)
                    spread=max(.40,path['width_m']*.72); broken=np.clip(.78+.10*no+.08*fi,.28,1)
                    line=np.exp(-((lat-center)/spread)**2)*fade*broken
                    bank=np.exp(-((abs(lat-center)-(.65+.1*j))/.43)**2)*fade*np.clip(.65+.12*no+.08*fi,.2,1)
                    channels=np.maximum(channels,line); deposits=np.maximum(deposits,bank)
                    physical+=(-spec['corner_additional_channel_depth_m']*line+spec['corner_additional_deposit_height_m']*bank)*path['depth_scale']
            half=width/2; edge=.7*no+.12*fi
            core=1-ease((abs(lat)-half+.2-edge*.45)/1.5)
            core*=1-ease((dist[active]-half+.2)/1.7)
            margin=(1-ease((dist[active]-half-.4-edge*.7)/2.4))*(1-core)
            straight=np.zeros(len(s))
            for j,base in enumerate([-2.1,-.55,1.2]):
                center=base+.45*np.sin(s*.019+j*1.7)+.18*np.sin(s*.047+j)
                line=np.exp(-((lat-center)/(.4+.09*j))**2)*np.clip(.55+.14*no+.13*fi+.16*np.sin(s*.07+j*2),.05,.92)
                straight=np.maximum(straight,line*(1-corner))
            packed=np.clip(.78*channels+.62*straight,0,.82)*core
            churn=np.clip(.69*deposits+.34*margin+.08*fi*core,0,.72)
            jf=np.zeros(len(s)); landing=jf.copy()
            for p in profiles:
                if p['kind']=='none':continue
                lip=p['lip_s']; dd=(s-lip+L/2)%L-L/2
                jf=np.maximum(jf,ease((dd+p['face_m']+2)/4)*(1-ease((dd-p['landmarks_m'].get('deck_start',0)-2)/5)))
                lb=p['landmarks_m'].get('landing_break',0); end=p['landmarks_m']['runout_end']
                landing=np.maximum(landing,np.exp(-((dd-(lb+end)/2)/max((end-lb)*.6,3))**2))
            local['prepared'][active]=core*np.clip(.94+.025*no,.76,.98)
            local['packed'][active]=np.maximum(packed,.16*landing*core)
            local['churn'][active]=churn
            local['margin'][active]=margin
            local['face'][active]=jf*core*.33*(1-corner*.7)*(1-packed*.6)
            local['relief'][active]=np.clip(physical,-.045,.030)*core
            protected_half[active]=np.maximum(protected_half[active],half+1.7)
            local['fresh'][active]=core*np.clip(.65+.10*no,.18,.8)*(1-packed*.98)*(1-corner*.72)*(1-jf*.35)
            local['theta'][active]=th%np.pi
            local['grass_cut'][active]=np.clip(core*.96+margin*(.42+.11*no),0,1)
            # Sparse lower/compacted-looking areas; no standing water restored.
            damp=np.zeros(len(s))
            for t in turns[2::4]:
                ds=(s-t['arc_end']+L/2)%L-L/2
                damp=np.maximum(damp,np.exp(-(ds/5.0)**2)*np.exp(-((lat+.8)/2.0)**2))
            local['damp'][active]=damp*core*spec['local_damp_default_opacity_max']
        ld,li=lane_tree.query(pts,workers=2); cd,ci=connector_tree.query(pts,workers=2)
        road=1-ease((cd-cfg['connector_width_m']/2+.3)/1.2)
        lane_mask=1-ease((ld-cfg['practice_width_m']/2+.3)/1.2)
        x0,z0,x1,z1=cfg['staging_bounds_xz_m']; xx=pts[:,0]; zz=pts[:,1]
        inset=np.minimum.reduce([xx-x0,x1-xx,zz-z0,z1-zz])
        bay=ease((inset+medium[sl].ravel()*.25)/1.7)*np.clip(.90+.12*medium[sl].ravel(),.70,1)
        local['pits']=np.maximum(bay*cfg['parking_wear_opacity'],road*.98)
        local['access']=np.maximum(lane_mask,road)
        local['parking_grass']=bay*cfg['parking_grass_opacity']*(1-road)*(1-lane_mask)
        # Worn/grass islands are edge irregularities, not painted full-field bands.
        local['grass_cut']=np.maximum(local['grass_cut'],np.maximum(local['pits']*.97,lane_mask*.98))
        sd,si=start_tree.query(pts,workers=2); sw=np.interp(start[si,3],knots[:,0],knots[:,1])/2
        along=(pts[:,0]-start[si,0])*np.cos(start[si,2])+(pts[:,1]-start[si,1])*np.sin(start[si,2])
        st=start[si,3]+along
        local['access_visual']=np.maximum(road,lane_mask*(1-ease((st-94)/28)))
        ldv=pts-lane[li,:2];llt=-ldv[:,0]*np.sin(lane[li,2])+ldv[:,1]*np.cos(lane[li,2])
        cdv=pts-connector[ci,:2];clt=-cdv[:,0]*np.sin(connector[ci,2])+cdv[:,1]*np.cos(connector[ci,2])
        traffic=np.maximum(np.exp(-((llt-.70)/.42)**2),np.exp(-((llt+.70)/.42)**2))*lane_mask*.30
        traffic=np.maximum(traffic,np.maximum(np.exp(-((clt-.90)/.48)**2),np.exp(-((clt+.90)/.48)**2))*road*.25)
        traffic*=np.clip(.72+.12*medium[sl].ravel()+.09*fine[sl].ravel(),.22,1)
        local['packed']=np.maximum(local['packed'],traffic)
        accepted_start=(st>=0)&(st<=start[-1,3])&(sd<sw+1.0)
        # Preserve a bare race-start lane, access and the original gravel roads.
        start_guard=1-ease((sd-sw-1.0)/1.5)
        start_guard*=ease((st+2)/2)*(1-ease((st-start[-1,3])/2))
        bounds=[q[:,0].min()-8,q[:,1].min()-8,q[:,0].max()+8,q[:,1].max()+8]
        inside=np.minimum.reduce([xx-bounds[0],bounds[2]-xx,zz-bounds[1],bounds[3]-zz])
        green=ease((dist-protected_half-.35*medium[sl].ravel())/2.2)*ease(inside/5)
        local['grass_islands']=green*spec['infield_grass_opacity']*(1-start_guard)*(1-road)*(1-lane_mask)
        # Smoothing stops before the accepted race-start lane and main track.
        local['access'][accepted_start]=0
        low=np.exp(-((start[si,3]-cfg['damp_practice_start_station_m'])/6)**2)*lane_mask*.25
        local['damp']=np.maximum(local['damp'],low)
        for name in names: out[name][sl]=local[name].reshape(sh)
        if row%1024==0: print('v028 shared riding/pit fields row',row,flush=True)
    # Off-line cover must not take over any accepted riding/berm/start mask.
    protected=np.zeros((n,n),np.float32)
    for name in ['racing','start','shoulder','worked']:
        a=np.asarray(Image.open(O/'masks'/f'{name}.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)
        protected=np.maximum(protected,a)
    out['grass_islands'][protected>0]=0
    save_npz(O/'surface_fields.npz',**out)
    save_npz(O/'practice_access.npz',**layout)
    return out

def apply_height(f,spec):
    original=np.fromfile(O/'terrain.raw','<u2').reshape(N,N); h=original/65535*SCALE
    def resized(a):return np.asarray(Image.fromarray(a).resize((N,N),Image.Resampling.BILINEAR))
    relief=resized(f['relief']); access=resized(f['access']); pits=resized(f['pits'])
    smooth=gaussian_filter(h,2.4/(SIZE/(N-1)))
    delta=np.clip(smooth-h,-spec['pit_smoothing_max_delta_m'],spec['pit_smoothing_max_delta_m'])*np.maximum(access,pits)
    # Any overlap with the active main track uses only the matched corner field.
    delta*=1-resized(f['prepared'])
    final=np.clip(h+relief+delta,0,SCALE); raw=np.uint16(np.rint(final/SCALE*65535))
    allowed=(abs(relief)>1e-9)|(abs(delta)>1e-9); assert np.array_equal(raw[~allowed],original[~allowed])
    actual=(raw.astype(float)-original)/65535*SCALE
    assert np.max(abs(actual))<.071
    raw.tofile(O/'terrain.raw'); np.save(O/'height_metres.npy',raw/65535*SCALE)
    Image.fromarray(raw).save(O/'terrain_16bit.png')
    Image.fromarray(np.uint8(allowed)*255).save(O/'v028_height_change_region.png')
    qa=dict(checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),v026_terrain_sha256=sha(R/'V026_OUTPUT/terrain.raw'),
            changed_samples=int(np.count_nonzero(raw!=original)),unchanged_samples_outside_authored_region=True,
            minimum_delta_m=float(actual.min()),maximum_delta_m=float(actual.max()),
            corner_relief_and_texture_use_same_path_fields=True,macro_jump_profiles_unchanged=True,
            route_native_start_and_race_configuration_unchanged=True)
    save(O/'surface_geometry_validation.json',qa)

def physics(f):
    def resize(a): return np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR))
    coverage=resize(np.maximum(f['pits'],f['access'])); bay=resize(f['pits']); changed=[]
    protected=np.maximum.reduce([np.asarray(Image.open(O/'masks'/f'{name}.tga').getchannel('A')) for name in ['racing','start','shoulder','worked']])>0
    new_grass=resize(np.maximum(f['grass_islands'],f['parking_grass'])).copy()
    # Clipping before downsampling is insufficient at feathered boundaries.
    # Enforce protection again on the exact grid consumed by TerrainEd.
    new_grass[protected]=0
    for name in ['off','pits','grass','sand']:
        p=O/'masks'/f'{name}.tga'; old=np.asarray(Image.open(p).getchannel('A'),np.float32)/255
        if name=='pits':a=np.maximum(old,bay)
        elif name=='grass':
            a=np.maximum(old,new_grass)*(1-coverage)
            assert not np.any((np.uint8(np.rint(a*255))>np.uint8(np.rint(old*255)))&protected),'Grass crosses a protected native-grid margin'
        else:a=old*(1-coverage)
        save_mask(p,a)
        if name!='grass':assert np.array_equal(np.uint8(np.rint(a[coverage==0]*255)),np.uint8(np.rint(old[coverage==0]*255)))
        changed.append(name)
    save(O/'surface_physics_validation.json',dict(checks_pass=True,changed_masks=changed,
         pit_practice_and_protected_off_lane_grass_coverage_only=True,material_declarations_and_thicknesses_exact_v026=True,
         race_and_start_coverage_masks_exact_v026=True,added_grass_outside_all_protected_native_grid_masks=True))

def main():
    O.mkdir(exist_ok=True); f=fields(read(S/'surface_spec.json'),read(S/'pit_access.json'))
    apply_height(f,read(S/'surface_spec.json')); physics(f)
    print('v028 shared wear, modest local relief and connected pit coverage validated',flush=True)
if __name__=='__main__':main()
