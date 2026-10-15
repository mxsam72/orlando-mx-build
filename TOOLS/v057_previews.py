"""Matched dirt source reviews and release preflight, no game claims."""
import numpy as np
from PIL import Image
from v057_inputs import R, PREV, O, sha, save
from v057_surface import baseline, source as updated
from v056_geometry import cross_points
from v054_previews import Terrain
from v054_geometry import read
import v049_previews as render

OUT=R/'BUILD/v057_review'
CURRENT='v056'


def source(name,version):return updated(name) if CURRENT=='v057' else baseline(name)


def main():
    global CURRENT
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ['terrain_validation','surface_validation','scenery_validation','race_validation']:
        assert read(O/(name+'.json'))['checks_pass']
    q=dict(np.load(O/'route.npz'))['q']; terrain=Terrain(O/'terrain.raw')
    render.OUT,render.source=OUT,source
    rows=[]
    for label,es,ts,eh in [('flat_loam',65.,91.,1.9),('finish_table',5.,32.,2.1),('single_landing',253.,282.,2.1)]:
        eye2=cross_points(q,np.array([es]),0)[0]; target2=cross_points(q,np.array([ts]),0)[0]
        points=np.stack([eye2,target2]);lo=points.min(0)-18;hi=points.max(0)+18;box=(*lo,*hi)
        eye=[*eye2,float(terrain.ground(eye2[None,0],eye2[None,1])[0])+eh]
        target=[*target2,float(terrain.ground(target2[None,0],target2[None,1])[0])+.5]
        frames=[]
        for version in ['v056','v057']:
            CURRENT=version; render.O=O if version=='v057' else PREV;render.BOX=box
            color,normal=render.composite('v049',n=1300)
            p=render.render(version,label,color,normal,terrain,eye,target,width=1100,height=700)
            frames.append(Image.open(p).copy()); rows.append(dict(file=p.name,sha256=sha(p),source_only=True,eye_xzy_m=eye,target_xzy_m=target))
        pair=Image.new('RGB',(2200,700));pair.paste(frames[0],(0,0));pair.paste(frames[1],(1100,0));pair.save(OUT/('comparison_'+label+'.jpg'),quality=95)
    for n in ['sign_face_1.png','sign_face_2.png']:assert (OUT/n).is_file()
    assert read(OUT/'vehicle_review.json')['meshes_sha256']==sha(O/'scenery.fbx')
    save(OUT/'manifest.json',dict(version='v057',source_only=True,in_game_captures=False,matched_cameras_and_light=True,
         terrain_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),surface_validation_sha256=sha(O/'surface_validation.json'),
         renders=rows,sign_serialized_UV_verified=True,vehicle_serialized_meshes_reviewed=True))
    print('V057_MATCHED_SOURCE_REVIEW_READY',flush=True)


if __name__=='__main__':main()
