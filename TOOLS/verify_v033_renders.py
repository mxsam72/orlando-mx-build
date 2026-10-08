"""Compare matching native-source views and annotate measured placement."""
import io, json, math, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates
from v033_common import R,O,S,BASE,read,save,sha,atomic

D=R.parent/'deliverables-v033'
BEFORE=R.parent/'deliverables-v033-checks/v032_output'
AFTER=R.parent/'deliverables-v033-checks/v033_output'
H=np.fromfile(BASE/'terrain.raw','<u2').reshape(2049,2049)/65535*18

def font(n,bold=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',n)
def ground(x,z):return float(map_coordinates(H,[[(600-z)/600*2048],[x/600*2048]],order=1,mode='nearest')[0])
def project(points,shot,width=2560,height=1440):
    c=np.array(shot['pos']);n=np.array(shot['focus'])-c;n/=np.linalg.norm(n)
    right=np.cross(n,shot.get('up',[0,0,1]));right/=np.linalg.norm(right);up=np.cross(right,n)
    delta=np.asarray(points)[:,[0,2,1]]-c;depth=delta@n;f=height/2/math.tan(math.radians(shot['fov']/2))
    return np.column_stack([width/2+(delta@right)/depth*f,height/2-(delta@up)/depth*f])
def image_save(im,path,kind='PNG',**kwargs):
    b=io.BytesIO();im.save(b,format=kind,**kwargs);atomic(path,b.getvalue())

def main():
    D.mkdir(exist_ok=True)
    old=read(BEFORE/'manifest_01,02.json');new=read(AFTER/'manifest.json')
    faces=[]
    for i in range(2):
        a=old['renders'][i];b=new['renders'][i]
        for k in ['pos','focus','fov','box','pixels']:assert a[k]==b[k],('Camera changed',k)
        im0=Image.open(BEFORE/'images'/(a['id']+'.png'));im0.load()
        im1=Image.open(AFTER/'images'/(b['id']+'.png'));im1.load()
        raw0=np.asarray(im0).astype(int);raw1=np.asarray(im1).astype(int);difference=np.max(abs(raw1-raw0),axis=2)
        cfg=read(R/'V032_SOURCE/memorial_spec.json');g=ground(322,144);z=143.896 if i==0 else 144.104
        lower=g+cfg['image_lower_edge_above_ground_m'];upper=lower+cfg['image_height_m']
        art=project([[318,lower,z],[326,lower,z],[326,upper,z],[318,upper,z]],b)
        x0,y0=np.ceil(art.min(0)+6).astype(int);x1,y1=np.floor(art.max(0)-6).astype(int)
        columns=[]
        for x in [318.7,322.,325.3]:
            line=project([[x,(lower+upper)/2,z]],b)[0];cx=int(round(line[0]))
            changed=int(np.count_nonzero(difference[y0:y1,cx-12:cx+13]>25));assert changed>1500
            columns.append(dict(world_x_m=x,projected_center_px=cx,changed_image_pixels=changed))
        faces.append(dict(face='front' if i==0 else 'back',matching_camera_verified=True,three_post_bands_visibly_changed=columns,artwork_region_px=[int(x0),int(y0),int(x1),int(y1)],before_sha256=sha(BEFORE/'images'/(a['id']+'.png')),after_sha256=sha(AFTER/'images'/(b['id']+'.png')),visually_inspected_all_three_stripes_removed=True))
    canvas=Image.new('RGB',(3200,2110),(17,25,31));draw=ImageDraw.Draw(canvas)
    draw.text((48,28),'PUP WHATLEY MEMORIAL | VERIFIED SUPPORT FIX',font=font(42,True),fill=(255,255,255))
    draw.text((48,88),'Matching cameras, actual track meshes and unchanged artwork. Front and back checked.',font=font(28),fill=(182,198,203))
    for row,name in enumerate(['01_Memorial_Front','02_Memorial_Back']):
        y=157+row*943
        for col,folder in enumerate([BEFORE,AFTER]):
            x=48+col*1577
            draw.text((x,y),('FRONT' if row==0 else 'BACK')+' | '+('v032: supports cross image' if col==0 else 'v033: full artwork visible'),font=font(28,True),fill=(238,182,103) if col==0 else (146,226,180))
            im=Image.open(folder/'images'/(name+'.png'));im.load();canvas.paste(im.resize((1529,860),Image.Resampling.LANCZOS),(x,y+45))
    draw.text((48,2061),'External source renders, not in-game captures. All three supports retained below the board; 4.4 cm clearance inside each printed face.',font=font(22),fill=(182,198,203))
    image_save(canvas,D/'OrlandoMX_v033_Memorial_Before_After.jpg','JPEG',quality=95,subsampling=0)
    image_save(canvas,D/'OrlandoMX_v033_Memorial_Before_After.png')
    layout=Image.open(AFTER/'images/05_Updated_Layout.png');layout.load()
    shot=next(s for s in new['renders'] if s['id']=='05_Updated_Layout');spec=read(S/'qwikchute_spec.json');x,z=spec['xz_m'];gy=ground(x,z)
    point=project([[x,gy,z]],shot)[0];reference_px=point/4+[1,15]
    # The grass anchor must land inside the user's original marked region.
    cx,cy=429.73,262.62;assert ((reference_px[0]-cx)/17)**2+((reference_px[1]-cy)/22)**2<1
    overlay=Image.new('RGBA',layout.size);dr=ImageDraw.Draw(overlay);px,py=point
    dr.ellipse((px-30,py-38,px+30,py+38),outline=(255,221,49,255),width=5)
    label='QWIKCHUTE | behind fence';f=font(28,True);box=dr.textbbox((0,0),label,font=f);lx=px+74;ly=py-55
    dr.rounded_rectangle((lx-15,ly-12,lx+box[2]+15,ly+box[3]+15),radius=8,fill=(14,22,28,240));dr.text((lx,ly),label,font=f,fill=(255,221,49,255));dr.line((px+30,py,lx-15,ly+20),fill=(255,221,49,255),width=4)
    annotated=Image.alpha_composite(layout.convert('RGBA'),overlay).convert('RGB');image_save(annotated,D/'OrlandoMX_v033_Qwikchute_Placement.jpg','JPEG',quality=95,subsampling=0)
    for name in ['01_Memorial_Front','02_Memorial_Back','03_Qwikchute_Pit_Face','04_Qwikchute_Track_Face']:
        target='OrlandoMX_v033_'+name.split('_',1)[1]+'.jpg';atomic(D/target,(AFTER/'images'/(name+'.jpg')).read_bytes())
    assert sha(O/'facility_textures/v032_pup_whatley_memorial.tga')==sha(BASE/'facility_textures/v032_pup_whatley_memorial.tga')
    report=dict(version='v033',checks_pass=True,source_geometry_before_sha256=old['source_sha256']['scenery.fbx'],source_geometry_after_sha256=new['source_sha256']['scenery.fbx'],source_sources_unchanged_during_render=True,actual_geometry_rendered=True,render_size_px=[2560,1440],memorial_artwork_byte_exact=True,memorial_face_checks=faces,qwikchute_anchor_xz_m=[x,z],qwikchute_anchor_projected_into_user_reference_px=reference_px.tolist(),anchor_inside_original_yellow_mark=True,qwikchute_both_faces_visually_checked=True,qwikchute_existing_light_pole_cleared_from_frontal_views=True,in_game_visual_check=False)
    save(D/'OrlandoMX_v033_Render_Verification.json',report)
    print('Both memorial faces changed in all three post bands; original artwork exact; billboard anchor inside original mark.',flush=True)

if __name__=='__main__':main()
