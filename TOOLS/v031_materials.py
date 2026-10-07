"""Twelve independent scanned soils, matched relief and broad dirt variation.

Scanned diffuse/normal/height/roughness maps are pinned in scan_catalog.json.
The engine uses the normal-map alpha as specular intensity, so measured
roughness is translated conservatively into that supported channel.
"""
import gc,re
from PIL import ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter,map_coordinates
from v031_common import *

def periodic(a,band=8):
    a=a.copy()
    d=(a[0].copy()-a[-1].copy())*.5
    for i in range(band):
        w=(1-i/band)**2
        a[i]-=d*w;a[-i-1]+=d*w
    d=(a[:,0].copy()-a[:,-1].copy())*.5
    for i in range(band):
        w=(1-i/band)**2
        a[:,i]-=d*w;a[:,-i-1]+=d*w
    value=(a[0]+a[-1])*.5;a[0]=value;a[-1]=value
    value=(a[:,0]+a[:,-1])*.5;a[:,0]=value;a[:,-1]=value
    return a

def norm_rgb(v):
    v=periodic(v)
    v/=np.maximum(np.linalg.norm(v,axis=2,keepdims=True),1e-6)
    return np.uint8(np.clip(np.rint((v+1)*127.5),0,255))

def source_maps(asset,catalog):
    a=next(a for a in catalog['assets'] if a['asset']==asset)
    for f in a['files'].values():
        p=SCANS/f['file'];assert p.stat().st_size==f['size'] and sha(p)==f['sha256']
    def image(kind,mode):
        return np.asarray(Image.open(SCANS/a['files'][kind]['file']).convert(mode),np.float32)
    rgb=image('Diffuse','RGB');normal=image('nor_gl','RGB')/127.5-1
    rough=image('Rough','L')/255
    ao=image('AO','L')/255 if 'AO' in a['files'] else np.ones((N,N),np.float32)
    height=np.asarray(Image.open(SCANS/a['files']['Displacement']['file']),np.float32)
    if height.ndim==3:height=height[...,0]
    lo,hi=np.percentile(height,[1,99]);height=np.clip((height-lo)/max(hi-lo,1e-6),0,1)
    assert rgb.shape==(N,N,3) and normal.shape==rgb.shape and height.shape==(N,N)
    return a,rgb,normal,rough,ao,height

def shade(rgb,normal,spec):
    n=normal/127.5-1;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-6)
    light=np.array([-.42,.28,.86]);light/=np.linalg.norm(light)
    nd=np.maximum(np.einsum('ijk,k->ij',n,light),0)
    lighting=.40+.68*nd
    return np.uint8(np.clip(rgb.astype(float)*lighting[...,None]+(nd**24*spec*1.4)[...,None],0,255))

