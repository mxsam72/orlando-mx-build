"""Three source-material studies on the same v056 terrain; no native build.

All candidate differences are confined by the same 210m world-space mask.
Unmodified v056 material data is used outside that mask. v057's approved
scenery is a separately preserved input; it is omitted from all dirt views.
"""
import json
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from v057_inputs import R, PREV, sha, save
from v056_surface import source
from v057_surface import Circuit as CoordinateCircuit
from v048_surface import smooth, normal_map
from v054_previews import Terrain

O=R/'V058_OUTPUT'; M=O/'materials'; OUT=R/'BUILD/v058_review'
S=R/'V058_SOURCE'; CACHE=R/'BUILD/v058_cache'
LO,HI,FEATHER=0.,210.,7.
METHODS={
 'v056':dict(title='v056 reference',summary='Original photographs and original high-opacity colour/normal atlas.'),
 'A':dict(title='A - Original scan, 25% overlay',summary='Only the existing overlay mask is reduced. Original 4K photo colours, photo normals, and v056 groove atlas remain unchanged.',cap=63/255),
 'B':dict(title='B - Photo colour + v056 grooves',summary='Replace coarse overlay colour with the original 2m scanned soil. Keep the original v056 macro normal and overlay opacity.',tile_m=2.),
 'C':dict(title='C - Loamy scan + broken cultivation',summary='3m clod scale, restrained normal-derived cavity shading, original scanned fine normals, and new broken lengthwise furrows. Matte surface; no diagonal tread stamps.',tile_m=3.,cap=.55),
}


class Section(CoordinateCircuit):
    def __init__(self):
        super().__init__()
        self.terrain=Terrain(PREV/'terrain.raw')
        self.section_points=self.p[(self.q[:,3]>=LO)&(self.q[:,3]<=HI)]

    def section(self,x,z):
        s,l=self.coords(x,z)
        return smooth((s-LO)/FEATHER)*smooth((HI-s)/FEATHER)*self.scope(x,z)

    def relief(self,x,z):
        s,l=self.coords(x,z); a=np.interp(s,self.arc_station,self.arc_distance)
        hx,hz=self.slope(x,z);flat=1-smooth((np.hypot(hx,hz)-.07)/.24)
        n0=self.noise(a,l,.20,0);n1=self.noise(a*.7,l,.38,1);n2=self.noise(a,l,.85,2)
        clod=np.maximum(0,.65*n0+.35*n1-.42)**1.7
        relief=(clod-.07)*(.025+.016*flat)+(n2-.5)*.004
        # Cultivator tines follow the local route. They fade in and out along
        # station, rather than leaving continuous paired vehicle tread bands.
        for i,c in enumerate(np.arange(-11.,11.,.46)):
            center=c+.022*np.sin(a*.12+i*2.1)+.012*np.sin(a*.39+i)
            w=.105+.025*np.sin(i*1.71)**2
            activity=.23+.77*smooth((self.noise(a+i*11,l,2.7,3)-.28)/.47)
            groove=np.exp(-((l-center)/w)**2)
            shoulder=np.exp(-((l-center-w*1.6)/(w*1.1))**2)
            relief+=(-groove+shoulder*.35)*(.033+.012*flat)*activity
        return relief


def author_c(section):
    M.mkdir(parents=True,exist_ok=True)
    # Cavity is a direction-independent local concavity estimate derived from
    # the actual scanned normal, not painted sunlight or new fake geometry.
    im=np.asarray(Image.open(source('v045_loose.tga')).convert('RGB'),np.float32)
    n=np.asarray(Image.open(source('v045_loose_n.tga')),np.float32)[:,:,:3]/127.5-1
    gx=-n[:,:,0]/np.maximum(n[:,:,2],.25);gy=n[:,:,1]/np.maximum(n[:,:,2],.25)
    gx=gaussian_filter(gx,3.,mode='wrap');gy=gaussian_filter(gy,3.,mode='wrap')
    curvature=(np.roll(gx,-1,1)-np.roll(gx,1,1)+np.roll(gy,-1,0)-np.roll(gy,1,0))*.5
    cavity=np.clip(gaussian_filter(curvature,2.,mode='wrap')/.12,0,1)
    factor=1-cavity*.18
    out=im*factor[:,:,None];out+=im.mean((0,1))-out.mean((0,1))
    out=np.uint8(np.rint(np.clip(out,8,235)));Image.fromarray(out).save(M/'v058_c_loose.tga')
    del n,gx,gy,curvature,cavity,im,out
    # Patch only the local atlas rectangle, retaining original texels elsewhere.
    src=source('v044_route_detail_n.tga');a=np.array(Image.open(src));n=a.shape[0];dx=600/n
    pmin=section.section_points.min(0)-18;pmax=section.section_points.max(0)+18
    x0=max(1,int(pmin[0]/dx)-2);x1=min(n-1,int(pmax[0]/dx)+2)
    y0=max(1,int((600-pmax[1])/dx)-2);y1=min(n-1,int((600-pmin[1])/dx)+2)
    changed=0
    for row in range(y0,y1,64):
        end=min(row+64,y1);x,z=np.meshgrid((np.arange(x0,x1)+.5)*dx,600-(np.arange(row-1,end+1)+.5)*dx)
        weight=section.section(x,z)[1:-1]
        target=normal_map(section,x,z,section.relief(x,z),dx)[1:-1]
        old=a[row:end,x0:x1,:3].copy();v=(old/127.5-1)*(1-weight[:,:,None])+(target/127.5-1)*weight[:,:,None]
        v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-8)
        new=np.uint8(np.rint(np.clip(v*127.5+127.5,0,255)));new=np.where((weight>0)[:,:,None],new,old)
        a[row:end,x0:x1,:3]=new;changed+=np.count_nonzero(np.any(old!=new,axis=2))
    assert np.all(a[:,:,3]==2)
    Image.fromarray(a).save(M/'v058_c_macro_n.tga')
    save(O/'C_materials.json',dict(photo_colour_sha256=sha(M/'v058_c_loose.tga'),macro_normal_sha256=sha(M/'v058_c_macro_n.tga'),changed_macro_texels=int(changed),cavity_strength=.18,cavity_is_normal_derived_not_true_AO=True,original_photo_normal_retained=True))
    print('C source textures authored',changed,'macro texels',flush=True)


