"""Generate the isolated Bushnell source foundation; not native compilation."""
from pathlib import Path
import csv,hashlib,json,math,re
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def validate_route(points):
 p=np.asarray(points,float)
 if p.ndim!=2 or p.shape[1]!=2 or len(p)<4:raise ValueError('Expected east/north closed route.')
 if not np.isfinite(p).all():raise ValueError('Non-finite route position.')
 if np.linalg.norm(p[0]-p[-1])>.001:raise ValueError('Approved route is open; do not invent a closing line.')
 if np.any(np.linalg.norm(np.diff(p,axis=0),axis=1)<1e-6):raise ValueError('Duplicate adjacent vertices.')
 return p

def load_project():
 c=json.loads((ROOT/'project.json').read_text())
 if c['project_id']!='bushnell-mx' or c['project_root']!='BUSHNELL':raise ValueError('Wrong project identity.')
 path=ROOT/c['approved_layout']
 if digest(path)!=c['approved_layout_sha256']:raise ValueError('Approved route checksum changed; version the change explicitly.')
 layout=json.loads(path.read_text());return c,layout,validate_route(layout['points'])

def world_origin(points,size):return (points.min(axis=0)+points.max(axis=0))/2-size/2

def local_to_game(points,origin):return np.asarray(points,float)-np.asarray(origin)

def game_to_pixel(points,size,n):
 p=np.asarray(points,float)
 return np.column_stack((p[:,0]/size*(n-1),(size-p[:,1])/size*(n-1)))

def sample_route(p,spacing=.5):
 arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
 s=np.linspace(0,arc[-1],math.ceil(arc[-1]/spacing)+1)
 return s,np.column_stack([np.interp(s,arc,p[:,i]) for i in range(2)])

def preview(c,layout,p,path):
 fig,ax=plt.subplots(figsize=(7.5,10),facecolor='#fafaf7');ax.set_facecolor('#fafaf7')
 bounds=np.array([p.min(axis=0)-15,p.max(axis=0)+15])
 ax.set(xlim=bounds[:,0],ylim=bounds[:,1],aspect='equal',xlabel='East from GPS reference (m)',ylabel='North from GPS reference (m)');ax.grid(color='#e1e6df',lw=.7)
 fig.canvas.draw();scale=abs(ax.transData.transform((1,0))[0]-ax.transData.transform((0,0))[0])*72/fig.dpi
 ax.plot(p[:,0],p[:,1],color='#b99b73',lw=c['corridor']['width_m']*scale,solid_joinstyle='round',solid_capstyle='round',zorder=2)
 colors=['#0072B2','#D55E00','#009E73','#B34C8A','#6F42C1','#9C5927','#D12F62','#4B5563']
 for r in layout['source_ranges']:
  q=p[r['start_index']:r['end_index']+1];color=colors[r['video']-1] if 'video' in r else '#B58300';ax.plot(q[:,0],q[:,1],color=color,lw=1.7,zorder=3)
 labels={1:(-12.6,-3),2:(-27,43),3:(-19,109),4:(.5,-39),5:(66,3),6:(-6,119),7:(-41,51),8:(-17,-60)}
 for n,xy in labels.items():ax.text(*xy,str(n),ha='center',va='center',fontsize=10,color=colors[n-1],bbox=dict(boxstyle='circle,pad=.2',fc='white',ec=colors[n-1]),zorder=4)
 ax.annotate('N',xy=(61,120),xytext=(61,103),ha='center',arrowprops={'arrowstyle':'-|>','color':'#183a2a'},color='#183a2a')
 ax.set_title('BUSHNELL MX / v001 source foundation\nApproved route - provisional 8 m corridor',fontsize=15,color='#183a2a',fontweight='bold',pad=16)
 fig.text(.5,.033,'Flat authoring base. Jump heights, profiles, scenery and local widths are not yet authored.',ha='center',fontsize=8,color='#5b6b62');fig.subplots_adjust(bottom=.10,top=.90)
 fig.savefig(path.with_suffix('.svg'),metadata={'Date':None});fig.savefig(path.with_suffix('.png'),dpi=150);plt.close(fig)

