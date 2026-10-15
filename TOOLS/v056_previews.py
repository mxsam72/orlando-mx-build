"""Actual source reviews of every corner and local landing; not game captures."""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from v056_inputs import R, PREV, O, sha, save
from v056_geometry import cross_points, corner_regions
from v056_surface import baseline, source as current_source
from v054_geometry import read
from v054_previews import Terrain
import v049_previews as render

OUT=R/'BUILD/v056_review'
CURRENT='v054'


def source(name,version):
    return current_source(name) if CURRENT=='v056' else baseline(name)


def shade(colors, normals, terrain, box):
    n=len(colors)
    x,z=np.meshgrid(np.linspace(box[0],box[2],n),np.linspace(box[3],box[1],n))
    hx,hz=terrain.slope(x,z)
    base=np.stack([-hx,-hz,np.ones_like(hx)],-1)
    base/=np.linalg.norm(base,axis=-1,keepdims=True)
    light=np.array([2,-7,10.]);light/=np.linalg.norm(light)
    intensity=.45+.65*np.maximum(0,base@light)
    return np.uint8(np.rint(np.clip(colors.astype(float)/255*intensity[:,:,None]**.45,0,1)*255))


def main():
    global CURRENT
    OUT.mkdir(parents=True,exist_ok=True)
    route=dict(np.load(O/'route.npz'));q=route['q']
    before,after=Terrain(PREV/'terrain.raw'),Terrain(O/'terrain.raw')
    render.OUT,render.source=OUT,source
    rows=[]
    # One matched light/camera-equivalent overhead atlas for all fourteen corners.
    box=(0.,0.,600.,600.)
    atlases={}
    for version,sample in [('v054',before),('v056',after)]:
        CURRENT=version;render.O=O if version=='v056' else PREV;render.BOX=box
        color,normal=render.composite('v049',n=2400)
        atlases[version]=shade(color,normal,sample,box)
    sheet=Image.new('RGB',(1400,7*230),(22,25,29))
    draw=ImageDraw.Draw(sheet)
    for i,(name,lo,hi) in enumerate(corner_regions(q,route['v054_old_station'])):
        pts=cross_points(q,np.linspace(lo,hi,150),0)
        mid=(pts.min(0)+pts.max(0))/2
        extent=max(np.ptp(pts,axis=0).max()+32,45)
        xx,zz=np.meshgrid(np.linspace(mid[0]-extent/2,mid[0]+extent/2,350),
                          np.linspace(mid[1]+extent/2,mid[1]-extent/2,205))
        for j,version in enumerate(['v054','v056']):
            a=atlases[version]
            tile=np.stack([map_coordinates(a[:,:,k],[(600-zz)/600*2399,xx/600*2399],order=1,mode='nearest') for k in range(3)],-1)
            col=(i%2)*700+j*350;row=(i//2)*230
            sheet.paste(Image.fromarray(tile),(col,row+25))
            draw.text((col+8,row+4),name+' '+version+' — source only',font=render.font(15),fill='white')
    sheet.save(OUT/'all_14_corners_v054_v056.jpg',quality=96)
    for version,a in atlases.items():
        Image.fromarray(a).save(OUT/(version+'_full_track_source.jpg'),quality=94)
    del atlases
    shots=[('landing_and_T03',(228.,241.,275.,308.),254.,0.,2.,285.,0.,.7),
           ('track_edge',(281.,159.,366.,213.),8.,0.,1.8,38.,0.,.5)]
    for label,box,es,el,eh,ts,tl,th in shots:
        eye2=cross_points(q,np.array([es]),el)[0];target2=cross_points(q,np.array([ts]),tl)[0]
        eye=[*eye2,float(before.ground(eye2[None,0],eye2[None,1])[0])+eh]
        target=[*target2,float(after.ground(target2[None,0],target2[None,1])[0])+th]
        frames=[]
        for version,sample in [('v054',before),('v056',after)]:
            CURRENT=version;render.O=O if version=='v056' else PREV;render.BOX=box
            colors,normals=render.composite('v049',n=1200)
            path=render.render(version,label,colors,normals,sample,eye,target,width=1100,height=700)
            frames.append(Image.open(path).copy())
            rows.append(dict(file=path.name,sha256=sha(path),source_only=True))
        pair=Image.new('RGB',(2200,700));pair.paste(frames[0],(0,0));pair.paste(frames[1],(1100,0))
        pair.save(OUT/('comparison_'+label+'.jpg'),quality=95)
    d=dict(np.load(O/'landing_sections.npz'))
    fig,axes=plt.subplots(1,2,figsize=(13,5),sharey=True)
    for ax,key,title in zip(axes,['before','after'],['v054 crown','v056 local crown correction; corner retained']):
        for lat in [-5,0,2,4,6]:
            j=np.argmin(abs(d['lat']-lat));ax.plot(d['s'],d[key][j],label=f'{lat:+g} m lateral')
        ax.axvline(272.518,c='black',ls='--',lw=1,label='T03 starts')
        ax.set_title(title);ax.set_xlabel('Route station (m)');ax.grid(alpha=.2);ax.legend()
    axes[0].set_ylabel('Emitted RAW elevation (m)');fig.tight_layout();fig.savefig(OUT/'landing_sections.png',dpi=150);plt.close(fig)
    save(OUT/'manifest.json',dict(version='v056',source_only=True,in_game_captures=False,
        all_14_corners_reviewed=True,matched_cameras_and_light=True,scenery_omitted=True,renders=rows,
        all_14_corner_grids_exact_v054=read(O/'terrain_validation.json')['all_14_corner_grids_exact'],
        source_terrain_sha256=sha(O/'terrain.raw'),surface_validation_sha256=sha(O/'surface_validation.json')))
    print('V056_ALL_14_CORNERS_SOURCE_REVIEW_READY',flush=True)


if __name__=='__main__':
    main()
