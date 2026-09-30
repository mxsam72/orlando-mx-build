"""Source-native, deterministic facility meshes. Coordinates are game XYZ metres.

One mesh per asset/material keeps export draw calls modest. No purchased or opaque
assets. Footage defines forms; placements/dimensions remain documented estimates.
"""
import math
import numpy as np
from v014_common import *

PALETTE={'timber':(87,76,61),'siding':(119,124,123),'trim':(225,224,214),
         'roof':(70,75,75),'alloy':(179,186,185),'glass':(33,48,52),
         'red':(159,38,33),'navy':(29,45,74),'rubber':(30,31,29),
         'bark':(98,91,74),'leaf1':(67,80,48),'leaf2':(84,99,61),'leaf3':(101,111,74),
         'gravel':(174,169,153)}

class Scene:
    def __init__(self,H):self.H=H;self.meshes={};self.group='';self.anchor=np.zeros(3);self.theta=0
    def asset(self,name,xz,heading=0):
        self.group=name;self.anchor=np.array([xz[0],float(ground(self.H,np.array([xz]))[0]),xz[1]]);self.theta=math.radians(heading)
    def add(self,verts,faces,mat):
        v=np.array(verts,float);c,s=math.cos(self.theta),math.sin(self.theta)
        v[:,[0,2]]=v[:,[0,2]]@np.array([[c,-s],[s,c]]);v+=self.anchor
        key=(self.group,mat);m=self.meshes.setdefault(key,dict(name=self.group+'_'+mat,asset=self.group,material=mat,vertices=[],faces=[]))
        n=len(m['vertices']);m['vertices'].extend(v.tolist());m['faces'].extend([[int(i+n) for i in f] for f in faces])
    def box(self,c,d,mat):
        c=np.array(c);d=np.array(d)/2;v=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])*d+c
        self.add(v,[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]],mat)
    def beam(self,a,b,r,mat,sides=6):
        a=np.array(a,float);b=np.array(b,float);axis=(b-a)/np.linalg.norm(b-a);u=np.cross(axis,[0,1,0])
        if np.linalg.norm(u)<.01:u=np.cross(axis,[1,0,0])
        u/=np.linalg.norm(u);w=np.cross(axis,u)
        v=[p+r*(math.cos(t)*u+math.sin(t)*w) for p in [a,b] for t in np.linspace(0,math.tau,sides,endpoint=False)]
        f=[[i,(i+1)%sides,(i+1)%sides+sides,i+sides] for i in range(sides)]+[list(range(sides-1,-1,-1)),list(range(sides,2*sides))];self.add(v,f,mat)
    def roof(self,width,depth,eave,rise,mat='roof',hip=False):
        w=width/2;d=depth/2;r=w*.48 if hip else w
        v=[[-w,eave,-d],[w,eave,-d],[w,eave,d],[-w,eave,d],[-r,eave+rise,0],[r,eave+rise,0]]
        self.add(v,[[0,1,5,4],[1,2,5],[2,3,4,5],[3,0,4],[3,2,1,0]],mat)
    def crown(self,c,rad,mat,seed):
        rng=np.random.default_rng(seed);v=[];rings=6;n=11
        for j in range(rings):
            p=-math.pi/2+.04+j*(math.pi-.08)/(rings-1)
            for k in range(n):
                t=k*math.tau/n;r=rad*(.88+.20*rng.random());v.append([c[0]+r*math.cos(p)*math.cos(t),c[1]+r*.48*math.sin(p),c[2]+r*math.cos(p)*math.sin(t)])
        f=[[j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k] for j in range(rings-1) for k in range(n)]
        f+=[list(range(n-1,-1,-1)),list(range((rings-1)*n,rings*n))];self.add(v,f,mat)