def validate(section):
    # Keep the physical track and the approved van/truck/sign work pinned.
    assert sha(PREV/'terrain.raw')=='ab99df42094ef29015f117babeffe555e814fc7f86cf836c60625b760868289f'
    assert sha(R/'V057_OUTPUT/scenery.fbx')=='59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604'
    old=Image.open(source('v044_route_detail_n.tga'));new=Image.open(M/'v058_c_macro_n.tga');n=old.width;changes=0
    for row in range(0,n,128):
        a=np.asarray(old.crop((0,row,n,min(row+128,n))));b=np.asarray(new.crop((0,row,n,min(row+128,n))))
        yy,xx=np.where(np.any(a!=b,axis=2));changes+=len(xx)
        if len(xx):assert np.all(section.section((xx+.5)*600/n,600-(row+yy+.5)*600/n)>0)
        assert np.array_equal(a[:,:,3],b[:,:,3])
    assert changes>0
    s=np.arange(LO+.5,HI-.5,.25);x=np.interp(s,section.q[:,3],section.q[:,0]);z=np.interp(s,section.q[:,3],section.q[:,1])
    wear=np.asarray(Image.open(source('mask_v046_wear.tga')).getchannel('A'),np.float32)/255
    alpha=map_coordinates(wear,[(600-z)/600*4096-.5,x/600*4096-.5],order=1)
    recipe=dict(version='v058 material trials only',baseline='v056 dirt and terrain',approved_scenery_source_commit='8903065aca3301fd0eed0522738f370eb69743ca',
        approved_scenery_sha256=sha(R/'V057_OUTPUT/scenery.fbx'),terrain_sha256=sha(PREV/'terrain.raw'),
        section=dict(start_station_m=LO,end_station_m=HI,feather_m=FEATHER,photographic_boundary_mask_retained=True,contains=['R01 finish tabletop','connecting turn and flat','R02 triple']),
        methods=METHODS,all_terrain_geometry_unchanged=True,scenery_preserved_but_omitted_in_dirt_renders=True,
        all_candidate_differences_zero_outside_section=True,macro_changed_pixels=changes,
        audit=dict(section_centerline_overlay_percentiles=(np.percentile(alpha,[0,10,50,90,100])*100).tolist(),
            macro_texel_m=600/8192,photo_texel_m=2/4096,macro_to_photo_linear_spacing_ratio=150.,
            previous_preview_problem='Fixed, large-world composite raster and mip selected before projection blurred near-camera detail.',
            v057_control_problem='Changed photo normals and macro relief at the same time as reducing overlay opacity.',
            shader_repeat_caution='Photo shader repetitions=0 was interpreted as inheritance by the old source preview. Native semantics are not proven; proposed full-version shaders will use explicit repeats.'),
        production_integration=dict(native_build_started=False,approved_method=None,source_trials_are_not_a_compiled_test_package=True,
            A=dict(terrain_layers=14,extra_image_bytes=0),
            B_C=dict(strategy='Full-version design replaces existing 8K macro colour slot with a 4K photographic colour map; normal atlas remains 8K with independent 1x repeat. Integrate lower layer3 at matching colour repeats after selection.',
                estimated_colour_slot_rgba8_base_bytes_saved=8192*8192*4-4096*4096*4,
                caveat='Local render scope uses a sampler override; an isolated native test would require an extra masked pass. Full-track integration and native allocation validation are pending user selection.')),
        native_game_appearance_verified=False,performance_test=False)
    save(S/'experiments.json',recipe);save(O/'trial_validation.json',dict(checks_pass=True,**recipe))
    return recipe


def main():
    for p in [O,M,OUT,CACHE,S]:p.mkdir(parents=True,exist_ok=True)
    section=Section();author_c(section);validate(section)
    print('V058_THREE_SCOPED_TRIAL_RECIPES_VALIDATED',flush=True)


if __name__=='__main__':main()
