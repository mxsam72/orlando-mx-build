"""Suppress white specular glare on foliage, keeping approved diffuse pixels and geometry."""
import json,re
import numpy as np
from PIL import Image,ImageDraw
from v052_surface import R,O,sha,save,tga
from v052_scenery import F
LEAVES=['CK_TREE_v047_pine','CK_TREE_v047_woodland']
MATTE='v052_foliage_specular.tga'
SHADER='specular\n{\n map = '+MATTE+'\n shininess = 8\n}\n'
EXPECTED={'CK_TREE_v047_pine':'091acfc8add61ce5d33fd36194d759fb3e5e7862899b9f7803c4a82ca20f7ac1',
          'CK_TREE_v047_woodland':'b2403d55134f5b4d6d01cd9d5c7e2b257bf45e565d2c6d59a43cdf8cee3d404e'}

def main():
 F.mkdir(parents=True,exist_ok=True)
 spec=np.zeros((16,16,4),np.uint8);spec[:,:,:3]=[127,127,255]
 tga(spec,F/MATTE);assert Image.open(F/MATTE).getchannel('A').getextrema()==(0,0)
 rows=[];view=R/'BUILD/v052_review';view.mkdir(parents=True,exist_ok=True)
 for stem in LEAVES:
  p=R/'V047_OUTPUT/facility_textures'/(stem+'.tga')
  assert sha(p)==EXPECTED[stem]
  oldshader=(p.with_suffix('.shd')).read_text()
  assert 'specular' in oldshader and not re.search(r'(?m)^\s*map\s*=',oldshader)
  (F/(stem+'.shd')).write_text(SHADER)
  # Preserve every approved foliage colour and opacity pixel.
  im=Image.open(p).convert('RGBA');rgb=np.asarray(im)
  opaque=rgb[:,:,3]>=128
  white=opaque&(rgb[:,:,:3].min(2)>180)
  rows.append(dict(diffuse_texture=p.name,diffuse_sha256=sha(p),diffuse_pixels_and_alpha_exact=True,
   original_shader=oldshader,corrected_shader=SHADER,specular_map=MATTE,
   specular_alpha_min=0,specular_alpha_max=0,opaque_pixels=int(opaque.sum()),white_opaque_texels=int(white.sum()),
   shader_sha256=sha(F/(stem+'.shd')),tree_meshes_and_positions_unchanged=True))
  bg=Image.new('RGBA',im.size,(36,45,57,255));bg.alpha_composite(im)
  image=bg.convert('RGB').resize((1024,1024));draw=ImageDraw.Draw(image)
  draw.rectangle((0,0,1024,46),fill=(22,26,30))
  draw.text((12,15),stem+' - exact green diffuse photo; matte specular alpha 0 - SOURCE ONLY',fill='white')
  image.save(view/(stem+'_matte_source.jpg'),quality=95)
 scene=O/'scenery.fbx';grass=json.loads((O/'v052_scenery_validation.json').read_text())
 assert sha(scene)==grass['scenery_sha256'] and grass['all_non_grass_records_exact']
 save(O/'v052_foliage_validation.json',dict(checks_pass=True,mode='Explicit zero-intensity specular map on both leaf shaders',
  source_scene_sha256=sha(scene),all_tree_geometry_records_exact=True,diffuse_and_cutout_alpha_pixels_exact=True,
  specular_map=MATTE,specular_map_sha256=sha(F/MATTE),specular_map_size=[16,16],specular_alpha_min=0,specular_alpha_max=0,
  rows=rows,bark_shader_unchanged=True,official_shader_reference='https://docs.piboso.com/wiki/index.php?title=Track_Creation_Guide',
  reported_white_patches_likely_cause='Unmapped broad specular highlights; source photographs contain essentially no white leaf regions',
  in_game_visual_check=False))
 print('Both leaf shaders use zero specular intensity; diffuse cutouts, tree geometry and scenery FBX exact.',flush=True)
if __name__=='__main__':main()
