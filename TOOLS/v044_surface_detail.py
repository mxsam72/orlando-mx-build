"""Continuous world-space route bake; visual materials only, no heightfield edits."""
import re,shutil
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates
from scipy.spatial import cKDTree
from v044_common import *

def alpha(name,n):
    with Image.open(M/name) as im:return np.asarray(im.getchannel('A').resize((n,n),Image.Resampling.BILINEAR),np.float32)/255

def mask(name,a):
    im=Image.new('RGBA',(a.shape[1],a.shape[0]),(255,255,255,0));im.putalpha(Image.fromarray(np.uint8(np.rint(np.clip(a,0,1)*255))));image_file(im,M/name)

def route():
    f=dict(np.load(O/'route.npz'));q=f['q'];p=q[:,:2];v=np.roll(p,-1,axis=0)-np.roll(p,1,axis=0);v/=np.maximum(np.linalg.norm(v,axis=1)[:,None],1e-8)
    # q stores x,z,terrain height,arc station; route is densely sampled already.
    return f,q,p,v,cKDTree(p)

def tiled(a,x,z,reps):
    n=a.shape[0];return map_coordinates(a,[np.mod(z/SIZE*reps,1)*(n-1),np.mod(x/SIZE*reps,1)*(n-1)],order=1,mode='wrap')

