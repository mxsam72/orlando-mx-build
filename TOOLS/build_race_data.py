#!/usr/bin/env python3
"""Emit documented PiBoSo text files and sampled TL reset boundaries."""
from pathlib import Path
import json,math,struct,shutil,csv
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1]
NAME='orlandomx_2026_v005'

def block(name,fields):
    return name+'\n{\n'+''.join(f' {k} = {v}\n' for k,v in fields.items())+'}\n'
def main():
    info=json.loads((ROOT/'01_GIS_AERIAL/geometry.json').read_text());d=np.load(ROOT/'01_GIS_AERIAL/route.npz');q=d['q'];w=d['width'];sa=d['start'];L=info['model_lap_length_m'];cut=0.;origin=np.array(info['native_origin_xz']);H=np.load(ROOT/'02_HEIGHTMAP/height_metres.npy')
    out=ROOT/'09_TRACKED';release=ROOT/'12_RELEASE'/NAME;release.mkdir(parents=True,exist_ok=True)
    def point(s,lat=0):
        source=(s+cut)%L;x=np.interp(source,q[:,3],q[:,0]);z=np.interp(source,q[:,3],q[:,1]);theta=np.interp(source,q[:,3],q[:,2]);x+=lat*math.sin(theta);z-=lat*math.cos(theta)
        y=float(map_coordinates(H,[[ (600-z)/600*2048 ],[ x/600*2048 ]],order=1)[0]);angle=(90-math.degrees(theta))%360
        return x,y,z,angle
    def project(x,z,absangle):
        a=q[:-1,:2];v=q[1:,:2]-a;u=np.clip(((np.array([x,z])-a)*v).sum(1)/(v*v).sum(1),0,1);p=a+u[:,None]*v;i=int(np.argmin(((p-[x,z])**2).sum(1)));ss=q[i,3]+u[i]*(q[i+1,3]-q[i,3]);theta=q[i,2]+u[i]*(q[i+1,2]-q[i,2]);right=np.array([math.sin(theta),-math.cos(theta)]);lat=float(np.dot(np.array([x,z])-p[i],right));angle=(90-math.degrees(theta))%360
        return dict(long=f'{(ss-cut)%L:.6f}',lat=f'{lat:.6f}',angle=f'{((absangle-angle+180)%360)-180:.6f}')
    def tcl(path,startxz,angle,segs):
        text=f'x = {startxz[0]:.6f}\nz = {startxz[1]:.6f}\nangle = {angle:.6f}\nnumsegment = {len(segs)}\n'
        for i,(typ,length,radius,ang) in enumerate(segs):text+=block(f'segment{i}',dict(type=typ,length=f'{length:.6f}',radius=f'{radius:.6f}',angle=f'{ang:.6f}',height=0,heightlock=0))
        path.write_text(text)
    finish=23.;rdf=block('finish_line',dict(line=0,long=finish,left=-8,right=8))+block('split1',dict(line=0,long=round(L/3,6),left=-9,right=9))+block('split2',dict(line=0,long=round(2*L/3,6),left=-9,right=9))
    stalls=[]
    for row in range(3):
        for col in range(8):
            x=260+col*10;z=110+row*7;stalls.append(dict(x=float(x),z=float(z),angle=0))
    fields=dict(numstalls=24,starttype=1,startstartlong=0,startdifflong=0,startstartlat=0,startendlat=0,startanglerel=0,startposx=f'{stalls[0]["x"]:.6f}',startposz=f'{stalls[0]["z"]:.6f}',startspacingx=10,startspacingz=7,startangleabs=0,startcolumns=8)
    pits=block('pit_lane',fields)[:-2]
    for i,st in enumerate(stalls):pits+=block(f' start_stall{i}',project(st['x'],st['z'],st['angle']))
    rdf+=pits+'}\n'
    pb=block('pit_board',dict(height=1.5,startlong=20,difflong=.65,startlat=8.8,endlat=8.8))[:-2]
    for i in range(24):pb+=block(f' stall{i}',dict(long=20-i*.65,lat=8.8,angle=0))
    rdf+=pb+'}\n'
    grid=[];gx=float(sa[0,0])+1.5;gz=float(sa[0,1])
    for i in range(24):grid.append(dict(x=float(gx),z=float(gz+(i-11.5)*1.5),angle=90))
    gridtxt=block('starting_grid',dict(numstalls=24,type=1,posx=f'{gx:.6f}',posz=f'{gz:.6f}',angle=90,numstallsperrow=24,distfromstartline=0,lanespacing=0,rowspacing=0,difflat=0,lanewidth=1.5,latshift=0,side=1))[:-2]
    for i,st in enumerate(grid):gridtxt+=block(f' stall{i}',project(st['x'],st['z'],st['angle']))
    rdf+=gridtxt+'}\n'
    cps=[]
    for e in info['turns']:
        s=(e['mid']-cut)%L;cps.append(dict(long=round(s,6),left=-e['width']/2-1,right=e['width']/2+1,penalty=5,line=0,start=0))
    cps.sort(key=lambda x:x['long']);cps.insert(0,dict(long=14,left=-19,right=19,penalty=5,line=2,start=1))
    rdf+=f'num_checkpoints = {len(cps)}\n'
    for i,c in enumerate(cps):rdf+=block(f'checkpoint{i}',c)
    bx=gx+5;bz=gz-20;rdf+=f'30secondsboard_posx = {bx:.6f}\n30secondsboard_posz = {bz:.6f}\n30secondsboard_angle = 0\n'+block('30seconds_board',project(bx,bz,0))
    (release/f'{NAME}.rdf').write_text(rdf)
    (out/'race_positions.json').write_text(json.dumps(dict(pits=stalls,grid=grid,finish=finish,checkpoints=cps),indent=2)+'\n')
    # The published sample TL format is magic + uint32 count + float32(long,lat) pairs.
    ss=np.linspace(0,L,math.ceil(L/2)+1);source=(ss+cut)%L;ww=np.interp(source,q[:,3],w)
    for fname,factor in [('minrace.tl',-1),('maxrace.tl',1),('checkleft.tl',-1),('checkright.tl',1)]:
        offset=ww/2-(.7 if fname in ['minrace.tl','maxrace.tl'] else -.5)
        data=np.c_[ss,offset*factor].astype('<f4');(release/fname).write_bytes(b'TL \0'+struct.pack('<I',len(data))+data.tobytes())
    cams=[]
    for i,e in enumerate(info['turns']):
        s=(e['mid']-cut)%L;side=1 if e['angle']>0 else -1;x,y,z,angle=point(s,side*(e['width']/2+9));cams.append(dict(x=x,y=y+4,z=z,angle=(angle+90*side)%360,start=(e['arc_start']-cut)%L,end=(e['arc_end']+8-cut)%L))
    tsc='numcamset = 1\ncamset0\n{\n name = Trackside\n surface = 0\n numcameras = 14\n'
    for i,c in enumerate(cams):tsc+=f' camera{i}\n {{\n  type = 0\n  pos = {c["x"]:.6f},{c["y"]:.6f},{c["z"]:.6f}\n  fov = 60\n  rot = {c["angle"]:.6f}\n  autozoom\n  {{\n   enable = 1\n   reference = 0.17\n   min = 12\n   max = 65\n  }}\n }}\n'
    (release/f'{NAME}.tsc').write_text(tsc+'}\n')
    mx,my,mz,_=point(finish,8.5);marshal=f'flagman\n{{\n pos\n {{\n x = {mx:.6f}\n y = {my:.6f}\n z = {mz:.6f}\n }}\n long = {finish}\n}}\n'
    for i,e in enumerate(info['turns'][::2]):
        s=(e['arc_start']-cut)%L;side=1 if e['angle']>0 else -1;x,y,z,_=point(s,side*(e['width']/2+3));marshal+=f'marshal{i}\n{{\n pos\n {{\n x = {x:.6f}\n y = {y:.6f}\n z = {z:.6f}\n }}\n long = {s:.6f}\n}}\n'
    (release/'marshals.cfg').write_text(marshal)
    (release/f'{NAME}.ini').write_text(f'[info]\nname=Orlando MX 2026 v005\nshort_name=Orlando MX\nlength={L:.0f}m\naltitude=20\n\n[race]\ndefaulteventlaps=5\nreflaptime=136\n\n[ui]\npic={NAME}.tga\npic_info={NAME}_map.tga\nauthor=Sir Strange / Codex\nlocation=Orlando, Florida\n\n[weather]\ncloud_prob=0.25\nrainy_prob=0.1\n\n[data]\ncode=2\n')
    amb='sun_position\n{\n x = 2\n y = 10\n z = -7\n}\n'
    for name,ambient,sun,fog,density in [('clear',(.48,.53,.60),(1.0,.95,.82),(.74,.81,.87),.00045),('cloudy',(.66,.68,.72),(.26,.27,.30),(.72,.76,.82),.00065),('rainy',(.53,.56,.63),(.22,.24,.29),(.55,.59,.64),.0013)]:
        amb+=name+'\n{\n'+block(' ambient',dict(zip(['red','green','blue'],ambient)))+block(' sun_color',dict(zip(['red','green','blue'],sun)))+block(' fog',dict(density=density,**dict(zip(['red','green','blue'],fog))))+f' sky = *{name}sky.edf\n sky_rot = 0\n'+'}\n'
    (release/f'{NAME}.amb').write_text(amb)
    # Source declarations get staged next to every referenced input by build_windows.ps1.
    common='samples_x = 2049\nsamples_z = 2049\ndata = terrain.raw\nsize_x = 600\nsize_z = 600\nscale = 18\n'
    hmf=common+'num_layers = 6\n'
    hmf+=block('layer0',dict(map='basemap.tga',repetitions=1))
    for i,(texture,reps,mask,thick) in enumerate([('soil',110,None,.15),('prepared',130,'racing.tga',.09),('sand',155,'sand.tga',.05),('grass',100,'grass.tga',.03),('worked',130,'worked.tga',.015)],1):
        text=f'layer{i}\n{{\n map = {texture}.tga\n repetitions = {reps}\n thickness = {thick}\n'
        if mask:text+=f' mask = mask_{mask}\n'
        if texture!='grass':text+=f' frame1\n {{\n  map = {texture}_wet.tga\n }}\n'
        hmf+=text+'}\n'
    scene='scene0\n{\n name = scenery.edf\n pos\n {\n  x = 0\n  y = 0\n  z = 0\n }\n rot\n {\n  x = 0\n  y = 0\n  z = 0\n }\n}\n'
    hmf+=scene
    tht=common+'num_surface_layers = 3\n'+''.join(block(f'surface_layer{i}',dict(surface=surf,mask=f'mask_{mask}.tga')) for i,(surf,mask) in enumerate([('off','off'),('pit','pits'),('start','start')]))+'num_material_layers = 5\n'+block('material_layer0',dict(material='compact soil'))
    for i,(mat,thick,mask) in enumerate([('soil',.15,None),('soft soil',.08,'racing'),('sand',.05,'sand'),('grass',.03,'grass')],1):
        fields=dict(material=mat,thickness=thick)
        if mask:fields['mask']=f'mask_{mask}.tga'
        tht+=block(f'material_layer{i}',fields)
    tht+=scene
    (ROOT/'BUILD/track.hmf').write_text(hmf);(ROOT/'BUILD/track.tht').write_text(tht)
    (ROOT/'BUILD/map_params.ini').write_text('[params]\nlightdir_x=2\nlightdir_y=10\nlightdir_z=-7\nshadowvolumes_create=1\nshadowvolumes_supersampling=1\nshadowmaps_create=1\nshadowmaps_scale=0.2\nshadowmaps_supersampling=1\nshadowmaps_terraincast=1\n')
    (ROOT/'BUILD/trh_params.ini').write_text('[params]\ntype=3\ntrackcode_filename=code.txt\n')
    (ROOT/'BUILD/edf_params.ini').write_text('[params]\ntype=0\nuse_normals=1\n')
    # Actual route map for the game's selection panel, not a georeferenced aerial.
    im=Image.new('RGB',(1024,1024),(28,42,35));dr=ImageDraw.Draw(im)
    bounds=np.array([q[:,:2].min(0)-30,q[:,:2].max(0)+30]);bmin=bounds[0];extent=max(bounds[1]-bmin);scale=850/extent
    def to_px(x,z):return ((x-bmin[0])*scale+65,950-(z-bmin[1])*scale)
    path=[to_px(*xz) for xz in q[:,:2]];dr.line(path,fill=(181,146,93),width=14,joint='curve');dr.line(path,fill=(223,197,145),width=2)
    x,y,z,a=point(finish);px,py=to_px(x,z);dr.ellipse((px-9,py-9,px+9,py+9),fill=(250,242,201))
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    try:font=ImageFont.truetype(fontpath,38);small=ImageFont.truetype(fontpath,20)
    except OSError:font=small=ImageFont.load_default()
    dr.text((55,30),'ORLANDO MX',font=font,fill='white');dr.text((56,80),f'2026 traced layout  |  {L/1000:.2f} km model  |  v005',font=small,fill=(192,205,183));im.save(release/f'{NAME}_map.tga');im.save(ROOT/'DOCUMENTATION/track_map.png')
    # Temporary image is replaced by the native Blender render during staging.
    if not (release/f'{NAME}.tga').exists():im.resize((1024,1024)).save(release/f'{NAME}.tga')
    print('Race data, centerlines, reset boundaries, metadata and compiler inputs generated.')
if __name__=='__main__':main()
