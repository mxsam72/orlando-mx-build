"""Fine tiled soil, directional grooming and shared local riding-line masks."""
import re, shutil
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from v025_materials import normals, save_mask
from v027_common import *

def tiles(spec):
    # Reuse the accepted granular texture process and its verified original
    # source bitmaps. This does not alter a historical generator or source asset.
    import v026_materials as granular
    granular.M=M
    qa=granular.tiles(spec)
    for p in list(M.glob('v026_*')):
        target=M/p.name.replace('v026_','v027_',1)
        if p.suffix=='.shd': target.write_text(p.read_text().replace('v026_','v027_')) ; p.unlink()
        else: p.rename(target)
    soil=np.asarray(Image.open(M/'v027_soil.tga').convert('RGB'),float)
    pits=np.clip(soil-soil.mean(axis=(0,1))+spec['palette']['pits'],0,255)
    pits=np.uint8(np.rint(pits)); Image.fromarray(pits).save(M/'v027_pits.tga')
    shutil.copy2(M/'v027_soil_n.tga',M/'v027_pits_n.tga')
    (M/'v027_pits.shd').write_text('bump\n{\n map = v027_pits_n.tga\n repetitions = 171\n}\nspecular\n{\n shininess = 8\n}\n')
    base=np.asarray(Image.open(M/'v027_prepared.tga').convert('RGB'),float); n=len(base)
    yy,xx=np.meshgrid(np.arange(n)/n,np.arange(n)/n,indexing='ij')
    lum=base.mean(axis=2); grain=gaussian_filter(lum,.8,mode='wrap')-gaussian_filter(lum,14,mode='wrap')
    grain/=max(float(grain.std()),1.)
    for angle,(kx,ky) in zip(spec['grooming_angles_degrees'],[(0,-12),(-8,-8),(-12,0),(-8,8)]):
        phase=2*np.pi*(kx*xx+ky*yy)+.18*np.sin(2*np.pi*(xx+yy))+.10*np.sin(2*np.pi*(3*xx-2*yy))
        grooves=np.sin(phase)*.72+np.sin(phase*2+.4)*.14
        h=grooves*spec['grooming_height_amplitude_m']+grain*.0016
        h[[0,-1],:]=h[[0,-1],:].mean(axis=0); h[:,[0,-1]]=h[:,[0,-1]].mean(axis=1)[:,None]
        rgb=np.clip(base+grooves[...,None]*2.0,0,255)
        rgb[[0,-1],:]=rgb[[0,-1],:].mean(axis=0); rgb[:,[0,-1]]=rgb[:,[0,-1]].mean(axis=1)[:,None]
        stem=f'v027_groom_{angle}'; ar=np.uint8(np.rint(rgb))
        Image.fromarray(ar).save(M/(stem+'.tga')); Image.fromarray(np.uint8(np.rint(ar*.85))).save(M/(stem+'_wet.tga'))
        Image.fromarray(normals(h,(SIZE/spec['repetitions']['prepared'])/n,1.,2)).save(M/(stem+'_n.tga'))
        for wet in ['', '_wet']:
            (M/(stem+wet+'.shd')).write_text(f'bump\n{{\n map = {stem}_n.tga\n repetitions = {spec["repetitions"]["prepared"]}\n}}\nspecular\n{{\n shininess = 8\n}}\n')
        qa.append(dict(material=stem,world_direction_deg=angle,world_groove_spacing_m=(SIZE/spec['repetitions']['prepared'])/np.hypot(kx,ky),normal_height_amplitude_m=spec['grooming_height_amplitude_m'],edge_jump_mean=float(abs(ar[0].astype(float)-ar[-1].astype(float)).mean())))
    Image.fromarray(np.uint8(np.rint(base*.79))).save(M/'v027_damp.tga')
    shutil.copy2(M/'v027_prepared_n.tga',M/'v027_damp_n.tga')
    (M/'v027_damp.shd').write_text('bump\n{\n map = v027_damp_n.tga\n repetitions = 193\n}\nspecular\n{\n shininess = 8\n}\n')
    return qa

