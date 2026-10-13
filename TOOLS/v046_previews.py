"""Source-material and scope inspection; optional CPU terrain authoring render.

These are previews of the authored files, never MX Bikes screenshots.
"""
import json,math,re,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import map_coordinates
from v046_surface import R,BASE,O,M,SIZE,Section

def font(n):
    for name in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(name).exists():return ImageFont.truetype(name,n)
    return ImageFont.load_default()

def main():
    spec=json.loads((R/'V046_SOURCE/visual_spec.json').read_text());section=Section(spec)
    h=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049).astype(np.float32)/65535*18
    shade=np.clip(110+h*7,35,215).astype(np.uint8)
    im=Image.fromarray(np.stack([shade,shade,shade],2)).resize((1200,1200))
    alpha=Image.open(M/'mask_v046_section.tga').getchannel('A').resize((1200,1200))
    overlay=Image.new('RGB',im.size,(205,122,44));im=Image.composite(overlay,im,alpha)
    d=ImageDraw.Draw(im)
    points=[(float(x/600*1200),float((600-z)/600*1200)) for x,z in section.p[::5]]
    d.line(points,fill=(220,230,239),width=2)
    for label,s in [('Finish tabletop',23),('Triple',151),('Table-single',255),('Pre-finish rollers',1345)]:
        q=section.q[np.argmin(abs(section.q[:,3]-s))];x=q[0]/600*1200;y=(600-q[1])/600*1200
        d.ellipse((x-5,y-5,x+5,y+5),fill='white');d.text((x+8,y-24 if label!='Triple' else y+7),label,font=font(18),fill='white',stroke_width=1,stroke_fill='black')
    d.rectangle((0,0,1200,75),fill=(22,25,29));d.text((24,15),'v046: entire riding circuit — orange = new dirt coverage',font=font(25),fill='white')
    im.save(R/'BUILD/v046_scope_preview.png')
    sheet=Image.new('RGB',(1600,920),(22,25,29));d=ImageDraw.Draw(sheet)
    for i,(kind,title) in enumerate([('loose','Loose / disturbed soil — 4K, 2 m tile'),('packed','Packed riding line — 4K, 2 m tile')]):
        sheet.paste(Image.open(M/f'v045_{kind}.tga').resize((800,800),Image.Resampling.LANCZOS),(i*800,60))
        d.text((i*800+18,16),title,font=font(22),fill='white')
    d.text((18,879),'Actual authored colour maps; paired normal maps are included. This is not an in-game screenshot.',font=font(20),fill='white')
    sheet.save(R/'BUILD/v046_soil_material_preview.jpg',quality=94)
    print('Source scope and paired-material previews saved.',flush=True)

if __name__=='__main__':main()
