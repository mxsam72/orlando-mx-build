"""Validate the encoded heightfield, including surviving decks and double valleys."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from v011_common import *

def main():
    q,w=route();H=np.fromfile(O/'main_terrain.raw','<u2').reshape(N,N)/65535*SCALE
    profiles=read(O/'jump_profiles.json');dest=R/'DOCUMENTATION/v011_qa';dest.mkdir(exist_ok=True)
    fig,axes=plt.subplots(9,2,figsize=(14,24),layout='constrained');metrics=[]
    for p,ax in zip(profiles,axes.flat):
        ss=np.linspace(p['profile_s'][0],p['profile_s'][-1],600);s=ss+p['lip_s']
        xz=np.c_[np.interp(s,q[:,3],q[:,0]),np.interp(s,q[:,3],q[:,1])];actual=ground(H,xz)
        substrate=np.interp(ss,[ss[0],ss[-1]],[actual[0],actual[-1]])
        rel=actual-substrate;grade=np.gradient(actual,ss);marks=p['landmarks_m']
        m=dict(id=p['id'],kind=p['kind'],maximum_actual_grade=float(abs(grade).max()),height_above_endpoint_chord_m=float(rel.max()))
        if p['kind']=='tabletop':
            deck=(ss>marks['deck_start']+.8)&(ss<marks['deck_end']-.8)
            m.update(deck_length_m=p['deck_m'],actual_deck_height_spread_m=float(np.ptp(actual[deck])),actual_deck_max_grade=float(abs(grade[deck]).max()))
            assert m['actual_deck_max_grade']<.10,(p['id'],'deck lost to smoothing',m)
        if p['kind']=='double':
            low=(ss>marks['valley_start'])&(ss<marks['valley_end'])
            a=(ss>marks['gap_start']-.4)&(ss<marks['gap_start']+.4)
            b=(ss>marks['landing_crest']-.4)&(ss<marks['landing_crest']+.4)
            m['actual_valley_below_lower_crest_m']=float(min(actual[a].max(),actual[b].max())-actual[low].min())
            assert m['actual_valley_below_lower_crest_m']>1.0,(p['id'],'double gap filled',m)
        ax.plot(ss,np.interp(ss,p['profile_s'],p['profile_h']),label='Authored earthwork',color='#ac6b25',lw=1.6)
        ax.plot(ss,rel,label='Encoded terrain, endpoint ground removed',color='#164f70',lw=1.5)
        ax.set_title(p['id']+' · '+p['kind'].replace('_',' '));ax.set_xlabel('Metres relative to lip');ax.set_ylabel('Rise (m)');ax.grid(alpha=.2)
        ax.legend(fontsize=6);metrics.append(m)
    fig.suptitle('v011 jump inventory — source estimates, not surveyed dimensions',fontsize=16)
    fig.savefig(dest/'jump_profiles.png',dpi=120);plt.close(fig)
    qa=read(R/'DOCUMENTATION/v011_geometry_validation.json')
    qa.update(actual_obstacle_profiles=metrics,geometry_checks_pass=bool(qa['finite'] and qa['raw_png_identical'] and qa['maximum_racing_grade']<.84 and qa['outer_terrain_max_delta_m']<.001),native_compilation=False,in_game_riding=False)
    save(R/'DOCUMENTATION/v011_geometry_validation.json',qa)
    assert qa['geometry_checks_pass'];print('Encoded decks, double valleys and terrain limits passed',len(metrics))
    lines=['# v011 jump inventory','','All distances are authoring estimates. R01 is strongly supported by the side views. R07/R16 double valleys remain provisional because the GoPro partly obscures them.','', '| ID | Type | Height m | Face m | Deck / gap m | Landing m | Riding role |','|---|---|---:|---:|---:|---:|---|']
    for p in profiles:lines.append(f"| {p['id']} | {p['kind']} | {p['crest_height_m']:.2f} | {p['face_m']:.1f} | {p.get('deck_m',p.get('gap_m',0)):.1f} | {p['landing_m']:.1f} | {p['role']} |")
    lines+=['','## Evidence']+[f"- {p['id']}: {p['evidence']}" for p in profiles]
    (R/'DOCUMENTATION/v011_jump_inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()
