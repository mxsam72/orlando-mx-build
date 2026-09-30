"""Deterministic, UV-bound scenery textures; owner graphics follow supplied photos.
No plates, phone numbers, addresses or VINs are reproduced.
"""
import json,math,io,base64,zlib,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from matplotlib.font_manager import findfont,FontProperties
from v019_common import R,S,O,save,sha
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
        im=im.convert('RGB');buf=io.BytesIO();im.save(buf,format='PNG');p=dest/(name+'.png');p.write_bytes(buf.getvalue());textures[name]=dict(file='vehicle_textures/'+p.name,rgb=list(color or np.array(im).mean(axis=(0,1)).astype(int)),width=im.width,height=im.height,sha256=sha(p));return im
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
    im=Image.new('RGB',(1024,512),(23,98,148));d=ImageDraw.Draw(im)
    for i in range(11):
        pts=[(rng.integers(0,480),0)]
        for y in range(0,500,45):pts.append((pts[-1][0]+rng.integers(-44,45),y))
        d.line(pts,fill=(88,164,194),width=2)
    d.polygon([(450,0),(1024,0),(1024,430),(360,430)],fill=(230,231,226));d.rectangle((0,420,1024,512),fill=(22,26,27))
    d.ellipse((445,-95,820,300),fill=(200,37,52));power(d,(636,106),118,(241,241,235))
    textfit(d,(730,244,285,56),'premier',(25,28,31));textfit(d,(730,299,285,56),'power',(25,28,31));power(d,(781,326),16,(199,35,50))
    textfit(d,(55,90,340,42),'Premier Power','white');textfit(d,(50,150,350,26),'ELECTRICAL SERVICES','white');d.ellipse((70,240,180,350),fill=(224,234,231),outline=(20,68,98),width=5);textfit(d,(75,267,100,38),'B & R',(17,90,122));textfit(d,(40,446,940,24),'QUALITY & SAFE ELECTRICAL INSTALLATIONS','white')
    keep('premier_wrap',im,(255,255,255))
    im=Image.new('RGB',(512,256),(24,98,148));d=ImageDraw.Draw(im);textfit(d,(20,23,472,80),'premier');textfit(d,(20,99,472,85),'power');textfit(d,(20,200,472,28),'ELECTRICAL SERVICES');keep('premier_tail',im,(255,255,255))
    for name,label,bg,fg in [('ford_badge','FORD',(19,49,84),'white'),('king_ranch','KING RANCH',(171,155,114),(45,45,36)),('four_by_four','4x4',(26,31,30),'white'),('chevy_badge','CHEVROLET',(44,47,47),(210,169,49))]:
        im=Image.new('RGB',(256,96),bg);d=ImageDraw.Draw(im);textfit(d,(7,20,242,55),label,fg);keep(name,im,(255,255,255))
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
    save(S/'vehicle_materials.json',textures);print('Vehicle texture materials:',len(textures));return textures
if __name__=='__main__':build()
