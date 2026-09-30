"""Validate topology/relational placement and plot the actual authored layout."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree,ConvexHull
from v012_common import *
from facility_mesh_v012 import PALETTE

def main():
    q,w=route();cfg=read(O/'facility_layout.json');sa=np.load(O/'route.npz')['start'];pit=read(S/'pit_facilities.json');assets={a['id']:a for a in pit['assets']}
    sw=np.interp(sa[:,3],*np.array(cfg['start_width_knots']).T);turns=read(R/'V009_SOURCE/baseline_geometry.json')['turns'];t6=next(t for t in turns if t['id']=='T06')
    # T05 approach/exit and T06 entry are the intended convergence area. Every
    # other lane must remain separate, including R08 to the north of this loop.
    unrelated=(q[:,3]<420)|(q[:,3]>535);dd,ii=cKDTree(q[unrelated,:2]).query(sa[:,:2]);clear=dd-w[unrelated][ii]/2-sw/2
    # Adjacent native samples do not count as a self-crossing.
    tree=cKDTree(sa[:,:2]);cross=[]
    for i,j in tree.query_pairs(.25):
        if abs(sa[i,3]-sa[j,3])>2:cross.append([i,j])
    b=np.array(assets['restroom']['xz']);a=np.array(assets['rv_02']['xz']);c=np.array(assets['toyhauler_01']['xz']);u=float((b-a)@(c-a)/((c-a)@(c-a)))
    between_distance=float(np.linalg.norm(b-(a+u*(c-a))))
    qa=dict(start_length_m=float(sa[-1,3]),gate_stalls=cfg['grid_stalls'],grid_outer_stall_span_m=23*cfg['stall_spacing_m'],gate_apron_width_m=cfg['start_width_knots'][0][1],minimum_start_width_m=float(sw.min()),minimum_other_lane_edge_clearance_m=float(clear.min()),self_crossings=cross,merge_station_m=cfg['merge_station_m'],right_turn='T06',right_turn_angle_deg=t6['angle'],distance_before_right_turn_m=t6['arc_start']-cfg['merge_station_m'],bathroom_between_camper_fraction=u,bathroom_distance_from_camper_axis_m=between_distance,office_left_of_frontage_truck=assets['office']['xz'][0]<assets['pickup_03']['xz'][0],office_view_direction='+Z from pit road toward spectator fence',outside_shoulder_note='Last ~35 m converges alongside the T05 exit. Shoulder overlap here is intentional; the start centerline ends at s493 before T06. It never crosses the T05 apex.',runtime_start_reset_and_timing='Pending in-game test')
    qa['layout_checks_pass']=bool(clear.min()>.5 and not cross and 0<t6['arc_start']-cfg['merge_station_m']<8 and t6['angle']<0 and 0<u<1 and between_distance<5 and qa['office_left_of_frontage_truck'])
    save(R/'DOCUMENTATION/v012_layout_validation.json',qa);assert qa['layout_checks_pass'],qa
    start=read(S/'start_layout.json');start.update(start_lane_width_m=cfg['start_width_knots'],start_length_m=float(sa[-1,3]),right_corner_start_m=t6['arc_start'],merge_before_corner_m=t6['arc_start']-cfg['merge_station_m']);save(O/'start_layout_resolved.json',start)
    folder=R/'DOCUMENTATION/v012_qa';folder.mkdir(exist_ok=True);meshes=read(O/'facility_meshes.json')
    fig,axes=plt.subplots(1,2,figsize=(16,10),layout='constrained');ax=axes[0];ax.set_facecolor('#dde2ce')
    for road in pit['roads']:
        pp=np.array(road['points']);ax.plot(*pp.T,lw=road['width']*2,color='#c3beb0',solid_capstyle='round')
    for m in meshes:
        vv=np.array(m['vertices'])[:,[0,2]];v=np.unique(vv,axis=0)
        if len(v)<3:continue
        try:h=ConvexHull(v)
        except Exception:continue
        ax.fill(v[h.vertices,0],v[h.vertices,1],color=np.array(PALETTE[m['material']])/255,alpha=.65 if m['material'].startswith('leaf') else 1)
    fence=np.array(cfg['fence_polyline_xz']);ax.plot(*fence.T,lw=2,color='#634c2e')
    for id,label,offset in [('office','Office: left of frontage truck',(-63,28)),('pickup_03','Red frontage truck',(6,-27)),('restroom','Bathroom between campers',(-112,-35)),('rv_02','Camper / RV',(10,-20)),('toyhauler_01','Toy hauler / camper',(14,15))]:
        a=assets[id];ax.annotate(label,a['xz'],xytext=offset,textcoords='offset points',fontsize=9,arrowprops=dict(arrowstyle='->',color='#243d49'),bbox=dict(boxstyle='round,pad=.25',fc='white',alpha=.9,ec='none'))
    ax.plot([350,356],[110,151],ls=':',c='#57766a',lw=1.4);ax.annotate('View toward spectator fence (+Z)',(240,158),xytext=(240,115),arrowprops=dict(arrowstyle='->'),fontsize=8,rotation=90,va='bottom')
    ax.set(xlim=(230,382),ylim=(88,180),aspect='equal',title='Pit corrections · actual source mesh footprints',xlabel='Native X (m)',ylabel='Native Z (m)')
    ax=axes[1];ax.set_facecolor('#e7e7d8');normal=np.c_[-np.sin(q[:,2]),np.cos(q[:,2])]
    for side in [-1,1]:
        edge=q[:,:2]+side*normal*w[:,None]/2;ax.plot(*edge.T,lw=.8,c='#8b694b')
    ax.plot(q[:,0],q[:,1],lw=2,c='#896746',label='Normal circuit')
    n=np.c_[-np.sin(sa[:,2]),np.cos(sa[:,2])];left=sa[:,:2]+n*sw[:,None]/2;right=sa[:,:2]-n*sw[:,None]/2;ax.fill(np.r_[left[:,0],right[::-1,0]],np.r_[left[:,1],right[::-1,1]],color='#d7b340',alpha=.6,label='Start lane actual width');ax.plot(sa[:,0],sa[:,1],color='#8d720f',lw=1.5)
    gg=np.array([[g['x'],g['z']] for g in cfg['grid']]);ax.scatter(*gg.T,c='#433520',marker='|',s=45);ax.annotate('24 gates · 38 m apron',cfg['grid_center_xz'],xytext=(-65,-22),textcoords='offset points',fontsize=9)
    for t in turns:
        if t['id'] in ['T05','T06','T08']:
            p=route_point(q,t['mid']);ax.text(p[0],p[1],t['id']+(' RIGHT' if t['id']=='T06' else ''),fontsize=9,bbox=dict(fc='white',ec='none',alpha=.85))
    end=sa[-1,:2];ax.scatter(*end,c='#cd512a',s=45);ax.annotate(f"Merge s493\n{qa['distance_before_right_turn_m']:.1f} m before T06",end,xytext=(0,-53),textcoords='offset points',arrowprops=dict(arrowstyle='->'),fontsize=9,bbox=dict(fc='white',ec='none',alpha=.9))
    for station in [45,85,120,145]:
        p=route_point(sa,station);ax.arrow(p[0],p[1],3*np.cos(p[2]),3*np.sin(p[2]),head_width=2,width=.25,color='#725c0b')
    ax.annotate('7 m corridor\nR08 remains separate',route_point(sa,134)[:2],xytext=(35,35),textcoords='offset points',arrowprops=dict(arrowstyle='->'),fontsize=8)
    ax.set(xlim=(304,441),ylim=(171,313),aspect='equal',title='Gate → outside T05 loop → before T06',xlabel='Native X (m)',ylabel='Native Z (m)');ax.legend(loc='lower left',fontsize=8)
    fig.suptitle('v012 facility and start corrections — measured from the authored source\nPositions are construction estimates; first-lap timing, 24 riders and resets require an in-game check',fontsize=14);fig.savefig(folder/'facility_start_corrections.png',dpi=150);plt.close(fig)
    print('Start topology and facility relations passed',qa)
if __name__=='__main__':main()
