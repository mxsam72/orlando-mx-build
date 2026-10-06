"""Remove continuous turf, including both user-marked start-corridor strips.

Grass reduction is spatial, rather than merely a uniform opacity change.
All exclusions are enforced on the actual 2048-pixel native mask grid.
Terrain and accepted racing/start coverage are not regenerated here.
"""
from PIL import Image
from scipy.ndimage import distance_transform_edt
from v025_materials import macro_noise, save_mask
from v029_common import *

def alpha(p): return np.asarray(Image.open(p).getchannel('A'),np.float32)/255

def main():
    spec=read(S/'surface_spec.json'); cfg=read(R/'V028_SOURCE/pit_access.json')
    old=alpha(BASE/'materials/mask_visual_grass.tga'); n=len(old)
    route=dict(np.load(O/'route.npz')); start=route['start']; q=route['q']
    a=access_layout(start,cfg); knots=np.asarray(read(R/'V024_SOURCE/facilities.json')['start_width_knots'])
    trees=[cKDTree(a['lane'][:,:2]),cKDTree(a['connector'][:,:2]),cKDTree(start[:,:2]),cKDTree(q[:-1,:2])]
    rng=np.random.default_rng(spec['seed'])
    patches=macro_noise(n,rng,88)*.80+macro_noise(n,rng,290)*.40
    # Few irregular grass remnants with a soft, thin soil transition.
    patch=ease((patches-spec['grass_patch_threshold'])/.70)*spec['grass_patch_opacity']
    interior=distance_transform_edt(old>.10)*(SIZE/(n-1))
    thin=ease((interior-spec['grass_edge_erosion_m'])/1.2)
    free=np.zeros((n,n),bool); access_free=np.zeros((n,n),bool); race_margin=np.zeros((n,n),np.float32)
    axis=np.linspace(0,SIZE,n)
    for row in range(0,n,64):
        zz,xx=np.meshgrid(SIZE-axis[row:row+64],axis,indexing='ij'); pts=np.c_[xx.ravel(),zz.ravel()]
        pd,_=trees[0].query(pts,workers=2); cd,_=trees[1].query(pts,workers=2)
        sd,si=trees[2].query(pts,workers=2); md,mi=trees[3].query(pts,workers=2)
        sv=pts-start[si,:2]
        station=start[si,3]+sv[:,0]*np.cos(start[si,2])+sv[:,1]*np.sin(start[si,2])
        half=np.interp(np.clip(station,0,start[-1,3]),knots[:,0],knots[:,1])/2
        start_free=(sd<half+spec['start_bare_margin_m'])&(station>=-5)&(station<=start[-1,3]+5)
        lane_free=pd<cfg['practice_width_m']/2+spec['corridor_bare_margin_m']
        connector_free=cd<cfg['connector_width_m']/2+spec['corridor_bare_margin_m']
        free[row:row+len(xx)]=(start_free|lane_free|connector_free).reshape(xx.shape)
        access_free[row:row+len(xx)]=(lane_free|connector_free).reshape(xx.shape)
        race_margin[row:row+len(xx)]=ease((md-route['width'][mi]/2-spec['riding_bare_margin_m'])/2).reshape(xx.shape)
    protected=np.maximum.reduce([alpha(O/'masks'/f'{k}.tga') for k in ['racing','start','shoulder','worked']])>0
    grass=old*patch*thin*race_margin
    grass[free|protected]=0
    # No new grass is added anywhere, even at interpolated mask boundaries.
    assert np.all(grass<=old+1e-7)
    save_mask(M/'mask_visual_grass.tga',grass)
    old_physical=alpha(BASE/'masks/grass.tga')
    physical=np.minimum(old_physical,grass); physical[free|protected]=0
    save_mask(O/'masks/grass.tga',physical)
    removed=np.maximum(old-grass,0)
    sand=alpha(BASE/'materials/mask_visual_sand.tga')
    # Exposed margins become a varied sandy soil, never a green undercoat.
    sand=np.maximum(sand,removed*(.14+.16*np.clip((patches+2)/4,0,1)))
    save_mask(M/'mask_visual_sand.tga',sand)
    # Cover the entire excluded corridor, including the rail-side shoulder.
    # A small edge blend lies outside the strictly grass-free corridor.
    inside=distance_transform_edt(access_free)*(SIZE/(n-1))
    corridor=ease(inside/.65)*.94
    # The start clay and active racing lane retain their prepared dirt.
    corridor[protected]=0
    pit=alpha(BASE/'materials/mask_v028_pits.tga'); save_mask(M/'mask_v029_pits.tga',np.maximum(pit,corridor))
    save_mask(M/'mask_v029_grass_free.tga',free.astype(np.float32))
    # Nonrepeating clod patches survive middle-distance mip filtering.
    # They are limited to authored loose soil and interrupted riding margins.
    f=dict(np.load(BASE/'surface_fields.npz'))
    def resize(v): return np.asarray(Image.fromarray(v).resize((n,n),Image.Resampling.BILINEAR))
    clods=resize(np.maximum(f['churn'],f['margin']*.6))*ease((patches+.7)/1.6)*.38
    clods[free]=0; save_mask(M/'mask_v029_clods.tga',clods)
    worked=alpha(BASE/'materials/mask_visual_worked.tga')
    save_mask(M/'mask_visual_worked.tga',np.maximum(worked,clods))
    after=alpha(M/'mask_visual_grass.tga'); after_physical=alpha(O/'masks/grass.tga')
    assert not np.any(after[free]) and not np.any(after_physical[free])
    ratio=float(after.sum()/max(float(old.sum()),1))
    assert ratio<=spec['maximum_grass_alpha_area_ratio'],('Insufficient grass reduction',ratio)
    pixel_area=(SIZE/n)**2
    qa=dict(checks_pass=True,version='v029',native_mask_size=n,
        grass_alpha_area_before_m2=float(old.sum()*pixel_area),grass_alpha_area_after_m2=float(after.sum()*pixel_area),
        grass_alpha_area_reduction_percent=round(100*(1-ratio),2),
        grass_visible_area_before_m2=float(np.count_nonzero(old>=.5)*pixel_area),
        grass_visible_area_after_m2=float(np.count_nonzero(after>=.5)*pixel_area),
        no_new_grass=True,grass_free_corridor_samples=int(free.sum()),
        corridor_visual_grass_nonzero_samples=int(np.count_nonzero(after[free])),
        corridor_physical_grass_nonzero_samples=int(np.count_nonzero(after_physical[free])),
        corridor_bare_margin_m=spec['corridor_bare_margin_m'],start_bare_margin_m=spec['start_bare_margin_m'],
        racing_start_shoulder_worked_mask_hashes={k:sha(O/'masks'/f'{k}.tga') for k in ['racing','start','shoulder','worked']},
        grass_removed_on_exact_native_grid=True,remaining_grass_is_sparse_irregular_patches=True,
        terrain_unchanged=True,changed_physical_masks=['grass'],in_game_visual_check=False)
    save(O/'grass_reduction_validation.json',qa)
    Image.fromarray(np.uint8(free)*255).save(O/'grass_free_corridor.png')
    print('v029 grass alpha area reduced',qa['grass_alpha_area_reduction_percent'],'percent; corridor grass is zero',flush=True)

if __name__=='__main__':main()
