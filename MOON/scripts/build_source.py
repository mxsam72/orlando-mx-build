"""Measured Moon terrain and authored half-gravity motocross source draft."""
from pathlib import Path
import hashlib,json,math
import numpy as np
import rasterio
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates,gaussian_filter,gaussian_filter1d,distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import LineString
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
R=Path(__file__).resolve().parents[1];S=R/'source';B=R/'build';P=R/'previews'
SIZE=1600.;N=2049;STEP=SIZE/(N-1);WIDTH=16.;G=4.905
CONTROL=np.array([[-430,-300],[-200,-320],[60,-300],[260,-350],[430,-200],[470,0],[370,140],[150,120],[90,220],[180,340],[0,430],[-240,400],[-420,300],[-360,120],[-200,90],[-140,-40],[-250,-160],[-440,-130],[-520,-210],[-430,-300]],float)
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dem_grid(filename,x,y,fill=False):
 with rasterio.open(S/filename) as ds:
  a=ds.read(1);invalid=a<-1e20
  if invalid.any():
   assert fill,'Missing measurements in riding area'
   a=a[tuple(distance_transform_edt(invalid,return_distances=False,return_indices=True))]
  m=json.loads((S/filename).with_suffix('.json').read_text());cx,cy=m['shorty_projected_xy_m']
  col=(x+cx-ds.transform.c)/ds.transform.a-.5;row=(y+cy-ds.transform.f)/ds.transform.e-.5
  assert col.min()>=0 and row.min()>=0 and col.max()<ds.width-1 and row.max()<ds.height-1
  return map_coordinates(a,[row,col],order=1,mode='nearest'),m

def route():
 knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(CONTROL,axis=0),axis=1))];spline=CubicSpline(knots,CONTROL,bc_type='periodic')
 dense=spline(np.linspace(0,knots[-1],20000));arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
 length=arc[-1];station=np.linspace(0,length,math.ceil(length/.5),endpoint=False)
 xy=np.c_[np.interp(station,arc,dense[:,0]),np.interp(station,arc,dense[:,1])]
 t=np.roll(xy,-1,axis=0)-np.roll(xy,1,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];n=np.c_[-t[:,1],t[:,0]]
 ds=length/len(station);dt=(np.roll(t,-1,axis=0)-np.roll(t,1,axis=0))/(2*ds);k=(dt*n).sum(1)
 z,_=dem_grid('shorty_2m.tif',xy[:,0],xy[:,1]);z=gaussian_filter1d(z,18/ds,mode='wrap')
 features=[];delta=np.zeros(len(station))
 for target in [250,730,1450,2200]:
  eligible=np.flatnonzero((abs(station-target)<110)&(abs(k)<.006))
  if not len(eligible):continue
  i=eligible[np.argmin(abs(station[eligible]-target))];s=float(station[i]);h=1.15;span=54.
  d=abs((station-s+length/2)%length-length/2);delta+=np.where(d<span/2,h*.5*(1+np.cos(np.pi*np.minimum(d,span/2)/(span/2))),0)
  features.append(dict(type='broad_rollover',station_m=round(s,2),height_m=h,length_m=span,max_added_grade=math.pi*h/span))
 return station,xy,t,n,k,z+delta,length,features

