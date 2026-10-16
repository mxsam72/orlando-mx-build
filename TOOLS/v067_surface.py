"""Deterministic v067 material/lighting candidate; deliberately never compiles.

Restore the pinned v066 source with TOOLS/v066_lighting.py restore first.
The patch only edits three color maps, three normal maps, and daylight inputs.
All routes, height samples, physical declarations, scenery and masks are exact.
"""
from pathlib import Path
import copy, gc, hashlib, json, math, os, re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
import v066_lighting as old

R=Path(__file__).resolve().parents[1]
BASE=R/'V066_OUTPUT'; O=R/'V067_OUTPUT'; M=O/'materials'; S=R/'V067_SOURCE'
TERRAIN_SHA=old.TERRAIN_SHA; SCENERY_SHA=old.SCENERY_SHA
sha=old.sha; save=old.save
CHANGED={'v045_loose.tga','v045_packed.tga','v044_route_detail.tga',
         'v045_loose_n.tga','v045_packed_n.tga','v044_route_detail_n.tga'}

def source(name, baseline=False):
    root=BASE if baseline else O
    for d in [root/'materials',root/'facility_textures',root]:
        if (d/name).is_file(): return d/name
    raise FileNotFoundError(name)

def image_write(a,path):
    temp=path.with_name(path.stem+'.writing.tga')
    Image.fromarray(a).save(temp);temp.replace(path)

def retain():
    M.mkdir(parents=True,exist_ok=True);S.mkdir(exist_ok=True)
    for p in BASE.rglob('*'):
        if not p.is_file() or p.suffix=='.json' or p.name.startswith('.'):continue
        dest=O/p.relative_to(BASE);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():os.link(p,dest)
    for name in ['native_probes.json']:
        if (BASE/name).is_file() and not (O/name).exists():os.link(BASE/name,O/name)

def color_tile(name,spec):
    a=np.asarray(Image.open(source(name,True)),np.float32)
    out=a.copy()
    # Derive all grain from the existing photographic tile. No added stripes,
    # highlight painting, palette substitution or synthetic displacement.
    y=a[...,:3].mean(2)
    mid=gaussian_filter(y,2.2,mode='wrap')-gaussian_filter(y,21,mode='wrap')
    fine=y-gaussian_filter(y,2.2,mode='wrap')
    delta=spec['soil_midfrequency_gain']*mid+spec['soil_finefrequency_gain']*fine
    # Gently reduce the large dark blob in the repeated tile, while retaining
    # the photographic aggregate and mean of each original color channel.
    broad=gaussian_filter(y,86,mode='wrap');delta-=.12*(broad-broad.mean())
    delta-=delta.mean()
    out[...,:3]=np.clip(a[...,:3]+delta[...,None],0,255)
    out=np.uint8(np.rint(out));image_write(out,source(name))
    means0=a[...,:3].mean((0,1),dtype=np.float64);means1=out[...,:3].mean((0,1),dtype=np.float64)
    assert np.max(np.abs(means1-means0))<1.0
    return dict(file=name,mean_before=means0.tolist(),mean_after=means1.tolist())

def tile_normal(name,gain):
    a=np.array(Image.open(source(name,True)));out=a.copy()
    for r in range(0,len(a),128):
        nn=a[r:r+128,:,:3].astype(np.float32)/127.5-1
        nn[...,:2]*=gain
        nn/=np.maximum(np.linalg.norm(nn,axis=2,keepdims=True),1e-6)
        out[r:r+128,:,:3]=np.uint8(np.rint(np.clip(nn*127.5+127.5,0,255)))
    assert np.array_equal(out[:,:,3],a[:,:,3])
    image_write(out,source(name))

