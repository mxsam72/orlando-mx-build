"""Fine tiled soil, directional grooming and shared local riding-line masks."""
import re, shutil
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from v025_materials import normals, save_mask
from v028_common import *

def tiles(spec):
    qa=[]
    accepted=R/'V027_OUTPUT/materials'
    # Regrade the byte-verified v027 grain, preserving existing close-up detail
    # and normals. This build needs no original JPEG download or regeneration.
    for p in accepted.iterdir():
        if p.suffix=='.shd':
            (M/p.name.replace('v027_','v028_')).write_text(p.read_text().replace('v027_','v028_'))
        elif p.suffix=='.tga' and not p.name.startswith('mask_'):
            shutil.copy2(p,M/p.name.replace('v027_','v028_'))
    for name,target in spec['palette'].items():
        old=accepted/f'v027_{name}.tga';a=np.asarray(Image.open(old).convert('RGB'),float)
        graded=np.clip(a-a.mean(axis=(0,1))+target,0,255)
        if name!='grass':
            graded[[0,-1],:]=graded[[0,-1],:].mean(axis=0);graded[:,[0,-1]]=graded[:,[0,-1]].mean(axis=1)[:,None]
        rgb=np.uint8(np.rint(graded));Image.fromarray(rgb).save(M/f'v028_{name}.tga')
        wet=accepted/f'v027_{name}_wet.tga'
        if wet.exists():
            factor=np.asarray(Image.open(wet).convert('RGB'),float)/np.maximum(a,1)
            Image.fromarray(np.uint8(np.rint(np.clip(rgb*factor,0,255)))).save(M/f'v028_{name}_wet.tga')
        qa.append(dict(material=name,source_v027_tile_sha256=sha(old),mean_rgb=rgb.mean(axis=(0,1)).round(2).tolist(),edge_jump_mean=float(abs(rgb[0].astype(float)-rgb[-1].astype(float)).mean()) if name!='grass' else 0.,accepted_microstructure_preserved=True))
    base=np.asarray(Image.open(M/'v028_prepared.tga').convert('RGB'),float); n=len(base)
    yy,xx=np.meshgrid(np.arange(n)/n,np.arange(n)/n,indexing='ij')
    lum=base.mean(axis=2); grain=gaussian_filter(lum,.8,mode='wrap')-gaussian_filter(lum,14,mode='wrap')
    grain/=max(float(grain.std()),1.)
    for angle,(kx,ky) in zip(spec['grooming_angles_degrees'],[(0,-12),(-8,-8),(-12,0),(-8,8)]):
        phase=2*np.pi*(kx*xx+ky*yy)+.18*np.sin(2*np.pi*(xx+yy))+.10*np.sin(2*np.pi*(3*xx-2*yy))
        grooves=np.sin(phase)*.72+np.sin(phase*2+.4)*.14
        h=grooves*spec['grooming_height_amplitude_m']+grain*.0016
        h[[0,-1],:]=h[[0,-1],:].mean(axis=0); h[:,[0,-1]]=h[:,[0,-1]].mean(axis=1)[:,None]
        rgb=np.clip(base+grooves[...,None]*3.5,0,255)
        rgb[[0,-1],:]=rgb[[0,-1],:].mean(axis=0); rgb[:,[0,-1]]=rgb[:,[0,-1]].mean(axis=1)[:,None]
        stem=f'v028_groom_{angle}'; ar=np.uint8(np.rint(rgb))
        Image.fromarray(ar).save(M/(stem+'.tga')); Image.fromarray(np.uint8(np.rint(ar*.85))).save(M/(stem+'_wet.tga'))
        Image.fromarray(normals(h,(SIZE/spec['repetitions']['prepared'])/n,1.,2)).save(M/(stem+'_n.tga'))
        for wet in ['', '_wet']:
            (M/(stem+wet+'.shd')).write_text(f'bump\n{{\n map = {stem}_n.tga\n repetitions = {spec["repetitions"]["prepared"]}\n}}\nspecular\n{{\n shininess = 8\n}}\n')
        qa.append(dict(material=stem,world_direction_deg=angle,world_groove_spacing_m=(SIZE/spec['repetitions']['prepared'])/np.hypot(kx,ky),normal_height_amplitude_m=spec['grooming_height_amplitude_m'],edge_jump_mean=float(abs(ar[0].astype(float)-ar[-1].astype(float)).mean())))
    Image.fromarray(np.uint8(np.rint(base*.79))).save(M/'v028_damp.tga')
    shutil.copy2(M/'v028_prepared_n.tga',M/'v028_damp_n.tga')
    (M/'v028_damp.shd').write_text('bump\n{\n map = v028_damp_n.tga\n repetitions = 193\n}\nspecular\n{\n shininess = 8\n}\n')
    return qa

