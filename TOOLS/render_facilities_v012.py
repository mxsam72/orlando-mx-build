"""Review the actual authored meshes and heightfield; not an in-game screenshot."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from facility_mesh_v012 import PALETTE
from pit_roads_v012 import road_field
from v012_common import *

def main():
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;meshes=read(O/'facility_meshes.json');cfg=read(S/'pit_facilities.json');q,w=route()
    dest=R/'DOCUMENTATION/v012_qa';dest.mkdir(exist_ok=True)
    light=np.array([-.35,.8,-.45]);light/=np.linalg.norm(light)
    views=[('facility_overview',(225,387,85,211),32,-65,None),('front_tabletop',(278,378,150,203),21,-63,None),('restroom_detail',(340,368,106,155),28,-50,['restroom','rv_02','toyhauler_01','oak_restroom']),('seating_detail',(299,342,156,173),26,65,['covered_stand','bleachers']),('pit_landmarks',(271,371,119,156),28,-65,['office','concession'])]
    for name,(x0,x1,z0,z1),el,az,include in views:
        fig=plt.figure(figsize=(13,8),facecolor='#e9eef0');ax=fig.add_subplot(111,projection='3d');ax.set_facecolor('#e9eef0')
        xx,zz=np.meshgrid(np.linspace(x0,x1,180),np.linspace(z0,z1,140));hh=ground(H,np.stack([xx,zz],axis=-1))
        pts=np.stack([xx,zz],axis=-1);colors=np.zeros((*hh.shape,4));colors[:]=[.40,.46,.29,1]
        from scipy.spatial import cKDTree
        dist,ix=cKDTree(q[:,:2]).query(pts.reshape(-1,2));track=(dist<w[ix]/2+5).reshape(hh.shape);colors[track]=[.56,.43,.30,1]
        for road in cfg['roads']:
            rp=np.array(road['points'])
            for a,b in zip(rp[:-1],rp[1:]):
                d=b-a;t=np.clip(((pts-a)*d).sum(-1)/(d@d),0,1);dd=np.linalg.norm(pts-(a+t[...,None]*d),axis=-1);colors[dd<road['width']/2]=[.72,.70,.64,1]
        # Ground and objects share one collection so depth sorting is per face,
        # rather than painting one enormous ground surface over whole objects.
        polygons=[];cs=[]
        for j in range(0,hh.shape[0]-2,2):
            for i in range(0,hh.shape[1]-2,2):
                polygons.append([[xx[j,i],zz[j,i],hh[j,i]],[xx[j,i+2],zz[j,i+2],hh[j,i+2]],[xx[j+2,i+2],zz[j+2,i+2],hh[j+2,i+2]],[xx[j+2,i],zz[j+2,i],hh[j+2,i]]]);cs.append(colors[j,i])
        for m in meshes:
            if include and m['asset'] not in include:continue
            v=np.asarray(m['vertices']);cx,cz=v[:,0].mean(),v[:,2].mean()
            if not (x0-5<cx<x1+5 and z0-5<cz<z1+5):continue
            base=np.array(PALETTE[m['material']])/255
            for face in m['faces']:
                p=v[face];n=np.cross(p[1]-p[0],p[2]-p[0]);n/=max(np.linalg.norm(n),1e-12);shade=.57+.43*max(0,n@light)
                polygons.append(p[:,[0,2,1]]);cs.append(np.r_[base*shade,1])
        ax.add_collection3d(Poly3DCollection(polygons,facecolors=cs,edgecolors='none',zsort='average'))
        ax.set(xlim=(x0,x1),ylim=(z0,z1),zlim=(2,15));ax.set_box_aspect((x1-x0,z1-z0,13),zoom=1.3);ax.view_init(el,az);ax.set_axis_off()
        ax.set_title('Orlando MX v012 · '+name.replace('_',' ')+'\nActual source geometry preview — placement estimates; game lighting differs',pad=0,fontsize=12)
        fig.subplots_adjust(left=0,right=1,bottom=0,top=.9);save_plot(fig,dest/(name+'.png'),dpi=135);plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,8),layout='constrained');ax.set_facecolor('#dbe0cf')
    ax.plot(q[:,0],q[:,1],color='#88674d',lw=12,label='Lap');front=np.array(read(S/'facilities.json')['fence_polyline_xz']);ax.plot(*front.T,color='#51483b',lw=3,label='Timber / mesh fence')
    for r in cfg['roads']:
        p=np.array(r['points']);ax.plot(*p.T,lw=r['width']*1.6,color='#b6b3a4',solid_capstyle='round')
    for a in cfg['assets']:
        x,z=a['xz'];ax.plot(x,z,'o',ms=6,c='#436646' if a['type']=='oak' else '#3f5868');ax.annotate(a['id'].replace('_',' '),(x,z),xytext=(3,5),textcoords='offset points',fontsize=7)
    ax.scatter([x for x in range(260,331,10) for z in [110,117,124]],[z for x in range(260,331,10) for z in [110,117,124]],marker='x',s=40,c='#97712f',label='Preserved pit spawns')
    ax.set(xlim=(224,390),ylim=(83,207),aspect='equal',xlabel='Native X (m)',ylabel='Native Z (m)',title='v012 facilities — authored layout, not surveyed coordinates');ax.legend(loc='upper left',fontsize=8);save_plot(fig,dest/'pit_layout.png',dpi=150);plt.close(fig)
    print('Actual facility meshes and pit layout rendered')
if __name__=='__main__':main()
