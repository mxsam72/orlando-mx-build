"""Check real encoded obstacle profiles, counts, gaps, decks and line choice."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.interpolate import CubicHermiteSpline
from refine_jumps import supports
from jump_v021 import envelope
from v021_common import *

def line(q, s, offset=0):
    ss=s%q[-1,3];theta=np.interp(ss,q[:,3],q[:,2])
    return np.c_[np.interp(ss,q[:,3],q[:,0])-offset*np.sin(theta),np.interp(ss,q[:,3],q[:,1])+offset*np.cos(theta)]

def main():
    q,w=route();H=np.fromfile(O/'main_terrain.raw','<u2').reshape(N,N)/65535*SCALE
    profiles=read(O/'jump_profiles.json');dest=R/'DOCUMENTATION/v021_qa';dest.mkdir(exist_ok=True)
    assert len(profiles)==18 and [p['id'] for p in profiles]==[f'R{i:02}' for i in range(1,19)]
    fig,axes=plt.subplots(9,2,figsize=(16,27),layout='constrained');metrics=[]
    inventory=['# v021 obstacle inventory','','User-authoritative types and approximate lengths; heights, slopes and absolute positions are authoring estimates. Lengths exclude zero-height sampling padding. Station zero is the unchanged native route origin. R01 wraps across station zero; all v021 station ranges below come from the current authored source.','', '| ID | Type | Start–end station m | Overall m | Height m | Geometry / placement |','|---|---|---|---:|---:|---|']
    for p,ax in zip(profiles,axes.flat):
        xs=np.linspace(p['profile_s'][0],p['profile_s'][-1],1200);s=xs+p['lip_s'];x=s-p['station_start_m'];offset=p.get('lateral_offset_m',0)
        actual=ground(H,line(q,s,offset));substrate=np.interp(xs,[xs[0],xs[-1]],[actual[0],actual[-1]]);rel=actual-substrate;grade=np.gradient(actual,xs)
        authored=CubicHermiteSpline(p['profile_s'],p['profile_h'],p['profile_derivative'])(xs);marks=p['landmarks_m'];kind=p['kind']
        m=dict(id=p['id'],target_type=p['target_type'],station_start_m=p['station_start_m'],station_end_m=p['station_end_m'],overall_length_m=p['authored_total_length_m'],maximum_actual_grade=float(abs(grade).max()),height_above_endpoint_chord_m=float(rel.max()))
        if kind in ['tabletop','table_single']:
            deck=(xs>marks['deck_start']+.8)&(xs<marks['deck_end']-.8)
            m.update(deck_length_m=p['deck_m'],actual_deck_height_spread_m=float(np.ptp(actual[deck])),actual_deck_max_grade=float(abs(grade[deck]).max()))
            assert m['actual_deck_max_grade']<.10,(p['id'],'deck lost to smoothing',m)
            ax.axvspan(marks['deck_start']+p['face_m'],marks['deck_end']+p['face_m'],alpha=.15,color='#e8b657',label='Deck')
        if kind in ['double','triple','table_single']:
            dips=[]
            for i,v in enumerate(p['valleys'],1):
                lo=(xs>v['start']-.2)&(xs<v['end']+.2);a=marks[f'gap_{i}_start'];b=marks[f'gap_{i}_end']
                first=(xs>a-.5)&(xs<a+.5);last=(xs>b-.5)&(xs<b+.5)
                depth=float(min(actual[first].max(),actual[last].max())-actual[lo].min());dips.append(depth)
                minimum=.20 if p['crest_height_m']<1 else 1.0
                assert depth>minimum,(p['id'],'gap filled',depth,minimum)
                ax.axvspan(a+p['face_m'],b+p['face_m'],alpha=.08,color='#2f658a');ax.text((a+b)/2+p['face_m'],max(rel.max(),p['crest_height_m'])*.92,f'gap {i}',ha='center',fontsize=7)
            m['encoded_valley_depths_m']=dips;m['distinct_mound_count']=len(dips)+1
        if kind=='roller_sequence':
            peaks,_=find_peaks(rel,prominence=.18,distance=int(3.2/(xs[1]-xs[0])))
            crests=s[peaks];m.update(encoded_roller_count=len(peaks),encoded_crest_stations_m=crests.tolist(),encoded_crest_spacing_m=np.diff(crests).tolist())
            assert len(peaks)==p['roller_count'],(p['id'],'roller count',crests)
            expected=np.asarray(p.get('crest_spacings_m',[p['spacing_m']]*(len(crests)-1)),dtype=float)
            assert len(expected)==len(crests)-1
            assert np.max(abs(np.diff(crests)-expected))<max(.65,float(expected.max())*.10),(p['id'],'roller spacing',expected,crests)
            ax.scatter(x[peaks],rel[peaks],c='#cc6336',s=18,zorder=4)
            for i,k in enumerate(peaks,1):ax.annotate(str(i),(x[k],rel[k]),xytext=(0,5),textcoords='offset points',ha='center',fontsize=7)
        if kind=='ant_hill':
            peaks,_=find_peaks(rel,prominence=.8);m['encoded_major_crest_count']=len(peaks);m['encoded_crest_station_m']=float(s[peaks[0]]) if len(peaks) else None
            expected_crest=float(p['lip_s'])
            assert len(peaks)==1 and abs(s[peaks[0]]-expected_crest)<2.0,(p['id'],'ant-hill placement',expected_crest,m)
        if kind=='none':
            assert max(p['profile_h'])==0;m['authored_jump_height_m']=0
        if kind=='inside_roller':
            main=ground(H,line(q,s));main-=np.interp(xs,[xs[0],xs[-1]],[main[0],main[-1]])
            support=supports([p],q,w);main_jump=envelope(line(q,s),support);inside_jump=envelope(line(q,s,offset),support)
            m.update(main_line_authored_jump_max_m=float(main_jump.max()),inside_line_authored_jump_max_m=float(inside_jump.max()),inside_offset_m=offset)
            assert main_jump.max()<1e-8 and inside_jump.max()>.48
            assert rel.max()>.22,(p['id'],'inside roller erased',rel.max())
            ax.plot(x,main,label='Encoded main line (no R18)',color='#648456',ls='--')
        ax.plot(x,authored,label='Authored earthwork',color='#ac6b25',lw=1.5);ax.plot(x,rel,label='Encoded terrain, endpoint ground removed',color='#164f70',lw=1.4)
        if kind not in ['none','roller_sequence']:
            ax.axvline(0,color='#aaa',lw=.5);ax.axvline(p['face_m'],color='#aaa',lw=.5);ax.text(p['face_m'],ax.get_ylim()[0],' crest' if kind in ['single','ant_hill','inside_roller'] else ' lip',fontsize=7,va='bottom')
        if 'landing_break' in marks:ax.axvline(marks['landing_break']+p['face_m'],color='#aaa',ls=':',lw=.7)
        ax.set_title(f"{p['id']} · {kind.replace('_',' ')} · s{p['station_start_m']:.1f}–{p['station_end_m']:.1f} · {p['authored_total_length_m']:.1f} m",fontsize=10)
        ax.set_xlabel('Metres from toe / section start (face → lip → deck / gaps → landing)',fontsize=8);ax.set_ylabel('Rise (m)',fontsize=8);ax.grid(alpha=.2);ax.legend(fontsize=6,loc='upper right')
        metrics.append(m);inventory.append(f"| {p['id']} | {p['target_type']} | {p['station_start_m']:.1f}–{p['station_end_m']:.1f} | {p['authored_total_length_m']:.1f} | {p['crest_height_m']:.2f} | {p['notes']} |")
    fig.suptitle('v021 — actual encoded terrain and independent obstacle construction\nMetric authoring estimates; riding and timing still require an in-game test',fontsize=15);save_plot(fig,dest/'jump_profiles.png',dpi=130);plt.close(fig)
    qa=read(R/'DOCUMENTATION/v021_geometry_validation.json');qa.update(actual_obstacle_profiles=metrics,geometry_checks_pass=bool(qa['finite'] and qa['raw_png_identical'] and qa['maximum_racing_grade']<.84 and qa['outer_terrain_max_delta_m']<.001),native_compilation=False,in_game_riding=False)
    save(R/'DOCUMENTATION/v021_geometry_validation.json',qa);assert qa['geometry_checks_pass']
    inventory+=['','R07 v021: compact 29 m ant-hill; shorter and modestly steeper than v017 with crest retained at s552.','R10 v021: 74 m tabletop beginning at s739.2; higher crest, shorter/steeper face, and expanded deck.','R11 v021: same 20 m low-lip double with another 5% increase in takeoff and landing crest heights.','All other R01-R18 geometry remains as v017.','No-jump areas retain normal corner banking and ground elevation.']
    (R/'DOCUMENTATION/v021_jump_inventory.md').write_text('\n'.join(inventory)+'\n',encoding='utf-8');print('Encoded profiles passed:',len(metrics))
if __name__=='__main__':main()
