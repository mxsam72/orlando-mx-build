"""Actual native regolith color/normal files and route-following groom atlas."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
B=Path(__file__).resolve().parents[1]/'build'
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def mask(name,a):
 a=np.uint8(np.rint(np.clip(a,0,1)*255));Image.fromarray(np.dstack([np.full_like(a,255)]*3+[a])).save(B/name)
def normals(h,dx):
 gy,gx=np.gradient(h,dx);v=np.stack([-gx,-gy,np.ones_like(gx)],-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
 return np.dstack([np.uint8(np.rint(v*127.5+127.5)),np.zeros(h.shape,np.uint8)])
def shader(name,norm,reps):
 (B/(name+'.shd')).write_text(f'bump\n{{\n map = {norm}.tga\n repetitions = {reps}\n}}\nspecular\n{{\n shininess = 5\n}}\n',newline='\n')
def build(xy,s,norm):
 rng=np.random.default_rng(170020);n=2048;white=rng.normal(size=(n,n)).astype(np.float32);h=np.zeros_like(white)
 for sigma,amp in [(1,.0007),(3,.0014),(11,.0025),(48,.002)]:
  a=gaussian_filter(white,sigma,mode='wrap');a/=a.std();h+=a*amp
 # Irregular centimeter-scale clasts. Work in local patches to keep memory bounded.
 peb=np.zeros_like(h)
 for _ in range(250):
  px,py=rng.integers(0,n,2);radius=rng.uniform(4,24);r=int(radius*3);yy,xx=np.mgrid[-r:r+1,-r:r+1];v=np.exp(-(xx*xx+yy*yy)/radius**2)*rng.uniform(.002,.009)
  rows=(py+np.arange(-r,r+1))%n;cols=(px+np.arange(-r,r+1))%n;peb[np.ix_(rows,cols)]+=v
 h+=peb;grain=gaussian_filter(white,.6,mode='wrap');grain/=grain.std();broad=gaussian_filter(white,25,mode='wrap');broad/=broad.std();color=np.clip(116+grain*7+broad*4+peb*480,65,168)
 for name,adjust,relief in [('v002_regolith',0,1.),('v002_fine',-4,.55)]:
  rgb=np.uint8(np.repeat((color+adjust)[:,:,None],3,axis=2));Image.fromarray(rgb).save(B/(name+'.tga'));Image.fromarray(normals(h*relief,2/n)).save(B/(name+'_n.tga'));shader(name,name+'_n',800)
 # Separate native object shader: scenery UVs already express 2 m tiles.
 with Image.open(B/'v002_regolith.tga') as im:im.resize((1024,1024),Image.Resampling.BILINEAR).save(B/'v002_context.tga')
 with Image.open(B/'v002_regolith_n.tga') as im:im.resize((1024,1024),Image.Resampling.BILINEAR).save(B/'v002_context_n.tga')
 shader('v002_context','v002_context_n',1)
 n=4096;dx=1600/n;rgb=np.empty((n,n,3),np.uint8);relief=np.zeros((n,n),np.float32);coverage=np.empty((n,n),np.float32);tree=cKDTree(xy)
 tangent=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 for r0 in range(0,n,64):
  y=800-(np.arange(r0,r0+64)+.5)*dx;x=-800+(np.arange(n)+.5)*dx;xx,yy=np.meshgrid(x,y);pts=np.c_[xx.ravel(),yy.ravel()];dist,idx=tree.query(pts,workers=4);d=pts-xy[idx]
  lat=(d*norm[idx]).sum(1).reshape(xx.shape);st=(s[idx]+(d*tangent[idx]).sum(1)).reshape(xx.shape);cov=smooth((12-dist.reshape(xx.shape))/4)
  phase=(lat+.18*np.sin(st*.02)+.06*np.sin(st*.13))*2*np.pi;groom=np.sin(phase)*.006+np.sin(phase*2+.3)*.0015;wheel=np.zeros_like(groom)
  for lateral in [-4.4,-1.5,1.5,4.3]:wheel+=np.exp(-((lat-lateral-.22*np.sin(st*.018+lateral))/.48)**2)
  shade=109+2*np.sin(xx*.23+np.sin(yy*.09))+2*np.sin(yy*.31+xx*.04)+groom*450-wheel*4
  rgb[r0:r0+64]=np.uint8(np.clip(np.repeat(shade[:,:,None],3,axis=2),65,150));relief[r0:r0+64]=(groom-wheel*.008)*cov;coverage[r0:r0+64]=cov
 Image.fromarray(rgb).save(B/'v002_route.tga');Image.fromarray(normals(relief,dx)).save(B/'v002_route_n.tga');shader('v002_route','v002_route_n',1);mask('mask_v002_route.tga',coverage*.92);mask('mask_v002_grain.tga',coverage*.45)
 for name,c in [('v002_marker_white',(193,190,174)),('v002_marker_blue',(32,85,117)),('v002_rock',(112,110,105)),('v002_panel',(48,54,58)),('NOLIGHTING_moon_black',(0,0,0))]:Image.new('RGB',(64,64),c).save(B/(name+'.tga'))
 return dict(tile_m=2,tile_pixels=2048,route_atlas_pixels=4096,route_texel_m=dx,normal_specular_alpha=0,photographic_scan=False,physical_micro_relief=False)