def main():
    spec=read(S/'surface_spec.json');catalog=read(S/'scan_catalog.json');tiles=[]
    assert len(set(a['asset'] for a in catalog['assets']))>=13
    for family,config in spec['materials'].items():
        a,rgb,normal,rough,ao,height=source_maps(config['asset'],catalog)
        lum=np.einsum('ijk,k->ij',rgb,np.array([.2126,.7152,.0722],np.float32))
        chroma=rgb-lum[...,None]
        rgb=np.asarray(config['palette'],np.float32)+(lum-lum.mean())[...,None]*config['luminance_gain']+(chroma-chroma.mean(axis=(0,1)))*.32
        rgb*=.96+.04*ao[...,None]
        normal[...,:2]*=config['normal_strength'];normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-6)
        repetitions=int(round(SIZE/(a['dimensions_mm'][0]/1000)))
        spacing=(SIZE/repetitions)/N
        if family.startswith('groom_'):
            angle=int(family.split('_')[1]);yy,xx=np.mgrid[:N,:N]/N
            kx,ky={0:(0,14),45:(10,10),90:(14,0),135:(-10,10)}[angle]
            phase=2*np.pi*(kx*xx+ky*yy)+.18*np.sin(2*np.pi*(xx+yy))
            continuity=.30+.70*np.clip(gaussian_filter(height,9,mode='wrap')*1.3,0,1)
            ridge=(np.sin(phase)+.18*np.sin(2*phase+.5))*continuity
            relief=ridge*config['groove_height_m']
            gx=(np.roll(relief,-1,axis=1)-np.roll(relief,1,axis=1))/(2*spacing)
            gy=(np.roll(relief,-1,axis=0)-np.roll(relief,1,axis=0))/(2*spacing)
            normal=np.stack([normal[...,0]/np.maximum(normal[...,2],.20)-gx,normal[...,1]/np.maximum(normal[...,2],.20)+gy,np.ones_like(gx)],axis=2)
            normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-6)
            rgb+=ridge[...,None]*.95
        rgb=np.uint8(np.clip(np.rint(periodic(rgb)),0,255))
        rough=np.clip(periodic(rough),0,1)
        nrgb=norm_rgb(normal)
        dryspec=np.uint8(np.rint(3+13*(1-rough)**2))
        wetspec=np.uint8(np.rint(9+24*(1-rough)**1.8))
        drynormal=np.dstack([nrgb,dryspec]);wetnormal=np.dstack([nrgb,wetspec])
        wet=np.uint8(np.clip(np.rint(rgb.astype(float)*config.get('wet_factor',.79)),0,255))
        stem='v031_'+family
        for suffix,data in [('',rgb),('_wet',wet),('_n',drynormal),('_wet_n',wetnormal)]:image_file(Image.fromarray(data),M/(stem+suffix+'.tga'))
        for wet_state in (False,True):
            suffix='_wet' if wet_state else '';nmap=stem+suffix+'_n.tga'
            atomic(M/(stem+suffix+'.shd'),f'bump\n{{\n map = {nmap}\n repetitions = 0\n}}\nspecular\n{{\n shininess = {28 if wet_state else 15}\n}}\n'.encode())
        for data in (rgb,nrgb,dryspec,wetspec):
            assert np.array_equal(data[0],data[-1]) and np.array_equal(data[:,0],data[:,-1])
        clipped=((rgb==0)|(rgb==255)).mean();assert clipped<.002
        vectors=nrgb.astype(float)/127.5-1
        assert np.max(np.abs(np.linalg.norm(vectors,axis=2)-1))<.014
        assert dryspec.max()<=16 and wetspec.max()<=33
        tiles.append(dict(material=stem,asset=a['asset'],source_page=a['source_page'],authors=a['authors'],license=a['license'],size=[N,N],physical_tile_width_m=SIZE/repetitions,repetitions=repetitions,normal_strength=config['normal_strength'],matched_photographic_color_normal_height_roughness=True,source_diffuse_sha256=a['files']['Diffuse']['sha256'],source_normal_sha256=a['files']['nor_gl']['sha256'],source_height_sha256=a['files']['Displacement']['sha256'],mean_rgb=rgb.mean(axis=(0,1)).round(2).tolist(),dry_specular_alpha_range=[int(dryspec.min()),int(dryspec.max())],wet_specular_alpha_range=[int(wetspec.min()),int(wetspec.max())],edge_jump=0,clipped_fraction=float(clipped),height_does_not_displace_physical_terrain=True))
        print('Authored scanned soil:',family,'from',a['asset'],flush=True)
        del rgb,normal,nrgb,rough,ao,height,wet,drynormal,wetnormal;gc.collect()
    assert len(tiles)==12 and len({t['source_diffuse_sha256'] for t in tiles})==12
    text=(BASE/'materials/track.hmf').read_text().replace('v030','v031')
    for tile in tiles:
        pattern=r'(map = '+tile['material']+r'\.tga\s+repetitions = )\d+'
        text,count=re.subn(pattern,lambda m:m[1]+str(tile['repetitions']),text)
        assert count==1,tile['material']
    for _,_,block in layer_blocks(text):
        if 'map = v031_damp.tga' in block and 'frame1' not in block:
            text=text.replace(block,block[:-1]+' frame1\n {\n  map = v031_damp_wet.tga\n }\n}')
    # A gentle, single world-space scan layer breaks up repeated micro tiles.
    a,rgb,_,_,_,_=source_maps('dirt_aerial_02',catalog)
    macro_n=4096;yy,xx=np.mgrid[:macro_n,:macro_n].astype(np.float32)
    rng=np.random.default_rng(spec['seed'])
    field=rng.normal(size=(64,64)).astype(np.float32)
    warp=map_coordinates(gaussian_filter(field,2,mode='wrap'),[yy/64,xx/64],order=1,mode='wrap')*650
    ux=(xx/macro_n*SIZE/20*N+warp)%N;vy=(yy/macro_n*SIZE/20*N+warp*.73)%N
    smooth=gaussian_filter(rgb,(12,12,0),mode='wrap');center=smooth.mean(axis=(0,1))
    sampled=np.stack([map_coordinates(smooth[...,c],[vy,ux],order=1,mode='wrap') for c in range(3)],axis=-1)
    macro=np.uint8(np.clip(np.rint((sampled-center)*.55+[98,85,72]),0,255))
    image_file(Image.fromarray(macro),M/'v031_macro.tga')
    grass=np.asarray(Image.open(M/'mask_visual_grass.tga').getchannel('A'))
    assert grass.shape==(N,N)
    yy,xx=np.mgrid[:N,:N].astype(np.float32);X=(xx+.5)/N*SIZE;Z=SIZE-(yy+.5)/N*SIZE
    scope=(X>=208)&(X<=467)&(Z>=155)&(Z<=442)&~((X<373)&(Z<=174))
    weight=np.uint8(np.rint(24*gaussian_filter(scope.astype(float),3)))
    weight[(grass>0)|~scope]=0
    mask=np.zeros((N,N,4),np.uint8);mask[...,:3]=255;mask[...,3]=weight
    image_file(Image.fromarray(mask),M/'mask_v031_macro.tga')
    assert not np.any(weight[grass>0]) and not np.any(weight[(X<373)&(Z<=174)])
    count=len(layer_blocks(text));assert count==14
    text=re.sub(r'num_layers\s*=\s*14','num_layers = 15',text,count=1)
    text+=f'\nlayer{count}\n{{\n map = v031_macro.tga\n repetitions = 1\n mask = mask_v031_macro.tga\n}}\n'
    atomic(M/'track.hmf',text.encode())
    dry_active={re.search(r'map\s*=\s*(\S+)',block)[1] for _,_,block in layer_blocks(text)}
    assert all(t['material']+'.tga' in dry_active for t in tiles)
    occupancy={}
    for _,_,block in layer_blocks(text):
        name=re.search(r'map\s*=\s*(\S+)',block)[1]
        if name.removesuffix('.tga') not in {t['material'] for t in tiles}:continue
        mask=re.search(r'(?m)^\s*mask\s*=\s*(\S+)',block)
        samples=int(np.count_nonzero(np.asarray(Image.open(M/mask[1]).getchannel('A')))) if mask else N*N
        assert samples>0,'Unused soil material: '+name
        occupancy[name]=samples
    material_files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(M.iterdir()) if p.suffix in ('.tga','.shd','.hmf')}
    qa=dict(version='v031',checks_pass=True,tiles=tiles,independent_scanned_soil_images=13,independent_detail_materials=12,macro_source='dirt_aerial_02',macro_strength_max=int(weight.max()),macro_does_not_overlay_grass_or_pits=True,native_author_layers=15,native_layers_with_legacy_gravel=16,normal_maps_use_scanned_GL_vectors=True,roughness_translated_to_supported_specular_alpha=True,wet_materials_have_separate_specular_response=True,grass_tile_and_masks_unchanged=True,native_supported_features_only=True,in_game_visual_check=False,files=material_files)
    qa['active_soil_mask_samples']=occupancy
    save(O/'material_validation.json',qa)
    preview=Image.new('RGB',(1600,1410),(30,29,27));draw=ImageDraw.Draw(preview)
    try:font=ImageFont.truetype('DejaVuSans.ttf',19)
    except OSError:font=ImageFont.load_default()
    draw.text((20,14),'v031 | 12 independent scanned soil materials + broad dirt variation',fill='white',font=font)
    draw.text((20,42),'Color, scanned relief and roughness maps | software material preview, not in-game screenshots',fill=(194,190,182),font=font)
    for i,tile in enumerate(tiles):
        x=i%4*400;y=90+i//4*440;stem=tile['material']
        rgb=np.asarray(Image.open(M/(stem+'.tga')).convert('RGB').resize((392,364)))
        normal=np.asarray(Image.open(M/(stem+'_n.tga')).convert('RGBA').resize((392,364)))
        preview.paste(Image.fromarray(shade(rgb,normal[...,:3].astype(float),normal[...,3].astype(float))),(x+4,y))
        draw.text((x+10,y+374),stem.removeprefix('v031_').replace('_',' '),fill='white',font=font)
        draw.text((x+10,y+402),tile['asset'],fill=(186,181,171),font=font)
    save_png(preview,O/'material_tiles.png')
    print('12 independent scanned materials and protected broad variation validated.',flush=True)

if __name__=='__main__':main()
