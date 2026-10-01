"""Deterministic, UV-bound scenery textures; owner graphics follow supplied photos.
No plates, phone numbers, addresses or VINs are reproduced.
"""
import json,math,io,base64,zlib,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from matplotlib.font_manager import findfont,FontProperties
from v020_common import R,S,O,save,sha
COLORS={'sam_paint':(26,31,30),'sam_tan':(165,151,115),'van_paint':(28,30,29),'cyber_steel':(168,171,168),'premier_blue':(24,100,151),'white':(226,228,228),'yamaha_blue':(31,54,173),'husky_white':(222,226,224),'dark':(22,26,29),'glass':(31,47,57),'rubber':(32,33,35),'tire':(35,36,38),'tread':(40,40,41),'steel':(115,122,128),'alloy':(183,192,198),'wheel_black':(47,50,55),'rim_blue':(28,66,187),'fork_gold':(164,147,98),'engine':(108,110,109),'black_seat':(29,30,33),'blue_seat':(28,44,84),'red_light':(166,25,24),'amber':(218,132,27),'headlight':(213,222,216)}

def font(size,bold=False):return ImageFont.truetype(findfont(FontProperties(family='DejaVu Sans',weight='bold' if bold else 'normal')),size)
def textfit(draw,box,text,color='white',bold=True):
    x,y,w,h=box;f=font(int(h),bold)
    while draw.textbbox((0,0),text,font=f)[2]>w and f.size>4:f=font(f.size-1,bold)
    bb=draw.textbbox((0,0),text,font=f);draw.text((x+(w-bb[2])/2,y-bb[1]+(h-(bb[3]-bb[1]))/2),text,fill=color,font=f)
def power(draw,c,r,fill):
    x,y=c;draw.arc((x-r,y-r,x+r,y+r),35,325,fill=fill,width=max(3,int(r*.28)));draw.line((x,y-r*1.15,x,y),fill=fill,width=max(3,int(r*.26)))
def star(draw,c,r,fill):
    x,y=c;pts=[]
    for i in range(10):
        a=-math.pi/2+i*math.pi/5;rr=r if i%2==0 else r*.40;pts.append((x+rr*math.cos(a),y+rr*math.sin(a)))
    draw.polygon(pts,fill=fill)
