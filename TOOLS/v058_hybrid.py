"""C's scanned loam with B's groove normals on the reviewed jump faces."""
import json
import numpy as np
from PIL import Image,ImageDraw
import v058_render as render
from v058_trials import R,PREV,S,METHODS,Section,sha,save,smooth
from v049_previews import font

OUT=R/'BUILD/v058_hybrid_review'
FEATURES=[(0.,51.5),(128.,177.)]
METHODS['H']=dict(title='C + B - Loamy dirt with jump-face grooves',summary="Keep C's 3m scan and cavity shading; blend B's macro grooves into sloped jump faces only.")
FACE_STATS=[]

def face_weight(section,ctx):
    s,l=section.coords(ctx['x'],ctx['z'])
    tx=np.interp(s,section.q[:,3],section.v[:,0]);tz=np.interp(s,section.q[:,3],section.v[:,1])
    hx,hz=section.slope(ctx['x'],ctx['z']);grade=hx*tx+hz*tz
    features=np.zeros_like(s)
    for a,b in FEATURES:
        features=np.maximum(features,smooth((s-a)/1.5)*smooth((b-s)/1.5))
    return smooth((np.abs(grade)-.06)/.13)*features

def hybrid(section,ctx,photo,cbase_rgb,cbase_n,c_macro,b_macro,old_alpha):
    f=face_weight(section,ctx)
    cap=.55/(232/255)
    alpha=old_alpha*(cap+(1-cap)*f)
    macro=render.blend(c_macro,b_macro,f)
    rgb=render.blend(cbase_rgb,photo,alpha);normal=render.blend(cbase_n,macro,alpha)
    c_rgb=render.blend(cbase_rgb,photo,old_alpha*cap)
    c_n=render.blend(cbase_n,c_macro,old_alpha*cap)
    flats=f==0
    # Copy the exact control where no face enhancement is requested. This
    # retains the reviewed C treatment without floating-point drift.
    rgb[flats]=c_rgb[flats];normal[flats]=c_n[flats]
    assert np.array_equal(rgb[flats],c_rgb[flats]) and np.array_equal(normal[flats],c_n[flats])
    FACE_STATS.append(dict(terrain_pixels=int(ctx['hit'].sum()),enhanced_face_pixels=int(np.count_nonzero((f>0)&ctx['hit'])),
        flat_pixels_exact_C=True,flat_pixel_count=int(np.count_nonzero(flats&ctx['hit'])),
        maximum_face_weight=float(f.max()),photo_sha256=sha(render.M/'v058_c_loose.tga')))
    return {'H':(rgb,normal)}

def main():
    OUT.mkdir(parents=True,exist_ok=True);render.OUT=OUT
    section=Section();materials=render.Materials();rows=[]
    key=sha(R/'TOOLS/v058_hybrid.py')+sha(R/'TOOLS/v058_render.py')
    for view in render.VIEWS:
        cache=OUT/('rows_'+view['id']+'.json')
        if cache.exists():
            prior=json.loads(cache.read_text())
            if prior['key']==key and all((OUT/r['file']).exists() and sha(OUT/r['file'])==r['sha256'] for r in prior['rows']):
                rows.extend(prior['rows']);FACE_STATS.append(prior['face_check']);continue
        result=render.render_view(section,materials,view,extra_candidates=hybrid)
        FACE_STATS[-1]['view']=view['id']
        save(cache,dict(key=key,rows=result,face_check=FACE_STATS[-1]))
        rows.extend(result)
    W,H=render.WIDTH,render.HEIGHT
    # Original B, original C and the hybrid from identical ray hits.
    sheet=Image.new('RGB',(W*3,H*4+105),(22,25,29));draw=ImageDraw.Draw(sheet)
    draw.text((22,12),'B grooves + C loam | Same section, camera and lighting',font=font(32),fill='white')
    draw.text((22,59),'LEFT: B reference     MIDDLE: C reference     RIGHT: combined treatment',font=font(27),fill=(209,219,225))
    for i,view in enumerate(render.VIEWS):
        for j,method in enumerate(['B','C','H']):sheet.paste(Image.open(OUT/(method+'_'+view['id']+'.jpg')),(j*W,105+i*H))
        pair=Image.new('RGB',(W*3,H))
        for j,method in enumerate(['B','C','H']):pair.paste(Image.open(OUT/(method+'_'+view['id']+'.jpg')),(j*W,0))
        pair.save(OUT/('Hybrid_Comparison_'+view['id']+'.jpg'),quality=96,subsampling=0)
    sheet.save(OUT/'Orlando_Dirt_C_With_B_Jump_Grooves_4Views.jpg',quality=96,subsampling=0)
    recipe=dict(source_only=True,native_build_started=False,scenery_placement_unchanged=True,
        terrain_sha256=sha(PREV/'terrain.raw'),scenery_sha256=sha(R/'V057_OUTPUT/scenery.fbx'),
        hybrid='C photographic loam plus B macro groove normals on sloped jump faces',
        photographic_colour_tile_exact_C=sha(render.M/'v058_c_loose.tga'),photo_size_m=3.,
        cavity_shading_exact_C=True,fine_normal_source='original scanned loose normal, 3m repeats',
        flat_and_deck_treatment_exact_C=True,face_weight='smooth(abs(along-route grade) from 0.06 to 0.19), only within reviewed jump feature envelopes',
        jump_envelopes_station_m=FEATURES,macro_normal='blend C to original B/v056 by face weight',
        alpha='blend C 55% cap toward original B strength by face weight',
        colour_note='Same C photo and cavity texture. Increased face opacity reduces packed-layer colour contribution only on the enhanced faces.',
        adds_terrain_images=False,adds_terrain_layers=False,native_integration_pending=True,
        native_game_appearance_verified=False,game_memory_measured=False,face_checks=FACE_STATS,renders=rows)
    assert all(r['changes_outside_section']==0 for r in rows)
    save(OUT/'hybrid_validation.json',dict(checks_pass=True,**recipe))
    save(S/'hybrid_recipe.json',dict(checks_pass=True,**recipe))
    print('V058_HYBRID_RENDERED_AND_VALIDATED',flush=True)

if __name__=='__main__':main()
