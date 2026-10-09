"""Create review boards from checked, matched source renders."""
import io, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from v037_common import R, O, BASE, read, sha, save, atomic

ROOT=R.parent;D=ROOT/'deliverables-v037';RENDERS=ROOT/'deliverables-v037-renders'
def font(n,bold=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',n)
def write_image(im,path):
    b=io.BytesIO();im.save(b,format='PNG');atomic(path,b.getvalue())
    with Image.open(path) as check:check.load();assert check.size==im.size
def image_for(version,record):
    path=RENDERS/(version+'_output')/'images'/record['filename'];assert sha(path)==record['sha256']
    with Image.open(path) as im:im.load();return im.convert('RGB')
def main():
    D.mkdir(exist_ok=True);before=read(RENDERS/'v036_output/manifest_01,02,06,07.json');after=read(RENDERS/'v037_output/manifest.json')
    old={x['id']:x for x in before['renders']};new={x['id']:x for x in after['renders']};metrics=[]
    for key in ['01_Oval_Overhead','02_Oval_Oblique','06_Full_Site','07_Start_Preserved']:
        a,b=old[key],new[key]
        for prop in ['pos','focus','up','fov','box','tex','step']:assert a.get(prop)==b.get(prop),(key,prop)
        aa,bb=(np.asarray(image_for(v,r)).astype(np.int16) for v,r in [('v036',a),('v037',b)])
        delta=np.abs(aa[:-110]-bb[:-110]);fraction=float((delta.max(2)>3).mean())
        if key!='07_Start_Preserved':assert fraction>.001,('Addition is not visible',key)
        metrics.append(dict(view=key,matched_camera=True,changed_pixel_fraction=fraction,mean_absolute_RGB_difference=float(delta.mean())))
    W=3840;pad=64;gap=32;col=1840;ih=1035;color=(20,26,29);boards=[]
    board=Image.new('RGB',(W,1370),color);dr=ImageDraw.Draw(board)
    dr.text((pad,28),'ORLANDO MX 2026  /  v037',font=font(31,True),fill=(224,188,85))
    dr.text((pad,75),'The empty field becomes a car oval',font=font(52,True),fill=(245,244,239))
    for j,(v,r,label) in enumerate([('v036',old['01_Oval_Overhead'],'v036  /  EMPTY FIELD'),('v037',new['01_Oval_Overhead'],'v037  /  OVAL + TWO CYBERTRUCKS')]):
        x=pad+j*(col+gap);dr.text((x,152),label,font=font(29,True),fill=(224,188,85) if j else (192,202,204));board.paste(image_for(v,r).resize((col,ih),Image.Resampling.LANCZOS),(x,202))
    dr.text((pad,1285),'Matched views of actual track source. External renders, not MX Bikes screenshots.',font=font(28),fill=(184,196,198))
    p=D/'OrlandoMX_v037_Field_Before_After.png';write_image(board,p);boards.append(dict(file=p.name,pixels=list(board.size),sha256=sha(p)))
    H=2430;board=Image.new('RGB',(W,H),color);dr=ImageDraw.Draw(board)
    dr.text((pad,27),'ORLANDO MX 2026  /  v037',font=font(31,True),fill=(224,188,85));dr.text((pad,75),'Field oval and two Cybertrucks',font=font(52,True),fill=(245,244,239))
    rows=[('01_Oval_Overhead','OVAL + CENTRAL CROSSOVER'),('02_Oval_Oblique','BEYOND THE TREE LINE'),('04_Cybertruck_Straight','CYBERTRUCK 01  /  STRAIGHT'),('05_Cybertruck_Curve','CYBERTRUCK 02  /  BEND')]
    for i,(key,label) in enumerate(rows):
        x=pad+(i%2)*(col+gap);y=160+(i//2)*(ih+88);dr.text((x,y),label,font=font(28,True),fill=(192,202,204));board.paste(image_for('v037',new[key]).resize((col,ih),Image.Resampling.LANCZOS),(x,y+44))
    dr.text((pad,H-68),'Actual source assets. Two static vehicle displays. v037 in-game riding and performance checks are pending.',font=font(27),fill=(184,196,198))
    p=D/'OrlandoMX_v037_Oval_Preview.png';write_image(board,p);boards.append(dict(file=p.name,pixels=list(board.size),sha256=sha(p)))
    inputs={}
    for version,folder,manifest in [('v036',BASE,before),('v037',O,after)]:
        inputs[version]={name:sha(folder/name) for name in ['terrain.raw','scenery.fbx','main.tcl','start.tcl','compiled_track.hmf']}
        for name,value in manifest['source_sha256'].items():assert inputs[version][name]==value
    native=read(D/'OrlandoMX_v037_Validation.json');assert native['source_validation']['terrain_sha256']==inputs['v037']['terrain.raw'];assert native['source_validation']['scenery_sha256']==inputs['v037']['scenery.fbx']
    manifest=dict(version='v037',baseline='user-tested v036',native_source_commit=native['source_commit'],source_inputs=inputs,comparisons=metrics,boards=boards,source_render_manifests={'v036':before,'v037':after},render_type='External renders of exact compiled source inputs; not MX Bikes screenshots',static_cybertruck_count=2,in_game_v037_test=False)
    save(D/'OrlandoMX_v037_Render_Manifest.json',manifest);print(json.dumps(dict(boards=boards,matched_views=len(metrics)),indent=2))
if __name__=='__main__':main()