def build():
    dest=S/'vehicle_textures';dest.mkdir(exist_ok=True);textures={}
    def keep(name,im,color=None):
        im=im.convert('RGB')
        # PiBoSo fbx2edf silently collapses NPOT textures: the v020 native
        # regression probe produced ~210 KB EDF for 256x256 but only 716 bytes
        # for 256x320. Normalize every generated bitmap to power-of-two dimensions.
        def np2(n):
            p=1
            while p<n:p*=2
            return p
        target=(np2(im.width),np2(im.height))
        if im.size!=target:im=im.resize(target,Image.Resampling.LANCZOS)
        buf=io.BytesIO();im.save(buf,format='PNG');p=dest/(name+'.png');p.write_bytes(buf.getvalue())
        assert im.width&(im.width-1)==0 and im.height&(im.height-1)==0
        textures[name]=dict(file='vehicle_textures/'+p.name,rgb=list(color or np.array(im).mean(axis=(0,1)).astype(int)),width=im.width,height=im.height,sha256=sha(p));return im
    rng=np.random.default_rng(19019)
    for name,c in COLORS.items():
        n=128;yy,xx=np.mgrid[:n,:n];noise=rng.normal(0,.8,(n,n))
        if name=='cyber_steel':noise+=rng.normal(0,2,(n,1))+2*np.sin(yy*.6)
        if name in ['glass','alloy','steel']:noise+=(1-yy/n)*14
        if 'seat' in name:noise+=((yy%8)<2)*9+((xx%8)<2)*3
        if name in ['tire','tread','rubber']:noise+=rng.normal(0,1.6,(n,n))
        arr=np.clip(np.array(c)+noise[...,None],0,255).astype('uint8');keep(name,Image.fromarray(arr),c)
    # Silverado-style side wrap: white front door, oversized red power icon,
    # blue lightning bed and dark sill band, faithfully distinct at pit distance.
    # Atlas dimensions match the physical 3.69 x 1.15 m side region.
    base=Image.new('RGB',(1024,320),(23,98,148));d=ImageDraw.Draw(base)
    for i in range(11):
        pts=[(rng.integers(0,430),0)]
        for y in range(0,321,32):pts.append((pts[-1][0]+rng.integers(-34,35),y))
        d.line(pts,fill=(88,164,194),width=2)
    d.polygon([(450,0),(1024,0),(1024,285),(380,285)],fill=(230,231,226));d.rectangle((0,282,1024,320),fill=(22,26,27))
    d.ellipse((440,-45,750,265),fill=(200,37,52));power(d,(595,108),103,(241,241,235))
    for mirrored in [False,True]:
        im=base.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirrored else base.copy();d=ImageDraw.Draw(im)
        def label(box,text,color='white',bold=True):
            x,y,w,h=box;textfit(d,(1024-x-w if mirrored else x,y,w,h),text,color,bold)
        label((760,178,250,35),'premier',(25,28,31));label((760,213,250,35),'power',(25,28,31))
        label((30,78,360,30),'Premier Power');label((35,119,350,16),'ELECTRICAL SERVICES');label((62,188,150,24),'B & R ELECTRICAL');label((40,293,940,15),'QUALITY & SAFE ELECTRICAL INSTALLATIONS')
        keep('premier_wrap_right' if mirrored else 'premier_wrap',im,(255,255,255))
    im=Image.new('RGB',(512,256),(24,98,148));d=ImageDraw.Draw(im);textfit(d,(20,23,472,80),'premier');textfit(d,(20,99,472,85),'power');textfit(d,(20,200,472,28),'ELECTRICAL SERVICES');keep('premier_tail',im,(255,255,255))
    for name,label,bg,fg in [('ford_badge','FORD',(19,49,84),'white'),('king_ranch','KING RANCH',(171,155,114),(45,45,36)),('four_by_four','4x4',(26,31,30),'white'),('chevy_badge','CHEVROLET',(44,47,47),(210,169,49))]:
        im=Image.new('RGB',(256,96),bg);d=ImageDraw.Draw(im)
        if name=='chevy_badge':
            d.polygon([(88,17),(167,17),(159,36),(234,36),(225,64),(159,64),(153,83),(73,83),(80,64),(20,64),(29,36),(82,36)],fill=(214,169,60),outline=(220,220,216),width=4)
        elif name=='ford_badge':
            d.ellipse((5,3,251,93),fill=(20,51,92),outline=(205,217,228),width=5);textfit(d,(28,20,200,52),'Ford','white')
        else:textfit(d,(7,20,242,55),label,fg)
        keep(name,im,(255,255,255))
    for owner,number,bg,fg in [('jordan','759',(231,234,229),(19,23,28)),('premier','277',(229,232,228),(18,21,26)),('sam','373',(23,27,34),(238,238,228)),('shane','927',(21,25,32),(239,239,231))]:
        im=Image.new('RGB',(512,320),bg);d=ImageDraw.Draw(im);d.polygon([(0,0),(512,0),(485,27),(20,40)],fill=(30,55,159) if owner!='jordan' else (22,24,27));textfit(d,(12,42,488,230),number,fg);textfit(d,(16,285,480,20),'HUSQVARNA' if owner=='jordan' else 'YAMAHA',fg);keep(owner+'_number',im,(255,255,255))
        im=Image.new('RGB',(512,384),(23,34,62) if owner!='jordan' else (25,27,31));d=ImageDraw.Draw(im)
        d.polygon([(0,280),(512,0),(512,70),(60,350)],fill=(46,101,203) if owner!='jordan' else (221,225,218));d.polygon([(0,330),(512,80),(512,116),(34,384)],fill=(206,220,233))
        if owner=='jordan':
            star(d,(406,100),85,(200,179,105));textfit(d,(12,134,365,53),'ROCKSTAR',(215,191,112));textfit(d,(25,192,330,26),'ENERGY DRINK','white');textfit(d,(332,254,170,76),'H', 'white')
        elif owner=='premier':
            textfit(d,(25,95,465,74),'premier');textfit(d,(25,168,465,74),'power');power(d,(152,201),23,(206,35,47));textfit(d,(15,298,480,38),'YZ450F')
        elif owner=='sam':
            textfit(d,(12,95,482,84),'YAMAHA');textfit(d,(85,238,342,55),'YZ250F',(218,227,243))
        else:
            textfit(d,(10,105,492,45),'CENTRAL FLORIDA');textfit(d,(12,169,488,66),'POWERSPORTS');textfit(d,(40,285,430,29),'YAMAHA YZ450F')
        keep(owner+'_shroud',im,(255,255,255))
    save(S/'vehicle_materials.json',textures)
    archive={}
    for p in sorted(dest.glob('*.png')):
        raw=p.read_bytes();archive[p.name]=dict(sha256=sha(p),data=base64.b64encode(zlib.compress(raw,9)).decode())
    save(S/'vehicle_textures_packed.json',archive)
    assert all((m['width']&(m['width']-1)==0 and m['height']&(m['height']-1)==0) for m in textures.values())
    print('Vehicle texture materials:',len(textures),'all power-of-two');return textures
if __name__=='__main__':build()
