"""Moon v002 native source: original lap plus pit access and regolith detail."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
import build_source as base
import test_materials as material
import race_setup as race
R=Path(__file__).resolve().parents[1];B=R/'build'
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def text(name,v):(B/name).write_text(v,encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base.main();(R/'previews_v002').mkdir(exist_ok=True)
 spec=json.loads((R/'source/track_spec.json').read_text());offset=spec['terrain_height_offset_m'];scale=spec['native_height_scale_m'];oldraw=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049);original=oldraw.astype(np.float32)/65535*scale
 def height(x,y):return map_coordinates(original,[(800-np.atleast_1d(y))/1600*2048,(np.atleast_1d(x)+800)/1600*2048],order=1,mode='nearest').squeeze()
 s,xy,tangent,norm,k,rz,L,features=base.route();rz-=offset;x=np.linspace(-800,800,2049,dtype=np.float32);xx,yy=np.meshgrid(x,x[::-1]);dist,idx=cKDTree(xy).query(np.c_[xx.ravel(),yy.ravel()],workers=4);dist=dist.reshape(xx.shape);idx=idx.reshape(xx.shape)
 pc=np.array([-445.,-410.]);pit=material.smooth((48-abs(xx-pc[0]))/8)*material.smooth((27-abs(yy-pc[1]))/8);pit_h=float(height(*pc));h=original*(1-pit)+(pit_h+.008*(xx-pc[0]))*pit
 control=np.array([[-415,-410],[-360,-402],[-305,-365],[-265,-320]],float);knots=np.r_[0,np.cumsum(np.linalg.norm(np.diff(control,axis=0),axis=1))];lane=CubicSpline(knots,control,bc_type='natural')(np.linspace(0,knots[-1],600));ld=np.r_[0,np.cumsum(np.linalg.norm(np.diff(lane,axis=0),axis=1))]
 lane_h=np.interp(ld,[0,ld[-1]],[pit_h+.008*(control[0,0]-pc[0]),float(height(*control[-1]))]);ad,ai=cKDTree(lane).query(np.c_[xx.ravel(),yy.ravel()],workers=4);access=material.smooth((8-ad.reshape(xx.shape))/3);ai=ai.reshape(xx.shape);h=h*(1-access)+lane_h[ai]*access
 protect=material.smooth((12-dist)/4);h=h*(1-protect)+original*protect
 assert h.min()>=0 and h.max()<=scale;raw=np.uint16(np.rint(h/scale*65535));assert np.array_equal(raw[dist<8],oldraw[dist<8]);assert np.array_equal(raw[np.hypot(xx,yy)<90],oldraw[np.hypot(xx,yy)<90])
 raw.astype('<u2').tofile(B/'terrain.raw');Image.fromarray(raw).save(B/'heightmap_16bit.png');h=raw.astype(np.float32)/65535*scale
 np.savez_compressed(B/'terrain_preview.npz',x=x[::2],y=x[::-1][::2],height=h[::2,::2],route_xy=xy.astype(np.float32),route_z=rz.astype(np.float32),offset=offset)
 np.savez_compressed(B/'v002_facility.npz',pit=pc,pit_size=[80,38],access=lane,access_h=lane_h)
 material.mask('mask_v002_pits.tga',pit);material.mask('mask_v002_start.tga',material.smooth((9-dist)/1)*(idx<100));material.mask('mask_v002_off.tga',material.smooth((np.maximum(abs(xx),abs(yy))-745)/25))
 mat=material.build(xy,s,norm);common=f'samples_x = 2049\nsamples_z = 2049\ndata = terrain.raw\nsize_x = 1600\nsize_z = 1600\nscale = {scale:g}\n'
 hmf=common+'num_layers = 4\n'+race.block('layer0',dict(map='basemap.tga',repetitions=1))+race.block('layer1',dict(map='v002_regolith.tga',repetitions=800,thickness=.03))+race.block('layer2',dict(map='v002_route.tga',repetitions=1,mask='mask_v002_route.tga',thickness=.025))+race.block('layer3',dict(map='v002_fine.tga',repetitions=800,mask='mask_v002_grain.tga',thickness=.01))
 hmf+='scene0\n{\n name = scenery.edf\n pos\n {\n x = 800\n y = 0\n z = 800\n }\n rot\n {\n x = 0\n y = 0\n z = 0\n }\n}\n';text('track.hmf',hmf)
 text('track.tht',common+'num_surface_layers = 3\n'+''.join(race.block('surface_layer'+str(i),dict(surface=surf,mask='mask_v002_'+name+'.tga')) for i,(surf,name) in enumerate([('off','off'),('pit','pits'),('start','start')]))+'num_material_layers = 2\n'+race.block('material_layer0',dict(material='compact soil'))+race.block('material_layer1',dict(material='soft soil',thickness=.025,mask='mask_racing.tga')))
 # All game bitmaps must use power-of-two dimensions; the height grid remains 2049.
 for bitmap in B.glob('*.tga'):
  with Image.open(bitmap) as im:
   if any(v & (v-1) for v in im.size):im.resize((2048,2048),Image.Resampling.BILINEAR).save(bitmap)
 positions=race.build(xy,s,tangent,L,pc,pit_h)
 text('map_params.ini','[params]\nlightdir_x=-6\nlightdir_y=10\nlightdir_z=-6.6666667\nshadowvolumes_create=0\nshadowvolumes_supersampling=2\nshadowmaps_create=1\nshadowmaps_scale=0.5\nshadowmaps_supersampling=2\nshadowmaps_terraincast=1\n');text('edf_params.ini','[params]\ntype=0\nuse_normals=1\n');text('trh_params.ini','[params]\ntype=3\ntrackcode_filename=code.txt\n')
 report=dict(version='moon-v002',stage='native source',checks_pass=True,baseline='moon-v001',main_riding_height_samples_unchanged=True,shorty_90m_unchanged=True,physical_changes_only_pit_and_access=True,max_pit_cut_fill_m=float(np.max(abs(h-original))),source_raw_sha256=sha(B/'terrain.raw'),terrain_source_resolution_m=2,half_gravity_m_s2=4.905,pit_stalls=8,grid_stalls=8,native_centerline_closure_m=positions['native_centerline_closure_m'],native_route_error_max_m=positions['native_route_error_max_m'],material=mat,in_game_test=False)
 save(B/'v002_source_validation.json',report);save(R/'source/v002_spec.json',report);print('MOON_V002_SOURCE_PASS',json.dumps(report),flush=True)
if __name__=='__main__':main()
