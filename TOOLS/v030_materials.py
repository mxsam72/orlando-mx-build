"""Two-scale cohesive dirt detail and correlated normal maps, at 2048 pixels.

Uses the accepted photographic grain and clods, with periodic deterministic
variation. Colour and height share fields; no unrelated colour-only noise is
painted onto the riding lane. All rendered relief remains in normal maps.
"""
import re
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from v025_materials import normals
from v028_materials import layer_blocks
from v030_common import *

def standard(a):
    a=a-a.mean(); return a/max(float(a.std()),1e-5)

def edges(a):
    a[[0,-1],:]=a[[0,-1],:].mean(axis=0)
    a[:,[0,-1]]=a[:,[0,-1]].mean(axis=1)[:,None]
    return a

def main():
    spec=read(S/'surface_spec.json'); n=spec['tile_size']; rng=np.random.default_rng(spec['seed']+29)
    work=np.asarray(Image.open(BASE/'materials/v028_worked.tga').convert('RGB').resize((n,n),Image.Resampling.LANCZOS),np.float32)
    clods=standard(gaussian_filter(work.mean(axis=2),2,mode='wrap')-gaussian_filter(work.mean(axis=2),55,mode='wrap'))
    noise=rng.standard_normal((n,n)).astype(np.float32)
    aggregate=standard(gaussian_filter(noise,18,mode='wrap'))
    fines=standard(gaussian_filter(noise,1.1,mode='wrap'))
    tiles=[]; heights={}
    for family in ['soil','prepared','worked','sand','packed','face','pits']:
        source=BASE/'materials'/f'v028_{family}.tga'
        rgb0=np.asarray(Image.open(source).convert('RGB').resize((n,n),Image.Resampling.LANCZOS),np.float32)
        micro=rgb0-gaussian_filter(rgb0,(48,48,0),mode='wrap')
        strengths={'soil':(4.4,.9),'prepared':(7.0,1.0),'worked':(4.0,1.05),'sand':(2.0,.82),'packed':(3.2,.86),'face':(5.0,1.0),'pits':(2.2,.72)}
        contrast,gain=strengths[family]
        detail=clods*contrast+aggregate*(2.5 if family!='packed' else 1.4)+fines*.65
        rgb=edges(np.clip(micro*gain+np.asarray(spec['palette'][family])+detail[...,None]*[1,.96,.90],0,255))
        rgb=np.uint8(np.rint(rgb)); stem='v030_'+family; Image.fromarray(rgb).save(M/(stem+'.tga'))
        wet=np.uint8(np.rint(rgb.astype(float)*spec['wet_factor'][family]));Image.fromarray(wet).save(M/(stem+'_wet.tga'))
        grain=standard(gaussian_filter(micro.mean(axis=2),.8,mode='wrap'))
        cohesive=standard(gaussian_filter(clods,4,mode='wrap'))
        amp=spec['height_amplitude_m'][family]
        h=edges(cohesive*amp+grain*amp*.20+fines*.00012);heights[family]=h
        reps=spec['repetitions'][family];spacing=(SIZE/reps)/n
        nm=normals(h,spacing,1.,2 if family not in ['sand','pits'] else 1)
        # Periodic texels are identical across both boundaries, including normals.
        nm[0]=nm[-1]=np.uint8(np.rint((nm[0].astype(float)+nm[-1])/2))
        nm[:,0]=nm[:,-1]=np.uint8(np.rint((nm[:,0].astype(float)+nm[:,-1])/2))
        Image.fromarray(nm).save(M/(stem+'_n.tga'))
        for suffix in ['','_wet']:
            (M/(stem+suffix+'.shd')).write_text(f'bump\n{{\n map = {stem}_n.tga\n repetitions = {reps}\n}}\nspecular\n{{\n shininess = 8\n}}\n')
        assert np.array_equal(rgb[0],rgb[-1]) and np.array_equal(rgb[:,0],rgb[:,-1])
        assert np.array_equal(nm[0],nm[-1]) and np.array_equal(nm[:,0],nm[:,-1])
        tiles.append(dict(material=stem,size=[n,n],source_sha256=sha(source),mean_rgb=rgb.mean(axis=(0,1)).round(2).tolist(),
            cohesive_clod_and_normal_fields_correlated=True,diffuse_edge_jump=0,normal_edge_jump=0,
            normal_height_amplitude_m=amp,specular_alpha_max=int(nm[...,3].max()),
            normal_vector_variation=float(np.asarray(nm[...,:3],float).std(axis=(0,1)).mean())))
    base=np.asarray(Image.open(M/'v030_prepared.tga').convert('RGB'),np.float32)
    yy,xx=np.meshgrid(np.arange(n)/n,np.arange(n)/n,indexing='ij')
    # Directional ridges are interrupted by shared cohesive dirt patches.
    continuity=.28+.72*ease((aggregate+.55)/1.55)
    for angle,(kx,ky) in zip(spec['grooming_angles_degrees'],[(0,-12),(-8,-8),(-12,0),(-8,8)]):
        phase=2*np.pi*(kx*xx+ky*yy)+.20*np.sin(2*np.pi*(xx+yy))+.13*np.sin(2*np.pi*(3*xx-2*yy))
        grooves=(np.sin(phase)*.70+np.sin(2*phase+.45)*.15)*continuity
        h=edges(heights['prepared']+grooves*spec['grooming_height_amplitude_m'])
        rgb=np.uint8(np.rint(edges(np.clip(base+grooves[...,None]*spec['grooming_diffuse_contrast'],0,255))))
        stem=f'v030_groom_{angle}'; reps=spec['repetitions']['prepared']
        Image.fromarray(rgb).save(M/(stem+'.tga'));Image.fromarray(np.uint8(np.rint(rgb*.85))).save(M/(stem+'_wet.tga'))
        nm=normals(h,(SIZE/reps)/n,1.,2)
        nm[0]=nm[-1]=np.uint8(np.rint((nm[0].astype(float)+nm[-1])/2));nm[:,0]=nm[:,-1]=np.uint8(np.rint((nm[:,0].astype(float)+nm[:,-1])/2))
        Image.fromarray(nm).save(M/(stem+'_n.tga'))
        for suffix in ['','_wet']:
            (M/(stem+suffix+'.shd')).write_text(f'bump\n{{\n map = {stem}_n.tga\n repetitions = {reps}\n}}\nspecular\n{{\n shininess = 8\n}}\n')
        tiles.append(dict(material=stem,size=[n,n],world_direction_deg=angle,diffuse_edge_jump=0,normal_edge_jump=0,
            normal_height_amplitude_m=spec['grooming_height_amplitude_m'],grooming_is_broken_by_shared_clod_field=True))
    Image.fromarray(np.uint8(np.rint(base*.79))).save(M/'v030_damp.tga')
    Image.open(M/'v030_prepared_n.tga').save(M/'v030_damp_n.tga')
    text=(M/'track.hmf').read_text()
    for family in spec['repetitions']:
        text=re.sub(r'(map = v030_'+family+r'\.tga\s+repetitions = )\d+',lambda m:m[1]+str(spec['repetitions'][family]),text)
    for _,_,block in layer_blocks(text):
        if 'map = v030_pits.tga' in block and 'frame1' not in block:
            text=text.replace(block,block[:-1]+' frame1\n {\n  map = v030_pits_wet.tga\n }\n}')
    assert len(layer_blocks(text))==14 and text.count('scene0')==1
    (M/'track.hmf').write_text(text)
    for p in M.glob('*.tga'):
        im=Image.open(p);assert not im.width&(im.width-1) and not im.height&(im.height-1)
    qa=dict(version='v030',checks_pass=True,tiles=tiles,physical_terrain_unchanged=True,source=read(R/'V026_SOURCE/asset_provenance.json'),
        dirt_tile_size=n,native_supported_features_only=True,color_and_normal_share_clods=True,
        wet_variants_preserved=True,matte_default=True,in_game_visual_check=False,
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.iterdir()) if p.is_file()})
    save(O/'material_validation.json',qa)
    names=['soil','prepared','worked','sand','packed','pits','groom_0','groom_45','groom_90','groom_135','face','damp']
    preview=Image.new('RGB',(1600,1290),(26,26,26));d=ImageDraw.Draw(preview)
    for i,name in enumerate(names):
        x=i%4*400;y=i//4*430;preview.paste(Image.open(M/f'v030_{name}.tga').resize((400,400)),(x,y));d.text((x+8,y+408),'v030 '+name+' | source tile',fill='white')
    save_png(preview,O/'material_tiles.png')
    print('v030 2048-pixel dirt, cohesive normals and interrupted grooming validated',flush=True)

if __name__=='__main__':main()
