#!/usr/bin/env python3
"""Inspect the delivered RAW, compare all jumps, and produce source QA figures."""
from pathlib import Path
import json,math
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import map_coordinates
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

ROOT=Path(__file__).resolve().parents[1]
def main():
    info=json.loads((ROOT/'V007_SOURCE/geometry.json').read_text())
    data=np.load(ROOT/'V007_SOURCE/route.npz');q=data['q'];w=data['width']
    old=json.loads((ROOT/'V007_SOURCE/v006_jump_profiles.json').read_text())
    new=json.loads((ROOT/'02_HEIGHTMAP/jump_profiles.json').read_text())
    baseline=np.fromfile(ROOT/'BUILD/v006_terrain.raw',dtype='<u2').reshape(2049,2049)/65535*18
    raw=np.fromfile(ROOT/'02_HEIGHTMAP/terrain.raw',dtype='<u2').reshape(2049,2049)
    height=raw/65535*18
    assert np.array_equal(raw,np.array(Image.open(ROOT/'02_HEIGHTMAP/terrain_16bit.png')))
    def sample(H,s):
        s=np.asarray(s)%q[-1,3]
        x=np.interp(s,q[:,3],q[:,0]);z=np.interp(s,q[:,3],q[:,1])
        return map_coordinates(H,[(600-z)/600*2048,x/600*2048],order=1)
    fig,axes=plt.subplots(6,3,figsize=(14,17),layout='constrained')
    rows=[]
    for a,b,ax in zip(old,new,axes.flat):
        start=min(a['lip_s']+a['profile_s'][0],b['lip_s']+b['profile_s'][0])-3
        end=max(a['lip_s']+a['profile_s'][-1],b['lip_s']+b['profile_s'][-1])+3
        s=np.linspace(start,end,1000);before=sample(baseline,s);after=sample(height,s)
        ax.plot(s-a['lip_s'],before,color='#a5a5a5',lw=1.7,label='v006')
        ax.plot(s-a['lip_s'],after,color='#bd5823',lw=2,label='v007')
        ax.set_title(b['id']+'  '+b['kind'],loc='left',weight='bold',fontsize=11)
        ax.grid(alpha=.2);ax.set_xlabel('Distance from v006 lip (m)',fontsize=8);ax.set_ylabel('Elevation (m)',fontsize=8)
        ax.tick_params(labelsize=8);ax.set_ylim(min(before.min(),after.min())-.2,max(before.max(),after.max())+.3)
        ax.spines[['top','right']].set_visible(False)
        f=CubicHermiteSpline(b['profile_s'],b['profile_h'],b['profile_derivative'])
        x=np.linspace(b['profile_s'][0],b['profile_s'][-1],10000)
        assert f(x).min()>-.0001 and max(abs(f(x,1)))<.60
        assert max(abs(f([x[0],x[-1]],1)))<1e-8
        row=dict(id=b['id'],kind=b['kind'],lip_s_m=b['lip_s'],lip_shift_m=b['lip_s']-a['lip_s'],
                 crest_height_above_base_m=b['crest_height_m'],maximum_profile_grade=float(max(abs(f(x,1)))))
        if b['kind']=='tabletop':
            oldf=CubicHermiteSpline(a['profile_s'],a['profile_h'],a['profile_derivative'])
            row['old_lip_max_abs_curvature']=float(max(abs(oldf(np.linspace(0,1.2,1000),2))))
            row['new_lip_max_abs_curvature']=float(max(abs(f(np.linspace(0,b['lip_rollover_m'],1000),2))))
            row['lip_curvature_reduction_percent']=100*(1-row['new_lip_max_abs_curvature']/row['old_lip_max_abs_curvature'])
            landing_end=b['lip_s']+b['profile_s'][-1]-2
            next_turn=next(t for t in info['turns'] if t['arc_start']>b['lip_s'])
            row['landing_end_s_m']=landing_end
            row['runout_to_next_turn_m']=next_turn['arc_start']-landing_end
            row['next_turn']=next_turn['id']
            assert row['runout_to_next_turn_m']>2, b['id']+' landing overlaps corner'
        rows.append(row)
    axes[0,0].legend(frameon=False,fontsize=9)
    fig.suptitle('Orlando MX v007 — jump surface comparison\nSampled from the actual terrain RAW; geometry estimates, not an in-game riding test',fontsize=15,weight='bold')
    fig.savefig(ROOT/'DOCUMENTATION/OrlandoMX_v007_Jump_Comparison.png',dpi=150);plt.close(fig)
    reductions=[x['lip_curvature_reduction_percent'] for x in rows if x['kind']=='tabletop']
    qa=dict(version='v007',jump_count=len(rows),
            takeoff_grade_range_degrees=[min(j['takeoff_angle_deg'] for j in new if j['kind']=='tabletop'),max(j['takeoff_angle_deg'] for j in new if j['kind']=='tabletop')],
            mean_lip_curvature_reduction_percent=float(np.mean(reductions)),
            minimum_tabletop_runout_to_turn_m=min(x['runout_to_next_turn_m'] for x in rows if x['kind']=='tabletop'),
            raw_source_checked=True,in_game_ridden=False,jumps=rows)
    (ROOT/'DOCUMENTATION/v007_jump_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
    # A source-terrain review rendered in route coordinates around J01.
    j=next(j for j in new if j['id']=='J01');s=np.linspace(j['lip_s']-15,j['lip_s']+30,240);lat=np.linspace(-11,11,100)
    theta=np.interp(s,q[:,3],q[:,2]);x=np.interp(s,q[:,3],q[:,0])[None,:]-lat[:,None]*np.sin(theta)
    z=np.interp(s,q[:,3],q[:,1])[None,:]+lat[:,None]*np.cos(theta)
    hh=map_coordinates(height,[(600-z)/600*2048,x/600*2048],order=1)
    ss,ll=np.meshgrid(s-j['lip_s'],lat)
    fig=plt.figure(figsize=(10.24,10.24));ax=fig.add_subplot(111,projection='3d')
    rgb=LightSource(315,45).shade(hh,cmap=plt.cm.copper,vert_exag=1,dx=45/239,dy=26/99)
    ax.plot_surface(ss,ll,hh,facecolors=rgb,linewidth=0,antialiased=True,shade=False,rcount=100,ccount=240)
    ax.set_box_aspect((45,26,12));ax.view_init(23,-66);ax.set_axis_off()
    fig.text(.07,.94,'ORLANDO MX 2026 v007',fontsize=25,weight='bold')
    fig.text(.07,.90,'J01 terrain geometry preview',fontsize=18)
    fig.subplots_adjust(left=0,right=1,bottom=0,top=.88)
    path=ROOT/'DOCUMENTATION/OrlandoMX_v007_Jump_Preview.png';fig.savefig(path,dpi=100);plt.close(fig)
    release=ROOT/'12_RELEASE/orlandomx_2026_v007';release.mkdir(exist_ok=True)
    Image.open(path).convert('RGB').resize((1024,1024)).save(release/'orlandomx_2026_v007.tga')
    print(json.dumps({k:v for k,v in qa.items() if k!='jumps'},indent=2))

if __name__=='__main__':main()