def main():
 c,layout,route=load_project();t=c['terrain'];size=t['size_m'];n=t['samples']
 if n<257 or (n-1)&(n-2):raise ValueError('Heightmap nodes must be a power of two plus one.')
 origin=world_origin(route,size);game=local_to_game(route,origin)
 if np.any(game<20) or np.any(game>size-20):raise ValueError('Route must fit inside a 20 m border.')
 out=ROOT/'build'/c['version'];out.mkdir(parents=True,exist_ok=True);pre=ROOT/'previews';pre.mkdir(exist_ok=True)
 s,q=sample_route(route);g=local_to_game(q,origin)
 with (out/'centerline.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['station_m','local_east_m','local_north_m','game_x_m','game_z_m']);w.writerows(np.round(np.c_[s,q,g],5))
 axes=np.linspace(0,size,n);distance=np.empty((n,n),np.float32);tree=cKDTree(g[:-1])
 for row in range(0,n,64):
  zz,xx=np.meshgrid(size-axes[row:row+64],axes,indexing='ij');d=tree.query(np.c_[xx.ravel(),zz.ravel()],workers=2)[0];distance[row:row+len(xx)]=d.reshape(xx.shape)
 width=c['corridor']['width_m'];shoulder=c['corridor']['shoulder_m'];weight=np.clip((width/2+shoulder-distance)/shoulder,0,1);weight=weight*weight*(3-2*weight)
 value=round(t['authoring_base_height_m']/t['native_height_scale_m']*65535);raw=np.full((n,n),value,dtype='<u2');raw.tofile(out/'terrain.raw');Image.fromarray(raw).save(out/'heightmap_16bit.png')
 mask=Image.fromarray(np.uint8(weight*255)).resize((n-1,n-1),Image.Resampling.BILINEAR);mask.save(out/'mask_racing.png');rgba=Image.new('RGBA',mask.size,'white');rgba.putalpha(mask);rgba.save(out/'mask_racing.tga')
 rgb=np.uint8(np.array([185,175,140])[None,None,:]*(1-weight[:,:,None])+np.array([132,106,79])[None,None,:]*weight[:,:,None]);base=Image.fromarray(rgb).resize((n-1,n-1),Image.Resampling.LANCZOS);base.save(out/'basemap.png');base.save(out/'basemap.tga')
 rng=np.random.default_rng(225232);noise=rng.normal(0,3,(512,512,1))
 for name,color in [('soil',(163,139,108)),('prepared',(132,106,79))]:Image.fromarray(np.uint8(np.clip(np.array(color)+noise,0,255))).save(out/(name+'.tga'))
 common=f'samples_x = {n}\nsamples_z = {n}\ndata = terrain.raw\nsize_x = {size:g}\nsize_z = {size:g}\nscale = {t["native_height_scale_m"]:g}\n'
 (out/'track.hmf').write_text(common+'num_layers = 3\nlayer0\n{\n map = basemap.tga\n repetitions = 1\n}\nlayer1\n{\n map = soil.tga\n repetitions = 96\n thickness = 0.03\n}\nlayer2\n{\n map = prepared.tga\n repetitions = 96\n thickness = 0.025\n mask = mask_racing.tga\n}\n')
 (out/'track.tht').write_text(common+'num_material_layers = 2\nmaterial_layer0\n{\n material = compact soil\n}\nmaterial_layer1\n{\n material = soft soil\n thickness = 0.025\n mask = mask_racing.tga\n}\n')
 for file in [out/'track.hmf',out/'track.tht']:
  for name in re.findall(r'^\s*(?:map|mask|data)\s*=\s*(.+)$',file.read_text(),re.M):
   if not (out/name.strip()).is_file():raise ValueError(f'Missing native source reference: {name}')
 assert (out/'terrain.raw').stat().st_size==n*n*2
 assert np.array_equal(np.asarray(Image.open(out/'heightmap_16bit.png')),raw)
 pixel=game_to_pixel(game,size,n);assert np.all(pixel>=0) and np.all(pixel<=n-1)
 preview(c,layout,route,pre/'01_source_foundation')
 report={'project_id':c['project_id'],'version':c['version'],'stage':'source_foundation','approved_layout_sha256':digest(ROOT/c['approved_layout']),'loop_closure_m':float(np.linalg.norm(route[0]-route[-1])),'approximate_route_length_m':round(float(s[-1]),2),'length_basis':'GPS and user sketch; not surveyed','terrain_size_m':size,'native_samples':n,'sample_spacing_m':size/(n-1),'raw_bytes':raw.nbytes,'native_origin_local_east_north_m':origin.tolist(),'image_top_is_north':True,'provisional_corridor_width_m':width,'authored_jump_profiles':0,'gps_altitude_used':False,'physics_profile':'standard_game','native_compiled':False,'installable':False,'next_stage':'Author individual obstacle positions and estimated profiles from the eight clips.'}
 save(out/'validation.json',report);save(out/'manifest.json',{p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'});print(json.dumps(report,indent=2))
if __name__=='__main__':main()