def route_normal(spec):
    name='v044_route_detail_n.tga';a=np.array(Image.open(source(name,True)));out=a.copy();n=len(a)
    mask=np.asarray(Image.open(source('mask_v046_section.tga',True)).getchannel('A'),np.float32)/255
    # Sample a properly low-passed 3 m photo tile for resolved 15-30 cm clods.
    # World atlas spacing is 600/8192 m: frequencies finer than that are left
    # to the existing 4K tiled normals, preventing aliased moire in this atlas.
    photo=np.asarray(Image.open(source('v045_loose.tga',True)).convert('L').resize((256,256),Image.Resampling.BOX),np.float32)
    relief=gaussian_filter(photo,6.5,mode='wrap')-gaussian_filter(photo,19,mode='wrap')
    relief/=max(float(relief.std()),1e-6);relief*=spec['photo_clod_height_std_m']
    dx=3/256
    gy=(np.roll(relief,-1,0)-np.roll(relief,1,0))/(2*dx)
    gx=(np.roll(relief,-1,1)-np.roll(relief,1,1))/(2*dx)
    ground=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
    hy,hx=np.gradient(ground,600/2048);hz=-hy
    changed=0;outside=0;xs=(np.arange(n,dtype=np.float32)+.5)/n
    for r in range(0,n,96):
        stop=min(n,r+96);ys=(np.arange(r,stop,dtype=np.float32)+.5)/n
        xx,yy=np.meshgrid(xs,ys)
        w=map_coordinates(mask,[yy*len(mask)-.5,xx*len(mask)-.5],order=1,mode='nearest')
        w=np.clip((w-.01)/.98,0,1);use=w>0
        original=a[r:stop,:,:3];nn=original.astype(np.float32)/127.5-1
        slopes=nn[...,:2]/np.maximum(nn[...,2:3],.22)
        slopes*=1+(spec['route_normal_slope_gain']-1)*w[...,None]
        coords=[np.mod(yy*200,1)*256-.5,np.mod(xx*200,1)*256-.5]
        px=map_coordinates(gx,coords,order=1,mode='grid-wrap')
        py=map_coordinates(gy,coords,order=1,mode='grid-wrap')
        tx=map_coordinates(hx,[yy*2048,xx*2048],order=1,mode='nearest')
        tz=map_coordinates(hz,[yy*2048,xx*2048],order=1,mode='nearest')
        tangent_x=px/np.sqrt(1+tx*tx)
        tangent_z=(-py-px*tx*tz/(1+tx*tx))/np.sqrt((1+tx*tx+tz*tz)/(1+tx*tx))
        slopes[...,0]-=tangent_x*w*spec['photo_clod_normal_weight']
        slopes[...,1]-=tangent_z*w*spec['photo_clod_normal_weight']
        nn=np.concatenate([slopes,np.ones((*w.shape,1),np.float32)],axis=2)
        nn/=np.maximum(np.linalg.norm(nn,axis=2,keepdims=True),1e-6)
        enc=np.uint8(np.rint(np.clip(nn*127.5+127.5,0,255)))
        enc=np.where(use[...,None],enc,original)
        diff=np.any(enc!=original,axis=2);changed+=int(diff.sum());outside+=int((diff&~use).sum())
        out[r:stop,:,:3]=enc
    assert outside==0 and np.array_equal(out[:,:,3],a[:,:,3])
    image_write(out,source(name));return dict(file=name,changed_pixels=changed,changes_outside_course_mask=outside)

def lighting(spec):
    baseline=old.parse_amb((BASE/'trial_daylight.amb').read_text());amb=copy.deepcopy(baseline)
    az=math.radians(spec['sun_azimuth_xz_degrees']);el=math.radians(spec['sun_elevation_degrees'])
    y=spec['sun_position_y'];h=y/math.tan(el)
    amb['sun_position']=dict(x=h*math.cos(az),y=y,z=h*math.sin(az))
    for key,field in [('ambient','clear_ambient_rgb'),('sun_color','clear_sun_rgb')]:
        amb['clear'][key]=dict(zip(['red','green','blue'],spec[field]))
    amb['clear']['fog']['density']=spec['clear_fog_density']
    for weather in ['cloudy','rainy']:assert amb[weather]==baseline[weather]
    # Replace the linked copies atomically, never mutate the baseline inode.
    for name,text in [('trial_daylight.amb',old.format_amb(amb)),
                      ('map_params.ini',old.author_params((BASE/'map_params.ini').read_text(),spec))]:
        temp=O/(name+'.writing');temp.write_text(text);temp.replace(O/name)
    return old.validate_pair((O/'trial_daylight.amb').read_text(),(O/'map_params.ini').read_text())

