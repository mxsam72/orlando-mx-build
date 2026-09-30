"""Native material/visual masks for compacted pit roads; no urban curbs."""
from PIL import Image
from scipy.ndimage import gaussian_filter
from v012_common import *

def road_field(shape):
    cfg=read(S/'pit_facilities.json');h,w=shape;x,z=np.meshgrid(np.linspace(0,600,w),np.linspace(600,0,h));p=np.stack([x,z],axis=-1);a=np.zeros(shape)
    for road in cfg['roads']:
        pts=np.asarray(road['points'])
        for start,end in zip(pts[:-1],pts[1:]):
            delta=end-start;t=np.clip(((p-start)*delta).sum(-1)/(delta@delta),0,1);dist=np.linalg.norm(p-(start+t[...,None]*delta),axis=-1)
            a=np.maximum(a,1-ease((dist-road['width']/2)/1.2))
    return a

def main():
    a=road_field((2048,2048));mdir=O/'masks';W=R/'BUILD/v009_work'
    for name in ['pits','off','grass','visual_grass','sand']:
        src=mdir/(name+'.tga')
        if not src.exists():src=W/'03_MASKS'/(name+'.tga')
        original=np.array(Image.open(src).convert('RGBA').getchannel('A'),dtype=float)/255
        out=np.maximum(original,a) if name=='pits' else original*(1-a)
        im=Image.new('RGBA',(2048,2048),'white');im.putalpha(Image.fromarray(np.uint8(np.round(out*255))));im.save(mdir/(name+'.tga'))
    im=Image.new('RGBA',(2048,2048),'white');im.putalpha(Image.fromarray(np.uint8(np.round(a*255))));im.save(mdir/'v012_pit_roads.tga')
    # Deterministic, low-contrast granular surface. All existing dirt tiles remain intact.
    rng=np.random.default_rng(110927);n=rng.normal(0,1,(256,256));n=gaussian_filter(n,.45)*6+gaussian_filter(n,6)*12
    rgb=np.clip(np.array([184,179,163])+n[...,None],0,255).astype('uint8');Image.fromarray(rgb).save(O/'v012_pit_sand.tga')
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;gy,gx=np.gradient(H,SIZE/(N-1));grade=np.hypot(gx,gy);core=road_field((N,N))>.9
    qa=read(R/'DOCUMENTATION/v012_release_validation.json');qa['pit_roads']=dict(area_m2=float((a>.5).sum())*(600/2047)**2,maximum_grade=float(grade[core].max()),pale_compacted_surface=True,terrain_unchanged=True)
    assert qa['pit_roads']['maximum_grade']<.18,'Pit road crosses steep ground'
    qa['input_sha256']={str(p.relative_to(R)):sha(p) for p in [O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),O/'v012_pit_sand.tga',*sorted(mdir.glob('*.tga')),*sorted((O/'facility_textures').glob('*.tga'))]}
    save(R/'DOCUMENTATION/v012_release_validation.json',qa);print('Pit roads: source masks and pale granular surface prepared')
if __name__=='__main__':main()
