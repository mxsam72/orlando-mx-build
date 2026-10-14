"""Matched source previews for the A/B/C geometry update; not game footage."""
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from v054_geometry import R,BASE,PREV,O,M,Layout,read,sha,save,ground
from v054_surfaces import source as baseline_source
import v049_previews as render

OUT=R/'BUILD/v054_review';CURRENT='v052'
def source(name,version):
 if CURRENT=='v054' and (M/name).is_file():return M/name
 return baseline_source(name)
class Terrain:
 def __init__(self,path):
  self.h=np.fromfile(path,'<u2').reshape(2049,2049).astype(np.float32)/65535*18;gy,self.gx=np.gradient(self.h,600/2048);self.gz=-gy
 def ground(self,x,z):return map_coordinates(self.h,[(600-z)/600*2048,x/600*2048],order=1,mode='nearest')
 def slope(self,x,z):
  c=[(600-z)/600*2048,x/600*2048];return map_coordinates(self.gx,c,order=1,mode='nearest'),map_coordinates(self.gz,c,order=1,mode='nearest')
def geometry_map():
 OUT.mkdir(parents=True,exist_ok=True);l=Layout();fig,ax=plt.subplots(figsize=(10,11));ax.set_facecolor('#eee8dd');fig.patch.set_facecolor('#eee8dd')
 ax.plot(l.old[:,0],l.old[:,1],color='#9e9382',lw=4,label='v052 main route');ax.plot(l.oldstart[:,0],l.oldstart[:,1],color='#c8b390',lw=4,label='v052 start')
 ax.plot(l.q[:,0],l.q[:,1],color='#5a3e2a',lw=2,label='v054 main route');ax.plot(l.start[:,0],l.start[:,1],color='#cc842e',lw=3,label='v054 start')
 for label,p in [('A',(412,312)),('B',(422,260)),('C',(199,293))]:ax.text(*p,label,fontsize=17,fontweight='bold')
 ax.set_xlim(190,443);ax.set_ylim(158,440);ax.set_aspect('equal');ax.set_xlabel('Game X (m)');ax.set_ylabel('Game Z (m)');ax.legend(loc='upper right',fontsize=10)
 ax.set_title('v054 A/B/C path revision over v052\nSource geometry comparison — not an in-game screenshot',fontsize=14);fig.tight_layout();fig.savefig(OUT/'v054_path_comparison.png',dpi=170);plt.close(fig)
 return l
def main():
 global CURRENT
 layout=geometry_map();render.OUT=OUT;render.source=source;rows=[]
 before=Terrain(BASE/'terrain.raw');after=Terrain(O/'terrain.raw')
 for label,box in [('start_and_A',(298.,246.,426.,325.)),('roller_entry_C',(193.,220.,265.,320.))]:
  frames=[]
  for version,sample in [('v052',before),('v054',after)]:
   CURRENT=version;render.O=PREV if version=='v052' else O;render.M=M;render.BOX=box;c,n=render.composite('v049',n=1400)
   x,z=np.meshgrid(np.linspace(box[0],box[2],1400),np.linspace(box[3],box[1],1400));hx,hz=sample.slope(x,z);normal=np.stack([-hx,-hz,np.ones_like(hx)],2);normal/=np.linalg.norm(normal,axis=2)[:,:,None];light=np.array([2,-7,10]);light=light/np.linalg.norm(light);shade=.5+.55*np.maximum(0,(normal*light).sum(2));rgb=np.uint8(np.clip(c.astype(float)*shade[:,:,None],0,255))
   im=Image.fromarray(rgb);d=ImageDraw.Draw(im);d.rectangle((0,0,1400,44),fill=(22,25,29));d.text((15,11),version+' '+label+' — terrain/material source preview; scenery omitted',font=render.font(20),fill='white')
   name=version+'_'+label+'.jpg';im.save(OUT/name,quality=95);frames.append(im);rows.append(dict(file=name,sha256=sha(OUT/name),world_box_xz_m=list(box)))
  sheet=Image.new('RGB',(2800,1400));sheet.paste(frames[0],(0,0));sheet.paste(frames[1],(1400,0));sheet.save(OUT/('comparison_'+label+'.jpg'),quality=94)
 # Matching viewpoint into the entry shows the bank opening on both sources.
 eye=np.array([382.,276.,float(after.ground(np.array([382.]),np.array([276.]))[0])+4.0]);target=[340.,278.,float(after.ground(np.array([340.]),np.array([278.]))[0])+.7]
 render.BOX=(315.,246.,417.,317.)
 for version,sample in [('v052',before),('v054',after)]:
  CURRENT=version;render.O=PREV if version=='v052' else O;c,n=render.composite('v049',n=1700);p=render.render(version,'start_merge',c,n,sample,eye,target,width=1200,height=750);rows.append(dict(file=p.name,sha256=sha(p)))
 save(OUT/'manifest.json',dict(version='v054',baseline='v052',source_only=True,in_game_captures=False,scenery_omitted=True,matched_lighting_and_cameras=True,renders=rows,geometry_file='v054_path_comparison.png',geometry_sha256=sha(OUT/'v054_path_comparison.png')))
 print('V054_PREVIEWS_READY',flush=True)
if __name__=='__main__':
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='geometry':geometry_map()
 else:main()
