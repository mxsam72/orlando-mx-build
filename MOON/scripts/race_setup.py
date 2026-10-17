"""Native closed centerline, timing, eight start and pit positions, reset limits."""
from pathlib import Path
import json,math,struct,sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[1];B=R/'build';GAME=B/'game';NAME='taurus_littrow_mx_v002'
sys.path.insert(0,str(R.parent/'TOOLS'))
from reference_route import native_segments,sample_native,write_tcl

def text(p,t):p.write_text(t,encoding='utf-8',newline='\n')
def block(n,d):return n+'\n{\n'+''.join(f' {k} = {v}\n' for k,v in d.items())+'}\n'
def build(xy,s,tangent,L,pc,pit_h):
 GAME.mkdir(exist_ok=True);theta=np.unwrap(np.arctan2(tangent[:,1],tangent[:,0]));q=np.c_[np.vstack([xy,xy[0]])+800,np.r_[theta,theta[0]+2*np.pi],np.r_[s,L],np.zeros(len(s)+1)]
 origin,heading,segments=native_segments(q,station_spacing=5);nq=sample_native(origin,heading,segments);nl=float(nq[-1,3]);closure=float(np.linalg.norm(nq[-1,:2]-nq[0,:2]));error=float(cKDTree(q[:,:2]).query(nq[:,:2])[0].max());assert closure<.02 and error<.4
 write_tcl(B/'main.tcl',origin,heading,segments);np.savez_compressed(B/'native_route.npz',q=nq)
 def point(st,lat=0):
  st%=nl;px=np.interp(st,nq[:,3],nq[:,0]);pz=np.interp(st,nq[:,3],nq[:,1]);th=np.interp(st,nq[:,3],nq[:,2]);return np.array([px+lat*math.sin(th),pz-lat*math.cos(th)]),th
 def project(p,ang):
  _,i=cKDTree(nq[:,:2]).query(p);th=nq[i,2];return dict(long=f'{nq[i,3]:.6f}',lat=f'{np.dot(p-nq[i,:2],[math.sin(th),-math.cos(th)]):.6f}',angle=f'{(ang-(90-math.degrees(th))+180)%360-180:.6f}')
 finish=150.;rdf=block('finish_line',dict(line=0,long=finish,left=-10,right=10))+block('split1',dict(line=0,long=round(nl/3,6),left=-12,right=12))+block('split2',dict(line=0,long=round(2*nl/3,6),left=-12,right=12))
 stalls=[dict(x=float(pc[0]-24+c*14+800),z=float(pc[1]-8+r*16+800),angle=90) for r in range(2) for c in range(4)]
 fields=dict(numstalls=8,starttype=1,startstartlong=0,startdifflong=0,startstartlat=0,startendlat=0,startanglerel=0,startposx=stalls[0]['x'],startposz=stalls[0]['z'],startspacingx=14,startspacingz=16,startangleabs=90,startcolumns=4)
 rdf+=block('pit_lane',fields)[:-2]+''.join(block(' start_stall'+str(i),project(np.array([v['x'],v['z']]),v['angle'])) for i,v in enumerate(stalls))+'}\n'
 grid=[]
 for row in range(2):
  for col in range(4):
   pos,th=point(8-row*6,(col-1.5)*2.8);grid.append(dict(x=float(pos[0]),z=float(pos[1]),angle=float((90-math.degrees(th))%360)))
 rdf+=block('starting_grid',dict(numstalls=8,type=1,posx=grid[0]['x'],posz=grid[0]['z'],angle=grid[0]['angle'],numstallsperrow=4,distfromstartline=0,lanespacing=0,rowspacing=0,difflat=0,lanewidth=2.8,latshift=0,side=1))[:-2]+''.join(block(' stall'+str(i),project(np.array([v['x'],v['z']]),v['angle'])) for i,v in enumerate(grid))+'}\n'
 rdf+=block('pit_board',dict(height=1.5,startlong=165,difflong=1,startlat=10,endlat=10))[:-2]+''.join(block(' stall'+str(i),dict(long=165+i,lat=10,angle=0)) for i in range(8))+'}\n'
 cps=np.arange(270,nl,180);rdf+=f'num_checkpoints = {len(cps)}\n'+''.join(block('checkpoint'+str(i),dict(long=round(st,6),left=-14,right=14,penalty=5,line=0,start=0)) for i,st in enumerate(cps));text(GAME/(NAME+'.rdf'),rdf)
 for name,side in [('minrace.tl',-1),('maxrace.tl',1),('checkleft.tl',-1),('checkright.tl',1)]:
  ss=np.linspace(0,nl,math.ceil(nl/2)+1);a=np.c_[ss,np.full(len(ss),side*(9 if name in ['minrace.tl','maxrace.tl'] else 11))].astype('<f4');(GAME/name).write_bytes(b'TL \0'+struct.pack('<I',len(a))+a.tobytes())
 text(GAME/(NAME+'.ini'),f'[info]\nname=Taurus-Littrow MX v002\nshort_name=Shorty Loop\nlength={nl:.0f}m\naltitude=0\n\n[race]\ndefaulteventlaps=3\nreflaptime=240\n\n[ui]\npic={NAME}.tga\npic_info={NAME}_map.tga\nauthor=Sir Strange / Codex\nlocation=Taurus-Littrow, Moon\n\n[weather]\ncloud_prob=0\nrainy_prob=0\n\n[data]\ncode=2\n')
 amb='sun_position\n{\n x = -6\n y = 10\n z = -6.6666667\n}\n'
 for weather in ['clear','cloudy','rainy']:amb+=weather+'\n{\n'+block(' ambient',dict(red=.10,green=.10,blue=.10))+block(' sun_color',dict(red=.98,green=.97,blue=.94))+block(' fog',dict(density=0,red=0,green=0,blue=0))+' sky = moon_sky.edf\n sky_rot = 0\n}\n'
 text(GAME/(NAME+'.amb'),amb)
 data=dict(pits=stalls,grid=grid,finish_station_m=finish,native_length_m=nl,pit_center_local=pc.tolist(),pit_elevation_m=pit_h,native_centerline_closure_m=closure,native_route_error_max_m=error)
 text(B/'race_positions.json',json.dumps(data,indent=2)+'\n')
 for name,target in [('01_layout.png',NAME+'_map.tga'),('02_valley_overview.png',NAME+'.tga')]:
  with Image.open(R/'previews'/name) as im:im.convert('RGB').resize((1024,1024)).save(GAME/target)
 return data