def validate(edits,light):
    expected=old.read(R/'V066_SOURCE/native_expected_inputs.json')
    protected={}
    for name in ['terrain.raw','scenery.fbx','route.npz','compiled_track.hmf','main.tcl','start.tcl']:
        assert sha(O/name)==sha(BASE/name),name;protected[name]=sha(O/name)
    assert protected['terrain.raw']==TERRAIN_SHA and protected['scenery.fbx']==SCENERY_SHA
    inventory=[];changed=[];unchanged=[]
    base=old.read(R/'V065_SOURCE/surface_validation.json')
    for row in base['active_terrain_inventory']:
        p=source(row['file']);im=Image.open(p)
        assert list(im.size)==row['size'] and im.mode==row['mode']
        actual=sha(p);new=dict(row,sha256=actual);inventory.append(new)
        if row['file'] in CHANGED:
            assert actual!=row['sha256'];changed.append(row['file'])
        else:
            assert actual==row['sha256'];unchanged.append(row['file'])
        assert sha(source(row['file'],True))==row['sha256'],'Baseline was modified'
    shaders=[]
    for row in base['active_shaders']:
        assert sha(source(row['file']))==row['sha256'];shaders.append(row)
    assert len(changed)==6
    assert sha(old.BASE_BUILD/'v054_track.tht')==expected['physical_declarations']
    report=dict(checks_pass=True,version='v067',native_compilation_started=False,in_game_verified=False,
        preserved=protected,physical_declarations_sha256=expected['physical_declarations'],
        all_masks_exact_v066=True,all_scenery_exact_v066=True,baseline_integrity_pass=True,
        lighting=light,changed_material_files=changed,unchanged_material_files=unchanged,
        active_terrain_inventory=inventory,active_shaders=shaders,
        layer_count=14,texture_allocation_bytes=base['texture_allocation_bytes'],
        added_layers=0,added_images=0,color_and_normal_edits=edits)
    save(O/'surface_validation.json',report);save(S/'precompile_validation.json',report)
    save(S/'native_expected_inputs.json',dict(terrain=protected['terrain.raw'],scenery=protected['scenery.fbx'],
        hmf=protected['compiled_track.hmf'],main_route=protected['main.tcl'],start_route=protected['start.tcl'],
        daylight=sha(O/'trial_daylight.amb'),map_params=sha(O/'map_params.ini'),
        physical_declarations=expected['physical_declarations'],native_scenery=expected['native_scenery'],
        terrain_images={r['file']:r['sha256'] for r in inventory},
        terrain_shaders={r['file']:r['sha256'] for r in shaders}))
    print('V067_PREVIEW_SOURCE_PASS; exact layout/scenery/masks, six material maps, 45-degree morning sun',flush=True)

def main():
    old.check();spec=old.read(S/'visual_spec.json');retain();edits=[]
    for name in ['v045_loose.tga','v045_packed.tga','v044_route_detail.tga']:
        edits.append(color_tile(name,spec));gc.collect();print('REFINED',name,flush=True)
    for name,gain in [('v045_loose_n.tga',spec['loose_normal_slope_gain']),('v045_packed_n.tga',spec['packed_normal_slope_gain'])]:
        tile_normal(name,gain);gc.collect();print('REFINED',name,flush=True)
    edits.append(route_normal(spec));gc.collect();validate(edits,lighting(spec))
if __name__=='__main__':main()
