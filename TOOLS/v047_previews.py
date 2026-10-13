"""Auditable track-wide A/B placements and static distant thinning preview."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from v047_common import *

def main():
    q=read(O/'v047_scenery_validation.json');route=dict(np.load(BASE/'route.npz'))
    fig,ax=plt.subplots(figsize=(10,10),facecolor='#f4f1eb');ax.set_facecolor('#e2e8d8')
    p=route['q'];ax.plot(p[:,0],p[:,1],c='#9b795c',linewidth=9,zorder=2,label='Unchanged riding circuit')
    for style,color in [('A','#447453'),('B','#184838')]:
        rows=[r for r in q['placements'] if r['retained'] and r['style']==style];a=np.array([r['anchor_xz_m'] for r in rows])
        ax.scatter(a[:,0],a[:,1],s=24 if style=='A' else 40,c=color,marker='^' if style=='A' else 'o',label=f'{style}: {len(rows)} trees',zorder=3)
    rows=[r for r in q['placements'] if not r['retained']];a=np.array([r['anchor_xz_m'] for r in rows]);ax.scatter(a[:,0],a[:,1],s=18,c='#abac9f',marker='x',label=f'{len(rows)} distant trees removed',zorder=1)
    ax.set_aspect('equal');ax.set_xlim(65,510);ax.set_ylim(60,530);ax.set_xlabel('Track X (m)');ax.set_ylabel('Track Z (m)')
    ax.set_title('Orlando MX v047 | 252 pine A + 45 woodland B',fontsize=17,pad=17)
    ax.legend(loc='lower left',framealpha=.94);ax.grid(alpha=.14)
    fig.text(.5,.035,'Placement diagram. All near-course and facility trees retained; distant density reduced.\nNot an in-game render. v046 dirt, physical track and non-tree scenery preserved.',ha='center',fontsize=10,color='#444b42')
    fig.subplots_adjust(bottom=.13,top=.91);fig.savefig(O/'v047_tree_placement_preview.png',dpi=140,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
