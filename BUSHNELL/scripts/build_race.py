"""Bushnell-specific closed native centerline, race setup and selection imagery."""
from pathlib import Path
import json, math, struct
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from PIL import Image, ImageDraw, ImageFont
from native_route import native_segments, sample_native, write_tcl
from build_source import ROOT, save


def block(name, fields):
    return name+'\n{\n'+''.join(f' {k} = {v}\n' for k,v in fields.items())+'}\n'


def main():
    config=json.loads((ROOT/'project.json').read_text());B=ROOT/'build/v001';G=B/'game';G.mkdir(exist_ok=True);name=config['game_track_id']
    design=np.load(B/'design.npz');xy=design['xy']-design['origin'];station=design['station'];width=design['width'];h=np.load(B/'height_metres.npy');size=config['terrain']['size_m']
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))];heading=np.unwrap(np.arctan2(design['tangent'][:,1],design['tangent'][:,0]));q=np.c_[xy,heading,arc,np.zeros(len(arc))]
    origin,theta,segments=native_segments(q,station_spacing=1.25);native=sample_native(origin,theta,segments,spacing=.2);length=float(native[-1,3]);closure=float(np.linalg.norm(native[0,:2]-native[-1,:2]));error=float(cKDTree(xy).query(native[:,:2])[0].max())
    if closure>.02 or error>.4: raise ValueError(f'Native route fit failed: {closure}, {error}')
    write_tcl(B/'main.tcl',origin,theta,segments);np.savez_compressed(B/'native_route.npz',q=native)
    def point(s,lat=0):
        s%=length;p=np.array([np.interp(s,native[:,3],native[:,i]) for i in range(2)]);th=np.interp(s,native[:,3],native[:,2]);return p+lat*np.array([math.sin(th),-math.cos(th)]),th
    def height(p): return float(map_coordinates(h,[[(size-p[1])/size*2048],[p[0]/size*2048]],order=1)[0])
    def project(p,angle):
        _,i=cKDTree(native[:,:2]).query(p);th=native[i,2];return dict(long=f'{native[i,3]:.6f}',lat=f'{np.dot(p-native[i,:2],[math.sin(th),-math.cos(th)]):.6f}',angle=f'{(angle-(90-math.degrees(th))+180)%360-180:.6f}')
    finish=33.
    rdf=block('finish_line',dict(line=0,long=finish,left=-5,right=5))+block('split1',dict(line=0,long=round(length/3,6),left=-5.5,right=5.5))+block('split2',dict(line=0,long=round(2*length/3,6),left=-5.5,right=5.5))
    pit=np.array([56.,-83.])-design['origin'];pits=[]
    for row in range(2):
        for col in range(4): pits.append(dict(x=float(pit[0]-12+col*8),z=float(pit[1]-4+row*8),angle=0))
    fields=dict(numstalls=8,starttype=1,startstartlong=0,startdifflong=0,startstartlat=0,startendlat=0,startanglerel=0,startposx=pits[0]['x'],startposz=pits[0]['z'],startspacingx=8,startspacingz=8,startangleabs=0,startcolumns=4)
    rdf+=block('pit_lane',fields)[:-2]+''.join(block(' start_stall'+str(i),project(np.array([p['x'],p['z']]),p['angle'])) for i,p in enumerate(pits))+'}\n'
    grid=[]
    for row in range(4):
        for col in range(2):
            p,th=point(21-row*4.5,(col-.5)*2.4);grid.append(dict(x=float(p[0]),z=float(p[1]),angle=float((90-math.degrees(th))%360)))
    rdf+=block('starting_grid',dict(numstalls=8,type=1,posx=grid[0]['x'],posz=grid[0]['z'],angle=grid[0]['angle'],numstallsperrow=2,distfromstartline=0,lanespacing=0,rowspacing=0,difflat=0,lanewidth=2.4,latshift=0,side=1))[:-2]+''.join(block(' stall'+str(i),project(np.array([p['x'],p['z']]),p['angle'])) for i,p in enumerate(grid))+'}\n'
    rdf+=block('pit_board',dict(height=1.5,startlong=35,difflong=.7,startlat=5,endlat=5))[:-2]+''.join(block(' stall'+str(i),dict(long=35+i*.7,lat=5,angle=0)) for i in range(8))+'}\n'
    cps=np.arange(85,length-30,85);rdf+=f'num_checkpoints = {len(cps)}\n'+''.join(block('checkpoint'+str(i),dict(line=0,long=round(float(s),6),left=-5,right=5,penalty=5,start=0)) for i,s in enumerate(cps));(G/(name+'.rdf')).write_text(rdf)
    ss=np.linspace(0,length,math.ceil(length/1.5)+1);native_width=np.interp(ss/length*station[-1],station,width)
    for filename,sign in [('minrace.tl',-1),('maxrace.tl',1),('checkleft.tl',-1),('checkright.tl',1)]:
        offset=native_width/2+(.6 if filename.startswith('check') else -.35);data=np.c_[ss,sign*offset].astype('<f4');(G/filename).write_bytes(b'TL \0'+struct.pack('<I',len(data))+data.tobytes())
    (G/(name+'.ini')).write_text(f'[info]\nname=Bushnell Motocross v001\nshort_name=Bushnell MX\nlength={length:.0f}m\naltitude=20\n\n[race]\ndefaulteventlaps=3\nreflaptime=120\n\n[ui]\npic={name}.tga\npic_info={name}_map.tga\nauthor=Sir Strange / Codex\nlocation=Bushnell, Florida\n\n[weather]\ncloud_prob=0.2\nrainy_prob=0.05\n\n[data]\ncode=2\n')
    amb='sun_position\n{\n x = -6\n y = 10\n z = -5\n}\n'
    for weather,ambient,sun,fog in [('clear',(.58,.62,.67),(1,.96,.86),.0003),('cloudy',(.68,.70,.73),(.35,.36,.38),.0005),('rainy',(.55,.58,.62),(.25,.27,.31),.001)]:
        amb+=weather+'\n{\n'+block(' ambient',dict(zip(['red','green','blue'],ambient)))+block(' sun_color',dict(zip(['red','green','blue'],sun)))+block(' fog',dict(density=fog,red=.74,green=.81,blue=.88))+f' sky = *{weather}sky.edf\n sky_rot = 0\n}}\n'
    (G/(name+'.amb')).write_text(amb)
    cameras='numcamset = 1\ncamset0\n{\n name = Bushnell trackside\n surface = 0\n numcameras = 8\n'
    for i,s in enumerate(np.linspace(50,length-50,8)):
        p,th=point(s,9);cameras+=f' camera{i}\n {{\n  type = 0\n  pos = {p[0]:.5f},{height(p)+3.5:.5f},{p[1]:.5f}\n  fov = 60\n  rot = {(90-math.degrees(th)+90)%360:.5f}\n  autozoom\n  {{\n   enable = 1\n   reference = 0.17\n   min = 12\n   max = 65\n  }}\n }}\n'
    (G/(name+'.tsc')).write_text(cameras+'}\n');p,_=point(finish,5.5);(G/'marshals.cfg').write_text(f'flagman\n{{\n pos\n {{\n  x = {p[0]:.5f}\n  y = {height(p):.5f}\n  z = {p[1]:.5f}\n }}\n long = {finish}\n}}\n')
    for filename,picture in [(name+'_map.tga','BushnellMX_v001_01_terrain_plan.png'),(name+'.tga','BushnellMX_v001_01_terrain_plan.png')]:
        with Image.open(ROOT/'previews'/picture) as im: im.convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS).save(G/filename)
    report=dict(checks_pass=True,native_centerline_length_m=length,native_closure_m=closure,native_route_error_max_m=error,native_segments=len(segments),finish_station_m=finish,pits=pits,grid=grid,pits_and_start_grid_status='provisional test layout; exact real gate not established',physics_profile='standard_game')
    save(B/'race_validation.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['pits','grid']},indent=2))


if __name__=='__main__': main()