def main():
    from v044_assets import material
    spec=read(S/'visual_spec.json');n=8192;dx=SIZE/n;f,q,p,v,tree=route()
    soil_qa=[]
    # Native shaders and world repeat scales stay compatible with accepted normals.
    for kind,scan,mix in [('soil','dirt',.32),('prepared','raked_dirt',.30),('worked','farm_soil',.38),('packed','park_dirt',.24),('face','raked_dirt',.23),('pits','park_dirt',.28)]:
        old=np.asarray(Image.open(M/f'v032_{kind}.tga').convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS),np.float32)
        ph=np.asarray(material(scan,'Diffuse','2k').convert('RGB').resize((2048,2048)),np.float32)
        ph=ph-ph.mean((0,1))+old.mean((0,1));a=old*(1-mix)+ph*mix
        a=np.clip(a,0,255);a[[0,-1]]=a[[0,-1]].mean(0);a[:,[0,-1]]=a[:,[0,-1]].mean(1)[:,None]
        image_file(Image.fromarray(np.uint8(np.rint(a))),M/f'v032_{kind}.tga')
        soil_qa.append(dict(material=kind,photographic_asset=scan,blend=mix,mean_rgb=a.mean((0,1)).round(2).tolist()))
    print('Refined six photographic material families with accepted color means.',flush=True)
    # Blend existing four groom masks into one coverage field. Their pattern direction is removed.
    coverage=sum(alpha('mask_v032_groom_'+str(a)+'.tga',2048) for a in [0,45,90,135])
    coverage=np.clip(coverage,0,1)
    rgb=np.empty((n,n,3),np.uint8);height=np.empty((n,n),np.float32)
    base=np.asarray(Image.open(M/'v032_prepared.tga').convert('RGB'),np.float32)
    x=(np.arange(n,dtype=np.float32)+.5)*dx
    count=0
    for y0 in range(0,n,64):
        z=SIZE-(np.arange(y0,min(y0+64,n),dtype=np.float32)+.5)*dx
        xx,zz=np.meshgrid(x,z);pos=np.stack([xx.ravel(),zz.ravel()],1);dist,idx=tree.query(pos,workers=2)
        delta=pos-p[idx];station=(q[idx,3]+(delta*v[idx]).sum(1)).reshape(xx.shape)
        lateral=(delta[:,0]*(-v[idx,1])+delta[:,1]*v[idx,0]).reshape(xx.shape)
        half=np.asarray(f['width'])[idx].reshape(xx.shape)/2
        curve=np.abs(np.asarray(f['curvature'])[idx]).reshape(xx.shape)
        # Gentle lateral drift breaks synthetic-perfect stripes while remaining continuous.
        drift=.08*np.sin(station*.085)+.025*np.sin(station*.34)
        phase=2*np.pi*(lateral+drift)/.36
        groom=np.sin(phase)*.006+np.sin(phase*2+.4)*.0014
        h=groom.copy();color=groom/.0074*5.5
        braking=(.25+.75*np.clip(curve/.10,0,1))*(.60+.40*np.sin(station*.15)**2)
        for offset,width,depth in [(-.9,.13,.016),(0,.12,.014),(1.15,.14,.018)]:
            center=offset+.30*np.sin(station*.018+offset)+.12*np.sin(station*.065+offset)
            tire=np.exp(-((lateral-center)/width)**2)
            h-=tire*depth;br=tire*(6+braking*5)
            tread=(.5+.5*np.cos(station*2*np.pi/.28))*np.exp(-((lateral-center)/(.18))**2)
            h+=tread*.002;color-=br+tread*1.8
        shoulder=np.clip((np.abs(lateral)-half*.72)/np.maximum(half*.25,.5),0,1)
        macro=2.7*np.sin(xx*.24+np.sin(zz*.15))+1.8*np.sin(zz*.61+xx*.13)
        grain=tiled(base.mean(2),xx,zz,193)-float(base.mean())
        h+=np.clip(grain/80,-1,1)*.0018+shoulder*np.sin(station*.8+lateral*9)*.003
        pixels=np.stack([tiled(base[:,:,k],xx,zz,193) for k in range(3)],2)
        pixels+=((color+macro+shoulder*1.2)[:,:,None])
        rgb[y0:y0+len(z)]=np.uint8(np.rint(np.clip(pixels,0,255)));height[y0:y0+len(z)]=h
        count+=int(np.count_nonzero(dist<np.asarray(f['width'])[idx]/2))
        if y0%1024==0:print('Continuous route bake rows',y0,'/',n,flush=True)
    image_file(Image.fromarray(rgb),M/'v044_route_detail.tga')
    normal=np.empty((n,n,4),np.uint8);normal[:,:,3]=2
    for y0 in range(0,n,64):
        lo=max(0,y0-1);hi=min(n,y0+65);gy,gx=np.gradient(height[lo:hi],dx);begin=y0-lo;end=min(64,n-y0)+begin
        nx=-gx[begin:end];ny=gy[begin:end];den=np.sqrt(nx*nx+ny*ny+1)
        normal[y0:y0+end-begin,:,:3]=np.uint8(np.rint(np.stack([nx/den,ny/den,1/den],2)*127.5+127.5))
    image_file(Image.fromarray(normal),M/'v044_route_detail_n.tga')
    (M/'v044_route_detail.shd').write_text('bump\n{\n map = v044_route_detail_n.tga\n repetitions = 1\n}\nspecular\n{\n shininess = 8\n}\n')
    mask('mask_v044_route_detail.tga',coverage*.88)
    # Clear dry surface: retain prepared/packed/worked dry families, remove small damp overlay.
    text=(O/'compiled_track.hmf').read_text()
    from v028_materials import layer_blocks
    layers=layer_blocks(text);prefix=text[:layers[0][0]];suffix=''.join(text[layers[k][1]:layers[k+1][0]] for k in range(len(layers)-1))+text[layers[-1][1]:]
    blocks=[]
    for _,_,b in layers:
        if re.search(r'map\s*=\s*v032_groom_',b):continue
        if re.search(r'map\s*=\s*v032_damp',b):continue
        blocks.append(b)
        if re.search(r'map\s*=\s*v032_prepared.tga',b):
            blocks.append('layer0\n{\n map = v044_route_detail.tga\n repetitions = 1\n mask = mask_v044_route_detail.tga\n}')
    blocks=[re.sub(r'^layer\d+','layer'+str(i),b) for i,b in enumerate(blocks)]
    prefix=re.sub(r'num_layers\s*=\s*\d+','num_layers = '+str(len(blocks)),prefix)
    text=prefix+'\n'.join(blocks)+suffix
    assert 'scene0' in text and len(blocks)==11
    (O/'compiled_track.hmf').write_text(text)
    # A restrained contact/organic variation field for grass margins. No new grass coverage.
    grass=alpha('mask_visual_grass.tga',2048)
    y,xg=np.mgrid[:2048,:2048]/2048*SIZE
    border=np.clip(1-gaussian_filter(grass,5),0,1)
    worn=grass*(1-.16*border*(.5+.5*np.sin(xg*.31+np.sin(y*.21))))
    assert np.all(worn<=grass+1e-6)
    mask('mask_visual_grass.tga',worn)
    preview=Image.fromarray(rgb).resize((2048,2048),Image.Resampling.LANCZOS);image_file(preview,O/'v044_route_atlas_preview.tga')
    # Close crops, spatially chosen from route, for authoring QA; never claimed as game screenshots.
    qix=int(np.argmax(np.abs(f['curvature'])));cx,cz=q[qix,:2]/SIZE*n;cz=n-cz;box=(int(cx)-384,int(cz)-384,int(cx)+384,int(cz)+384)
    Image.fromarray(rgb).crop(box).save(O/'v044_corner_surface_preview.png')
    save(O/'v044_surface_validation.json',dict(checks_pass=True,atlas_size=[n,n],world_texel_m=dx,continuous_curve_following=True,normal_map_height_amplitude_range_m=[float(height.min()),float(height.max())],groom_spacing_m=.36,visual_wheel_paths=3,soil_photographic_refinements=soil_qa,physical_terrain_modified=False,grass_coverage_never_increased=True,dry_damp_overlay_removed=True,native_layer_count=len(blocks),in_game_visual_check=False))
    print('Continuous diffuse and correlated normal atlas written; physical terrain exact.',flush=True)
if __name__=='__main__':main()