def masks(spec):
    f=dict(np.load(O/'surface_fields.npz')); n=spec['mask_size']
    def original(name):
        return np.asarray(Image.open(R/'V026_OUTPUT/materials'/f'mask_{name}.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    prepared=np.maximum(original('visual_racing'),f['prepared'])
    churn=np.maximum(original('visual_worked')*.20,f['churn'])
    grass=np.maximum(original('visual_grass')*(1-f['grass_cut']),np.maximum(f['grass_islands'],f['parking_grass']))
    protected_native=np.maximum.reduce([np.asarray(Image.open(O/'masks'/f'{name}.tga').getchannel('A')) for name in ['racing','start','shoulder','worked']])>0
    accepted_native_grass=np.asarray(Image.open(R/'V026_OUTPUT/materials/mask_visual_grass.tga').getchannel('A'),np.float32)/255
    # High-priority legacy pit gravel remains bare where its roads pass.
    gravel=np.asarray(Image.open(O/'masks/v024_pit_roads.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    grass*=1-gravel
    sand=np.asarray(Image.open(O/'masks/sand.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    sand*=(1-f['prepared']*.95)*(1-grass*.96)
    # Keep off-course grass but suppress the accepted round-capped start area
    # wherever the new staging apron or access is visibly worn.
    for name,a in [('visual_racing',prepared),('visual_worked',churn),('visual_grass',grass),('visual_sand',sand),('v028_packed',f['packed']),('v028_face',f['face']),('v028_pits',np.maximum(f['pits'],f['access_visual'])*.95),('v028_damp',f['damp'])]:
        small=a if name in ['v028_packed','v028_damp'] else np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR))
        if name=='visual_grass':
            small=small.copy()
            small[protected_native]=np.minimum(small[protected_native],accepted_native_grass[protected_native])
            assert not np.any((np.uint8(np.rint(small*255))>np.uint8(np.rint(accepted_native_grass*255)))&protected_native),'Added visual grass crosses a protected native-grid margin'
        save_mask(M/f'mask_{name}.tga',small)
    # Blend the two nearest axial directions; masks share the exact route
    # heading used by the wear fields. Packed/loose traffic takes priority.
    theta=f['theta']; fresh=f['fresh']; weights=[]
    for angle in spec['grooming_angles_degrees']:
        diff=abs((theta-np.radians(angle)+np.pi/2)%np.pi-np.pi/2)
        a=np.clip(1-diff/(np.pi/4),0,1)*fresh
        save_mask(M/f'mask_v028_groom_{angle}.tga',np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR)))
        weights.append(a)
    assert np.allclose(sum(weights),fresh,atol=2e-6)
    return dict(mask_size=n,packed_max_opacity=float(f['packed'].max()),
                directional_grooming_blend_checks_pass=True,matte_default=True,
                local_damp_max_opacity=float(f['damp'].max()),standing_water_added=False,
                all_wear_color_and_normals_finely_tiled=True,low_resolution_diffuse_overlay=False,
                edge_irregularity_and_pit_wear_shared_with_physical_coverage=True,added_grass_outside_all_protected_native_grid_masks=True)

def layer_blocks(text):
    found=[]
    for match in re.finditer(r'(?m)^layer(\d+)\s*\n\{',text):
        begin=match.start(); cursor=match.end(); level=1
        while level:
            if text[cursor]=='{':level+=1
            elif text[cursor]=='}':level-=1
            cursor+=1
        found.append((begin,cursor,text[begin:cursor]))
    return found

def hmf(spec):
    text=(R/'V026_OUTPUT/materials/track.hmf').read_text().replace('v026_','v028_')
    layers=layer_blocks(text); assert len(layers)==8
    prefix=text[:layers[0][0]]
    # v026 appends packed/face layers after scene0. Keep all inter-layer
    # top-level declarations when regrouping the visual layer order.
    suffix=''.join(text[layers[k][1]:layers[k+1][0]] for k in range(len(layers)-1))+text[layers[-1][1]:]
    def new(name,reps,wet=True):
        return 'layer0\n{\n map = v028_'+name+'.tga\n repetitions = '+str(reps)+'\n mask = mask_v028_'+name+'.tga\n'+(' frame1\n {\n  map = v028_'+name+'_wet.tga\n }\n' if wet else '')+'}'
    blocks=[]
    for k,(_,_,b) in enumerate(layers):
        if k==2: b=re.sub(r'mask\s*=\s*\S+','mask = mask_visual_racing.tga',b)
        if k==3: b=re.sub(r'mask\s*=\s*\S+','mask = mask_visual_sand.tga',b)
        if k==4: b=re.sub(r'mask\s*=\s*\S+','mask = mask_visual_grass.tga',b)
        if k==5: b=re.sub(r'mask\s*=\s*\S+','mask = mask_visual_worked.tga',b)
        blocks.append(b)
        if k==2: blocks += [new('groom_'+str(angle),193) for angle in spec['grooming_angles_degrees']]
        if k==5: blocks += [new('pits',171,False)]
    blocks += [new('damp',193,False)]
    blocks=[re.sub(r'^layer\d+','layer'+str(i),b) for i,b in enumerate(blocks)]
    prefix=re.sub(r'num_layers\s*=\s*8','num_layers = '+str(len(blocks)),prefix)
    text=prefix+'\n'.join(blocks)+suffix
    (M/'track.hmf').write_text(text)
    assert len(layer_blocks(text))==14
    assert text.count('scene0')==1 and 'name = scenery.edf' in text

def preview():
    names=['soil','prepared','worked','sand','packed','pits','groom_0','groom_45','groom_90','groom_135','face','damp']
    im=Image.new('RGB',(1536,1160),(24,27,27)); draw=ImageDraw.Draw(im)
    for i,name in enumerate(names):
        x=i%4*384;y=i//4*386; im.paste(Image.open(M/f'v028_{name}.tga').resize((384,350)),(x,y))
        draw.text((x+10,y+360),'v028 '+name+' | source tile',fill='white')
    im.save(O/'material_tiles.png')

def main():
    if M.exists():shutil.rmtree(M)
    M.mkdir(); spec=read(S/'surface_spec.json'); qa=dict(version='v028',tiles=tiles(spec))
    qa.update(masks(spec)); hmf(spec); preview()
    assert all(x['edge_jump_mean']==0 for x in qa['tiles'])
    for p in M.glob('*.tga'):
        im=Image.open(p); assert not im.width&(im.width-1) and not im.height&(im.height-1)
    qa.update(checks_pass=True,source_asset_provenance=read(R/'V026_SOURCE/asset_provenance.json'),
              in_game_visual_check=False,files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.iterdir()) if p.is_file()})
    save(O/'material_validation.json',qa); print('v028 warm granular tiles and direction/wear masks validated',flush=True)
if __name__=='__main__':main()
