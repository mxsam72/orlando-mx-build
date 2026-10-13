"""Label real model renders and preserve all reproducible prototype assets."""
import json,zipfile,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path(__file__).resolve().parent;O=R/'output'
def font(n):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
panels=[('OLD','Current generic geometry'),('A','A  |  Airy pine'),('B','B  |  Dense woodland')]
sheet=Image.new('RGB',(2100,1060),'#f1f1ec');d=ImageDraw.Draw(sheet)
d.text((40,20),'ORLANDO MX  |  TREE PROTOTYPE REVIEW',fill='#202723',font=font(32))
d.text((40,65),'Actual 3D model renders with the same daylight. Track replacement awaits your selection.',fill='#505752',font=font(23))
for i,(key,title) in enumerate(panels):
    im=Image.open(O/(key+'_front.png')).convert('RGB').resize((700,550),Image.Resampling.LANCZOS);sheet.paste(im,(i*700,120))
    d.text((i*700+28,688),title,font=font(26),fill='#202723')
    if key!='OLD':
        im=ImageOps.fit(Image.open(O/(key+'_detail.png')).convert('RGB'),(700,280),Image.Resampling.LANCZOS);sheet.paste(im,(i*700,740))
    else:
        d.text((32,760),'Reconstructed from the current\ngeneric tree builder.\nSolid crown volumes and\nflat foliage colors.',font=font(24),fill='#505752',spacing=15)
sheet.save(O/'Orlando_Tree_Comparison.png')
woodline=Image.new('RGB',(1440,1760),'#f1f1ec');d=ImageDraw.Draw(woodline)
d.text((32,20),'BIKE-HEIGHT VIEW  |  ACTUAL 3D PROTOTYPES',font=font(30),fill='#202723')
for i,key in enumerate(['A','B']):
    image=Image.open(O/(key+'_woodline.png')).convert('RGB').resize((1440,800),Image.Resampling.LANCZOS);woodline.paste(image,(0,100+i*840))
    d.text((24,108+i*840),panels[i+1][1],font=font(28),fill='white',stroke_width=2,stroke_fill='#202723')
woodline.save(O/'Orlando_Tree_Woodline_Comparison.png')
for key in ['A','B']:
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','8','-i',str(O/(key+'_orbit_%03d.png')),'-vf','scale=640:480','-c:v','libx264','-pix_fmt','yuv420p',str(O/('Tree_'+key+'_Turntable.mp4'))],check=True)
qa=json.loads((O/'prototype_validation.json').read_text());assert qa['review_only'] and not qa['track_modified']
for name in ['Tree_A_LOD0.fbx','Tree_B_LOD0.fbx','Orlando_Tree_Prototypes.blend']:
    assert (O/name).stat().st_size>10000
readme='''Orlando MX tree prototypes — review only

A: Airy pine, approximately 11 m tall. Tapered trunk, irregular live branch levels, and fine needle sprays.
B: Dense evergreen woodland, approximately 9 m tall. Forked trunks, finer secondary branching, and layered small leaf sprays.

The PNG previews and turntable videos render the actual FBX source geometry and its textures with Blender Cycles. They are not MX Bikes screenshots. The old generic example is reconstructed from the current tree builder under the same lighting.

The track has not been changed. Style approval, native shader/transparency checks, variation/LOD design, final placement and an in-game performance check are required before mass replacement.

Files: Two FBX assets; editable Blender scene; generated foliage source textures; native-size TGA textures and matte shader files; photographic CC0 bark and soil provenance; reproducible Python scripts; validation; daylight stills and orbit videos.
'''
(O/'README_Tree_Prototypes.txt').write_text(readme)
zipname=O/'Orlando_Tree_Prototypes_Review.zip'
with zipfile.ZipFile(zipname,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(O.iterdir()):
        if p.is_file() and p!=zipname and '_orbit_' not in p.name:z.write(p,'review/'+p.name)
    for p in sorted((R/'textures').iterdir()):
        if p.is_file():z.write(p,'textures/'+p.name)
    for p in sorted(R.glob('*.py')):z.write(p,'source/'+p.name)
    z.write(R/'texture_provenance.json','texture_provenance.json')
with zipfile.ZipFile(zipname) as z:assert z.testzip() is None
print('PROTOTYPE_PACKAGE',zipname.stat().st_size,hashlib.sha256(zipname.read_bytes()).hexdigest(),flush=True)