def masks(spec):
    f=dict(np.load(O/'surface_fields.npz')); n=spec['mask_size']
    def original(name):
        return np.asarray(Image.open(R/'V026_OUTPUT/materials'/f'mask_{name}.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    prepared=np.maximum(original('visual_racing'),f['prepared'])
    churn=np.maximum(original('visual_worked')*.20,f['churn'])
    grass=original('visual_grass')*(1-f['grass_cut'])
    sand=np.asarray(Image.open(O/'masks/sand.tga').getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255
    sand*=1-f['prepared']*.95
    # Keep off-course grass but suppress the accepted round-capped start area
    # wherever the new staging apron or access is visibly worn.
    for name,a in [('visual_racing',prepared),('visual_worked',churn),('visual_grass',grass),('visual_sand',sand),('v027_packed',f['packed']),('v027_face',f['face']),('v027_pits',np.maximum(f['pits'],f['access_visual'])*.95),('v027_damp',f['damp'])]:
        small=a if name in ['v027_packed','v027_damp'] else np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR))
        save_mask(M/f'mask_{name}.tga',small)
    # Blend the two nearest axial directions; masks share the exact route
    # heading used by the wear fields. Packed/loose traffic takes priority.
    theta=f['theta']; fresh=f['fresh']; weights=[]
    for angle in spec['grooming_angles_degrees']:
        diff=abs((theta-np.radians(angle)+np.pi/2)%np.pi-np.pi/2)
        a=np.clip(1-diff/(np.pi/4),0,1)*fresh
        save_mask(M/f'mask_v027_groom_{angle}.tga',np.asarray(Image.fromarray(a).resize((2048,2048),Image.Resampling.BILINEAR)))
        weights.append(a)
    assert np.allclose(sum(weights),fresh,atol=2e-6)
    return dict(mask_size=n,packed_max_opacity=float(f['packed'].max()),
                directional_grooming_blend_checks_pass=True,matte_default=True,
                local_damp_max_opacity=float(f['damp'].max()),standing_water_added=False,
                all_wear_color_and_normals_finely_tiled=True,low_resolution_diffuse_overlay=False,
                edge_irregularity_and_pit_wear_shared_with_physical_coverage=True)

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
    text=(R/'V026_OUTPUT/materials/track.hmf').read_text().replace('v026_','v027_')
    layers=layer_blocks(text); assert len(layers)==8
    prefix=text[:layers[0][0]]
    # v026 appends packed/face layers after scene0. Keep all inter-layer
    # top-level declarations when regrouping the visual layer order.
    suffix=''.join(text[layers[k][1]:layers[k+1][0]] for k in range(len(layers)-1))+text[layers[-1][1]:]
    def new(name,reps,wet=True):
        return 'layer0\n{\n map = v027_'+name+'.tga\n repetitions = '+str(reps)+'\n mask = mask_v027_'+name+'.tga\n'+(' frame1\n {\n  map = v027_'+name+'_wet.tga\n }\n' if wet else '')+'}'
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
        x=i%4*384;y=i//4*386; im.paste(Image.open(M/f'v027_{name}.tga').resize((384,350)),(x,y))
        draw.text((x+10,y+360),'v027 '+name+' | source tile',fill='white')
    im.save(O/'material_tiles.png')

def main():
    if M.exists():shutil.rmtree(M)
    M.mkdir(); spec=read(S/'surface_spec.json'); qa=dict(version='v027',tiles=tiles(spec))
    qa.update(masks(spec)); hmf(spec); preview()
    assert all(x['edge_jump_mean']==0 for x in qa['tiles'])
    for p in M.glob('*.tga'):
        im=Image.open(p); assert not im.width&(im.width-1) and not im.height&(im.height-1)
    qa.update(checks_pass=True,source_asset_provenance=read(R/'V026_SOURCE/asset_provenance.json'),
              in_game_visual_check=False,files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.iterdir()) if p.is_file()})
    save(O/'material_validation.json',qa); print('v027 warm granular tiles and direction/wear masks validated',flush=True)
if __name__=='__main__':main()