def build(H,cfg,front):
    s=Scene(H)
    for spec in cfg['assets']:
        typ=spec['type'];s.asset(spec['id'],spec['xz'],spec['heading'])
        if typ=='covered_stand':
            for x in [-4,0,4]:
                for z in [-2.4,2.4]:s.box([x,1.85,z],[.20,3.7,.20],'timber')
            for i in range(4):
                z=1.8-i*1.05;y=.25+i*.32
                s.box([0,y,z],[8.2,.17,1.0],'timber');s.box([0,y+.45,z-.3],[8,.12,.38],'timber')
                for x in [-3.5,3.5]:s.box([x,(y+.45)/2,z-.3],[.12,y+.45,.12],'timber')
            for z in [-2.5,2.5]:s.box([0,3.55,z],[8.6,.22,.18],'timber')
            s.roof(9.2,6,3.65,.65,'alloy')
            for x in np.arange(-4.4,4.5,.28):s.beam([x,3.68,-3],[x,4.30,0],.017,'trim',4);s.beam([x,4.30,0],[x,3.68,3],.017,'trim',4)
            for x in [-4.1,4.1]:
                for y in [1.4,2.0]:s.beam([x,y,-2.45],[x,y,2.4],.045,'timber',4)
        elif typ=='bleachers':
            s.box([0,.04,0],[7.5,.08,4.8],'gravel')
            for i in range(5):
                z=1.8-i*.84;y=.55+i*.34
                s.box([0,y,z],[6.8,.08,.34],'alloy');s.box([0,y-.30,z+.3],[6.8,.08,.55],'alloy')
                for x in [-2.8,0,2.8]:s.beam([x,.12,z],[x,y,z],.038,'alloy')
            for x in [-3.45,3.45]:
                s.beam([x,.15,-1.6],[x,2.85,-1.6],.04,'alloy');s.beam([x,1.5,2],[x,2.85,-1.6],.04,'alloy')
            s.beam([-3.45,2.85,-1.6],[3.45,2.85,-1.6],.04,'alloy')
        elif typ in ['office','restroom']:
            width,depth=(7.2,4.5) if typ=='office' else (6,4)
            s.box([0,1.3,0],[width,2.6,depth],'siding');s.roof(width+.6,depth+.6,2.65,.85,hip=(typ=='restroom'))
            for y in np.arange(.25,2.55,.23):s.box([0,y,depth/2+.015],[width,.018,.025],'alloy')
            for x in [-width/2+.06,width/2-.06]:s.box([x,1.3,depth/2+.04],[.13,2.6,.1],'trim')
            doors=[-1.45,1.45] if typ=='restroom' else [-2.5]
            for x in doors:
                s.box([x,1.05,depth/2+.055],[1.02,2.1,.1],'trim');s.box([x,1.04,depth/2+.115],[.88,1.99,.04],'glass');s.box([x+.3,1,depth/2+.15],[.04,.14,.04],'alloy')
            if typ=='office':
                s.box([.85,1.55,depth/2+.07],[3.2,1.1,.14],'trim');s.box([.85,1.55,depth/2+.15],[2.96,.86,.025],'glass');s.box([.85,1.02,depth/2+.3],[3.4,.1,.6],'trim')
            else:
                for z in np.arange(-2,2.2,.18):s.box([-4.1,.9,z],[.13,1.8,.16],'timber')
                s.box([-3.5,.9,2.1],[1.3,1.8,.12],'timber')
        elif typ in ['rv','trailer','concession','pickup']:
            length=7.6 if typ=='rv' else 5.4 if typ=='trailer' else 5.8 if typ=='concession' else 4.9
            width=2.4 if typ!='pickup' else 2.0
            for z in [-length*.29,length*.29]:
                for x in [-width/2,width/2]:
                    s.beam([x-.12,.43,z],[x+.12,.43,z],.41,'rubber',12);s.beam([x-.13,.43,z],[x+.13,.43,z],.23,'alloy',10)
            if typ=='pickup':
                s.box([0,.75,0],[2, .7,4.9],'red');s.box([0,1.4,.35],[1.85,.65,1.8],'red');s.box([0,1.48,1.27],[1.60,.48,.03],'glass')
                s.box([0,1.01,-1.45],[1.7,.05,1.7],'rubber')
            else:
                s.box([0,1.7,0],[width,2.5,length],'trim');s.box([0,3.03,0],[width+.1,.14,length+.1],'alloy')
                s.box([0,3.21,-1.1],[.85,.28,1.2],'trim')
                for x in [-width/2-.015,width/2+.015]:
                    s.box([x,1.1,0],[.035,.16,length-.3],'navy')
                    for z in [-1.8,.5,2.0]:s.box([x,2.1,z],[.04,.65,.95],'glass')
                if typ=='concession':
                    s.box([width/2+.05,1.9,0],[.08,1.1,3],'glass');s.box([width/2+.3,1.3,0],[.7,.12,3.2],'alloy');s.box([width/2+.45,2.58,0],[1,.08,3.3],'red')
                if typ=='rv':s.box([0,2.2,length/2+.02],[1.95,.9,.05],'glass')
                else:s.beam([-.8,.5,length/2],[0,.5,length/2+1.4],.06,'alloy');s.beam([.8,.5,length/2],[0,.5,length/2+1.4],.06,'alloy')
        elif typ=='pop_up':
            for x in [-1.7,1.7]:
                for z in [-1.7,1.7]:s.beam([x,0,z],[x,2.3,z],.027,'alloy')
            s.roof(3.8,3.8,2.3,.8,'navy',True)
        elif typ=='oak':
            radius=spec['radius'];s.beam([0,0,0],[.22,3.7,-.15],.36,'bark',9)
            for i in range(7):
                a=i*math.tau/7+.2;cx=math.cos(a)*radius*.52;cz=math.sin(a)*radius*.52;cy=4.6+(i%3)*.8
                s.beam([.1,2.3,0],[cx,cy,cz],.16 if i%2 else .21,'bark',7)
                s.crown([cx,cy+.8,cz],radius*.56,'leaf'+str(1+i%3),i+51)
        elif typ in ['flagpole','utility']:
            s.beam([0,0,0],[0,8.5,0],.08 if typ=='flagpole' else .16,'alloy' if typ=='flagpole' else 'timber',9)
            if typ=='utility':
                s.box([0,7.8,.15],[.65,.4,.4],'trim');s.box([0,7.77,.37],[.45,.24,.04],'glass')
            else:
                # 13 stripes, blue canton and 50 individually formed white stars.
                for i in range(13):s.box([1.1,7.9-i*.092,0],[2.15,.092,.014],'red' if i%2==0 else 'trim')
                s.box([.48,7.62,.014],[.92,.644,.016],'navy')
                for row in range(9):
                    count=6 if row%2==0 else 5
                    for col in range(count):
                        x=.08+col*.15+(0 if count==6 else .075);y=7.87-row*.069
                        verts=[[x,y,.031]]+[[x+.025*math.sin(k*math.pi/5)*(1 if k%2==0 else .4),y+.025*math.cos(k*math.pi/5)*(1 if k%2==0 else .4),.031] for k in range(10)]
                        s.add(verts,[[0,k+1,(k+1)%10+1] for k in range(10)],'trim')
    # Timber + open wire grid. Genuine holes, no solid opaque fence panels.
    points=np.array(front['fence_polyline_xz']);ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    gap=cfg['fence_opening_station_m'];stations=np.unique(np.r_[np.arange(0,ss[-1],3.0),ss[-1],gap]);stations=stations[(stations<=gap[0])|(stations>=gap[1])]
    pos=np.c_[np.interp(stations,ss,points[:,0]),np.interp(stations,ss,points[:,1])]
    for i,(station,p) in enumerate(zip(stations,pos)):
        s.asset('front_fence',p);s.box([0,.675,0],[.15,1.35,.15],'timber')
        if i==0:continue
        a=pos[i-1];length=np.linalg.norm(p-a);isgate=stations[i-1]==gap[0] and station==gap[1]
        heading=math.degrees(math.atan2(-(p[1]-a[1]),p[0]-a[0]));s.asset('pedestrian_gate' if isgate else 'front_fence',((p+a)/2).tolist(),heading)
        material='trim' if isgate else 'timber'
        for y in [.35,1.15]:s.box([0,y,0],[length,.12,.10],material)
        if isgate:
            for x in np.arange(-length/2+.15,length/2,.30):s.box([x,.74,0],[.055,.86,.055],'trim')
        else:
            for y in np.arange(.16,1.17,.16):s.beam([-length/2,y,.025],[length/2,y,.025],.007,'alloy',4)
            for x in np.arange(-length/2+.12,length/2,.16):s.beam([x,.12,.025],[x,1.18,.025],.007,'alloy',4)
    return list(s.meshes.values())

def main():
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    meshes=build(H,read(S/'pit_facilities.json'),read(S/'facilities.json'))
    save(O/'facility_meshes.json',meshes)
    print('Facility meshes:',len(meshes),'vertices:',sum(len(m['vertices']) for m in meshes))
if __name__=='__main__':main()