def main():
 B.mkdir(exist_ok=True);P.mkdir(exist_ok=True)
 s,xy,tangent,normal,curv,rz,length,features=route();line=LineString(np.vstack([xy,xy[0]]));assert line.is_simple
 x=np.linspace(-800,800,N,dtype=np.float32);y=x[::-1].copy();xx,yy=np.meshgrid(x,y);base,meta=dem_grid('shorty_2m.tif',xx,yy)
 distance,index=cKDTree(xy).query(np.c_[xx.ravel(),yy.ravel()],workers=4);distance=distance.reshape(N,N).astype(np.float32);index=index.reshape(N,N)
 lateral=(xx-xy[index,0])*normal[index,0]+(yy-xy[index,1])*normal[index,1]
 blend=np.clip((WIDTH/2+8-distance)/8,0,1);blend=blend*blend*(3-2*blend)
 outside=np.maximum(0,-np.sign(curv[index])*lateral);berm=np.clip(abs(curv[index])*90,0,1)*.85*np.clip((outside-3)/6,0,1)**2
 target=rz[index]+berm-.025*np.minimum(abs(lateral),WIDTH/2);height=(base*(1-blend)+target*blend).astype(np.float32)
 assert np.max(blend[np.hypot(xx,yy)<90])==0
 offset=float(math.floor(height.min())-1);scale=float(math.ceil(height.max()-offset)+1)
 raw=np.rint((height-offset)/scale*65535).astype('<u2');raw.tofile(B/'terrain.raw');Image.fromarray(raw).save(B/'heightmap_16bit.png')
 np.savez_compressed(B/'terrain_preview.npz',x=x[::2],y=y[::2],height=height[::2,::2]-offset,route_xy=xy.astype(np.float32),route_z=(rz-offset).astype(np.float32),offset=offset)
 context_x=np.arange(-11960,11961,40,dtype=np.float32);cx,cy=np.meshgrid(context_x,context_x[::-1]);context,_=dem_grid('valley_context_20m.tif',cx,cy,fill=True)
 radial=np.maximum(abs(cx),abs(cy));near=radial<1750;measured,_=dem_grid('shorty_2m.tif',cx[near],cy[near]);weight=np.clip((1750-radial[near])/250,0,1);context[near]=context[near]*(1-weight)+measured*weight
 np.savez_compressed(B/'context_preview.npz',x=context_x,y=context_x[::-1],height=context-offset)
 rng=np.random.default_rng(17017);noise=gaussian_filter(rng.normal(size=(N,N)).astype(np.float32),30);noise/=noise.std()
 grooming=.009*np.cos(lateral*2*np.pi/1.8)+.007*np.sin(lateral*2*np.pi/3.7)
 gray=np.clip(.46+noise*.018-blend*.035+grooming*blend,.25,.65);rgb=np.uint8(np.clip(np.stack([gray*1.015,gray,gray*.985],axis=-1)*255,0,255))
 Image.fromarray(rgb).save(B/'basemap.png');Image.fromarray(rgb).save(B/'basemap.tga')
 mask=np.uint8(blend*255);Image.fromarray(mask).save(B/'mask_racing.png');Image.fromarray(np.dstack([np.full_like(mask,255)]*3+[mask])).save(B/'mask_racing.tga')
 fine=rng.normal(size=(1024,1024)).astype(np.float32);grains=gaussian_filter(fine,1,mode='wrap');grains/=grains.std()
 relief=gaussian_filter(fine,2,mode='wrap')*.03+gaussian_filter(fine,12,mode='wrap')*.25
 for name,level in [('regolith',.49),('groomed',.42)]:
  a=np.uint8(np.clip(level+grains*.025,0,1)*255);im=Image.fromarray(np.stack([a,a,a],axis=-1));im.save(B/(name+'.tga'));im.save(B/(name+'.png'))
 gy,gx=np.gradient(relief,4/1024);normals=np.stack([-gx,-gy,np.ones_like(gx)],axis=-1);normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
 Image.fromarray(np.uint8(np.clip(normals*.5+.5,0,1)*255)).save(B/'regolith_n.tga')
 common=f'samples_x = {N}\nsamples_z = {N}\ndata = terrain.raw\nsize_x = 1600\nsize_z = 1600\nscale = {scale:g}\n'
 (B/'track.hmf').write_text(common+'num_layers = 3\nlayer0\n{\n map = basemap.tga\n repetitions = 1\n}\nlayer1\n{\n map = regolith.tga\n repetitions = 400\n thickness = 0.03\n}\nlayer2\n{\n map = groomed.tga\n repetitions = 400\n thickness = 0.025\n mask = mask_racing.tga\n}\n')
 (B/'track.tht').write_text(common+'num_material_layers = 2\nmaterial_layer0\n{\n material = compact soil\n}\nmaterial_layer1\n{\n material = soft soil\n thickness = 0.025\n mask = mask_racing.tga\n}\n')
 np.savetxt(B/'route.csv',np.c_[s,xy[:,0]+800,rz-offset,xy[:,1]+800],delimiter=',',header='station_m,game_x_m,game_y_height_m,game_z_m',comments='')
 ds=length/len(s);grade=(np.roll(rz,-1)-np.roll(rz,1))/(2*ds);native=raw.astype(float)/65535*scale+offset
 report=dict(version='moon-v001',name='Taurus-Littrow MX — Shorty Loop',stage='source and offline preview; not native compiled',half_gravity_m_s2=G,gravity_applied_by='Separate MXB Quiet Gravity v4 preset=half; single-player Testing only validated',lunar_gravity_is_not_simulated=True,track_length_m=round(length,1),riding_width_m=WIDTH,terrain_size_m=SIZE,native_samples=N,native_sample_spacing_m=STEP,measured_source_resolution_m=2,terrain_height_offset_m=offset,native_height_scale_m=scale,shorty_reference_lonlat=meta['shorty_reference_lonlat'],route_elevation_change_m=round(float(np.ptp(rz)),2),max_route_grade_percent=round(float(np.max(abs(grade))*100),2),min_centerline_radius_m=round(float(1/np.max(abs(curv))),1),min_centerline_distance_from_shorty_m=round(float(np.min(np.linalg.norm(xy,axis=1))),1),max_earthwork_cut_fill_m=round(float(np.max(abs(height-base))),2),shorty_90m_radius_unchanged=True,route_simple=bool(line.is_simple),native_quantization_max_error_m=float(np.max(abs(height-native))),source_data_valid_in_riding_area=True,context_nodata='Approximately 0.41% of coarse context crop filled with nearest valid elevation; no riding-area gaps',geometry_vertical_exaggeration=1,features=features,limitations=['Authored racing surface and procedural grain are fictional, not measured microtopography.','Provisional compact/soft soil mappings; no lunar granular tire or dust physics.','No timing, pits, native MAP/TRH/EDF or playable PKZ yet.','Rideability, jump clearances and engine lighting require a test build.'],source_hashes={p.name:sha(p) for p in S.glob('*.tif')})
 save(S/'track_spec.json',report);save(S/'route_control_points.json',dict(coordinates='meters east,north of Shorty reference',closed=True,points=CONTROL.tolist()));save(B/'validation.json',report)
 plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#e7e9eb','axes.labelcolor':'#bac2c8','xtick.color':'#a7b3bb','ytick.color':'#a7b3bb'})
 fig,ax=plt.subplots(figsize=(12,11),facecolor='#11161c');ax.set_facecolor('#11161c')
 ax.imshow(LightSource(315,30).hillshade(base[::2,::2],dx=STEP*2,dy=STEP*2),cmap='gray',extent=[-800,800,-800,800],vmin=-.1,vmax=1.1)
 ax.plot(xy[:,0],xy[:,1],color='#142831',lw=5);ax.plot(xy[:,0],xy[:,1],color='#6de1e5',lw=2.2);ax.add_patch(plt.Circle((0,0),90,fill=False,color='#f1c282',ls='--',lw=1))
 ax.annotate('SHORTY CRATER\nMapped terrain retained',xy=(0,0),xytext=(85,-40),color='#ffe0af',fontsize=10,arrowprops={'arrowstyle':'-','color':'#ffe0af'})
 for n,f in enumerate(features,1):
  i=np.argmin(abs(s-f['station_m']));ax.scatter(*xy[i],s=40,color='#f2c789',zorder=4);ax.annotate(f'R{n}',xy[i]+[12,14],color='#ffe0af',fontsize=10)
 ax.annotate('START / FIRST TEST STRAIGHT',xy=xy[0],xytext=(-570,-480),fontsize=9,color='#d6fbff',arrowprops={'arrowstyle':'->','color':'#d6fbff'})
 for station in [100,900,1700,2500]:
  i=np.argmin(abs(s-station));ax.annotate('',xy=xy[i]+tangent[i]*32,xytext=xy[i],arrowprops={'arrowstyle':'->','color':'#e7ffff','lw':2})
 ax.plot([400,600],[-600,-600],color='white',lw=3);ax.text(500,-640,'200 m',ha='center',fontsize=10);ax.annotate('N',xy=(650,560),xytext=(650,440),ha='center',color='white',arrowprops={'arrowstyle':'->','color':'white'},fontsize=13)
 ax.set(xlim=(-680,700),ylim=(-680,650),xlabel='Meters east of Shorty',ylabel='Meters north of Shorty')
 fig.text(.125,.95,'TAURUS–LITTROW MX  /  SHORTY LOOP',fontsize=20,color='#f4f4f5',fontweight='bold');fig.text(.125,.922,f'v001 terrain draft  •  {length/1000:.2f} km loop  •  16 m riding width  •  0.5 g baseline',fontsize=11,color='#9dd8df')
 fig.text(.125,.04,'LROC 2 m elevation data • No vertical exaggeration • Cyan = fictional motocross route\nR1–R4 = broad low rollovers • Initial layout, not a verified rideable build',fontsize=10,color='#aab4bd')
 fig.savefig(P/'01_layout.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
 save(B/'manifest.json',{p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(B.iterdir()) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
