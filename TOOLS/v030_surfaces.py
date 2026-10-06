"""Restore v028 pits, clear the marked start area, halve remaining course grass.

The 50% target is spatial and opacity-weighted on the encoded native mask.
Original grass opacity survives in patch interiors. All other visual masks
and all other physical masks remain exactly the v028 source bytes.
"""
from PIL import Image
from matplotlib.path import Path as PolygonPath
from scipy.ndimage import distance_transform_edt, label
from v025_materials import macro_noise, save_mask
from v030_common import *

def alpha8(path):
    return np.asarray(Image.open(path).getchannel('A'),np.uint8)

def main():
    spec=read(S/'surface_spec.json')
    old=alpha8(BASE/'materials/mask_visual_grass.tga'); n=len(old)
    assert old.shape==(2048,2048)
    axis=np.linspace(0,SIZE,n)
    xx,zz=np.meshgrid(axis,SIZE-axis)
    points=np.c_[xx.ravel(),zz.ravel()]
    pits=(xx<spec['pit_grass_protection']['max_x'])&(zz<=spec['pit_grass_protection']['max_z'])
    circle=PolygonPath(spec['circled_polygon_xz_m']).contains_points(points).reshape(old.shape)
    circle=distance_transform_edt(~circle)*(SIZE/(n-1))<=spec['circle_padding_m']
    assert not np.any(circle&pits),'Circled start area overlaps protected pits'
    route=dict(np.load(O/'route.npz')); start=route['start']
    cfg=read(R/'V028_SOURCE/pit_access.json'); layout=access_layout(start,cfg)
    knots=np.asarray(read(R/'V024_SOURCE/facilities.json')['start_width_knots'])
    trees=[cKDTree(start[:,:2]),cKDTree(layout['lane'][:,:2]),cKDTree(layout['connector'][:,:2])]
    free=circle.copy()
    for row in range(0,n,64):
        p=np.c_[xx[row:row+64].ravel(),zz[row:row+64].ravel()]
        sd,si=trees[0].query(p,workers=2); pd,_=trees[1].query(p,workers=2); cd,_=trees[2].query(p,workers=2)
        offset=p-start[si,:2]
        station=start[si,3]+offset[:,0]*np.cos(start[si,2])+offset[:,1]*np.sin(start[si,2])
        half=np.interp(np.clip(station,0,start[-1,3]),knots[:,0],knots[:,1])/2
        start_free=(sd<half+spec['start_bare_margin_m'])&(station>=-1)&(station<=start[-1,3]+1)
        access_free=(pd<cfg['practice_width_m']/2+spec['corridor_bare_margin_m'])|(cd<cfg['connector_width_m']/2+spec['corridor_bare_margin_m'])
        free[row:row+64]|=(start_free|access_free).reshape(xx[row:row+64].shape)
    assert not np.any(free&pits),'Start/corridor exclusions overlap protected pits'
    x0,z0,x1,z1=spec['track_grass_bounds_xz_m']
    course=(xx>=x0)&(xx<=x1)&(zz>=z0)&(zz<=z1)
    eligible=course&~free&~pits
    # Measure distance to the actual grass boundary, not to the rectangular
    # review scope. That prevents an artificial bare border around the scope.
    inside=distance_transform_edt(old>=51)*(SIZE/(n-1))
    noise=macro_noise(n,np.random.default_rng(spec['grass_seed']),96)
    score=inside+np.clip(noise,-2,2)*.8
    keep=np.ones(old.shape,np.float32)
    components,count=label((old>=51)&eligible,np.ones((3,3)))
    assert count>0
    nearest=distance_transform_edt(components==0,return_distances=False,return_indices=True)
    zones=components[tuple(nearest)]
    patch_checks=[]
    # Halve every original patch independently. A large background field
    # must not consume the target and leave the small infield islands bare.
    for patch_id in range(1,count+1):
        selected=eligible&(zones==patch_id)
        values=old[selected];field=score[selected]
        before_sum=int(values.astype(np.uint64).sum())
        target=before_sum*spec['remaining_track_grass_fraction']
        assert target>0
        low=float(field.min()-spec['spatial_edge_blend_m']);high=float(field.max())
        for _ in range(38):
            threshold=(low+high)/2
            factor=ease((field-threshold)/spec['spatial_edge_blend_m'])
            measured=int(np.rint(values*factor).astype(np.uint64).sum())
            if measured>target:low=threshold
            else:high=threshold
        keep[selected]=ease((field-(low+high)/2)/spec['spatial_edge_blend_m'])
        after_sum=int(np.rint(values*keep[selected]).astype(np.uint64).sum())
        assert abs(after_sum-target)<=max(2,before_sum*.0001),(patch_id,before_sum,after_sum)
        patch_checks.append(dict(patch_id=patch_id,baseline_alpha_sum=before_sum,final_alpha_sum=after_sum,
            retained_fraction=after_sum/before_sum,erosion_threshold_m=(low+high)/2))
    keep[free]=0
    after=np.uint8(np.rint(old*keep))
    assert np.array_equal(after[pits],old[pits])
    assert not np.any(after[circle]) and not np.any(after[free])
    assert np.all(after<=old)
    save_mask(M/'mask_visual_grass.tga',after.astype(np.float32)/255)
    before_physical=alpha8(BASE/'masks/grass.tga')
    physical=np.uint8(np.rint(before_physical*keep)); physical[free]=0
    save_mask(O/'masks/grass.tga',physical.astype(np.float32)/255)
    encoded=alpha8(M/'mask_visual_grass.tga'); encoded_physical=alpha8(O/'masks/grass.tga')
    assert np.array_equal(encoded,after) and np.array_equal(encoded_physical,physical)
    assert np.array_equal(physical[pits],before_physical[pits])
    changed=eligible|free
    assert np.array_equal(after[~changed],old[~changed])
    assert np.array_equal(physical[~changed],before_physical[~changed])
    ratio=float(encoded[eligible].astype(np.uint64).sum()/old[eligible].astype(np.uint64).sum())
    assert abs(ratio-.5)<.0001,ratio
    preserved_visual_masks={}
    for p in (BASE/'materials').glob('mask_*.tga'):
        if p.name=='mask_visual_grass.tga':continue
        out=M/p.name.replace('v028_','v030_')
        assert sha(out)==sha(p),'Unexpected v028 visual mask change: '+p.name
        preserved_visual_masks[p.name]=sha(p)
    for suffix in ['.tga','.shd']:
        before=BASE/'materials'/('v028_grass'+suffix);out=M/('v030_grass'+suffix)
        if suffix=='.tga':assert sha(before)==sha(out)
        else:assert before.read_text().replace('v028_','v030_')==out.read_text()
    qa=dict(version='v030',checks_pass=True,baseline_version='v028',native_mask_size=n,
        track_grass_bounds_xz_m=spec['track_grass_bounds_xz_m'],
        remaining_course_grass_fraction=ratio,remaining_course_grass_reduction_percent=round(100*(1-ratio),4),
        reduction_scope='Remaining track-area grass after clearing marked starting section; pits excluded',
        baseline_remaining_course_grass_alpha_sum=int(old[eligible].astype(np.uint64).sum()),
        final_remaining_course_grass_alpha_sum=int(encoded[eligible].astype(np.uint64).sum()),
        surviving_patch_interiors_keep_v028_opacity=True,patchwise_reduction=True,
        original_grass_patch_count=count,patch_checks=patch_checks,
        circled_area_samples=int(circle.sum()),start_section_exclusion_samples=int(free.sum()),
        circle_visual_grass_nonzero_samples=int(np.count_nonzero(encoded[circle])),
        circle_physical_grass_nonzero_samples=int(np.count_nonzero(encoded_physical[circle])),
        start_visual_grass_nonzero_samples=int(np.count_nonzero(encoded[free])),
        start_physical_grass_nonzero_samples=int(np.count_nonzero(encoded_physical[free])),
        pit_visual_grass_changed_samples=int(np.count_nonzero(encoded[pits]!=old[pits])),
        pit_physical_grass_changed_samples=int(np.count_nonzero(encoded_physical[pits]!=before_physical[pits])),
        pit_grass_preserved_samples=int(pits.sum()),pit_grass_protection=spec['pit_grass_protection'],
        staging_inside_user_circle_cleared=True,no_new_grass=True,all_other_v028_visual_masks_byte_exact=True,
        preserved_visual_mask_sha256=preserved_visual_masks,grass_tile_exact_v028=True,
        changed_physical_masks=['grass'],terrain_unchanged=True,in_game_visual_check=False)
    save(O/'grass_reduction_validation.json',qa)
    save_npz(O/'grass_scope_masks.npz',circle=circle,free=free,pits=pits,eligible=eligible)
    print('v030 grass checks passed: remaining track grass reduced',qa['remaining_course_grass_reduction_percent'],'%; pits grass changes 0; circled/start grass 0',flush=True)

if __name__=='__main__':main()
