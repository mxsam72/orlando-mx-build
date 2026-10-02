"""Small deterministic mesh authoring kit; local +Z is vehicle front, +Y up."""
import math,json
import numpy as np
from v024_common import *

def triangulate(poly):
    """Ear clip a planar 2D simple polygon, including open wheel-arch profiles."""
    p=np.asarray(poly,float);ids=list(range(len(p)));area=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))
    if area<0:ids.reverse()
    tris=[]
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    while len(ids)>3:
        found=False
        for j in range(len(ids)):
            a,b,c=ids[j-1],ids[j],ids[(j+1)%len(ids)];A,B,C=p[[a,b,c]]
            if cross(B-A,C-B)<=1e-10:continue
            others=[k for k in ids if k not in [a,b,c]]
            if any(cross(B-A,p[k]-A)>=-1e-9 and cross(C-B,p[k]-B)>=-1e-9 and cross(A-C,p[k]-C)>=-1e-9 for k in others):continue
            tris.append([a,b,c]);ids.pop(j);found=True;break
        if not found:raise ValueError('Non-simple polygon or degenerate ear')
    tris.append(ids);return tris

class MeshBuilder:
    def __init__(self,asset):self.asset=asset;self.parts={}
    def add(self,verts,faces,mat,uv=None):
        v=np.asarray(verts,float);assert np.isfinite(v).all();m=self.parts.setdefault(mat,dict(name=self.asset+'_'+mat,asset=self.asset,material=mat,vertices=[],faces=[],uv=[]));offset=len(m['vertices']);m['vertices']+=v.tolist()
        for k,face in enumerate(faces):
            # All supplied non-triangle faces here are convex.
            coords=uv[k] if uv is not None else [[v[i,2]%1,v[i,1]%1] for i in face]
            for j in range(1,len(face)-1):
                ids=[0,j,j+1];f=[face[i] for i in ids]
                if np.linalg.norm(np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]))<1e-10:continue
                m['faces'].append([i+offset for i in f]);m['uv'].append([coords[i] for i in ids])
    def box(self,c,d,mat,rotation=None):
        v=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float)*np.array(d)/2
        if rotation is not None:v=v@np.array(rotation).T
        v+=c;faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]];uv=[[[0,0],[1,0],[1,1],[0,1]]]*6;self.add(v,faces,mat,uv)
    def beam(self,a,b,r,mat,n=8,cap=True):
        a=np.asarray(a,float);b=np.asarray(b,float);axis=b-a;axis/=np.linalg.norm(axis);u=np.cross(axis,[0,1,0])
        if np.linalg.norm(u)<.01:u=np.cross(axis,[1,0,0])
        u/=np.linalg.norm(u);v=np.cross(axis,u)
        vv=[p+r*(math.cos(t)*u+math.sin(t)*v) for p in [a,b] for t in np.linspace(0,math.tau,n,endpoint=False)];faces=[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        if cap:faces += [list(range(n-1,-1,-1)),list(range(n,2*n))]
        self.add(vv,faces,mat)
    def tube(self,points,r,mat,n=8):
        for a,b in zip(points[:-1],points[1:]):self.beam(a,b,r,mat,n)
    def loft(self,sections,mat):
        # Each section: z, bottom, shoulder, top, halfwidth, roof_halfwidth.
        verts=[]
        for z,b,s,t,w,r in sections:verts.extend([[-w,b,z],[w,b,z],[w,s,z],[r,t,z],[-r,t,z],[-w,s,z]])
        faces=[]
        for k in range(len(sections)-1):
            for i in range(6):faces.append([k*6+i,k*6+(i+1)%6,(k+1)*6+(i+1)%6,(k+1)*6+i])
        faces += [list(range(5,-1,-1)),list(range((len(sections)-1)*6,len(sections)*6))];self.add(verts,faces,mat)
    def prism(self,zy,x0,x1,mat):
        zy=np.asarray(zy,float)
        if np.sum(zy[:,0]*np.roll(zy[:,1],-1)-zy[:,1]*np.roll(zy[:,0],-1))<0:zy=zy[::-1]
        n=len(zy);verts=[[x,y,z] for x in [x0,x1] for z,y in zy];tris=triangulate(zy)
        faces=tris+[[i+n for i in reversed(t)] for t in tris]+[[i,i+n,(i+1)%n+n,(i+1)%n] for i in range(n)];self.add(verts,faces,mat)
    def panel(self,verts,mat,flip=False):
        uv=[[0,0],[1,0],[1,1],[0,1]] if not flip else [[1,0],[0,0],[0,1],[1,1]]
        self.add(verts,[[0,1,2,3],[3,2,1,0]],mat,[uv,list(reversed(uv))])
    def wheel(self,x,y,z,r,width,rim,style='spoke',spokes=12,knobs=False):
        n=32 if not knobs else 40;verts=[]
        inner=.73 if knobs else .58
        profile=[(-width*.50,r*inner),(-width*.53,r*.83),(-width*.40,r*.97),(-width*.24,r),(width*.24,r),(width*.40,r*.97),(width*.53,r*.83),(width*.50,r*inner)]
        for dx,rad in profile:
            for t in np.linspace(0,math.tau,n,endpoint=False):verts.append([x+dx,y+rad*math.sin(t),z+rad*math.cos(t)])
        faces=[[k*n+i,k*n+(i+1)%n,((k+1)%len(profile))*n+(i+1)%n,((k+1)%len(profile))*n+i] for k in range(len(profile)) for i in range(n)]
        self.add(verts,[list(reversed(f)) for f in faces],'tire')
        rr=r*(.76 if knobs else .61)
        for side in [-1,1]:
            xx=x+side*width*.51
            for i in range(n):
                a=i*math.tau/n;b=(i+1)*math.tau/n
                self.beam([xx,y+rr*math.sin(a),z+rr*math.cos(a)],[xx,y+rr*math.sin(b),z+rr*math.cos(b)],.013 if knobs else .025,rim,5)
            self.beam([xx-side*.05,y,z],[xx+side*.006,y,z],r*.16,'alloy' if style=='steel' else rim,12)
            if style=='steel':
                self.beam([xx-side*.02,y,z],[xx,y,z],r*.53,'steel',24)
                for t in np.linspace(0,math.tau,6,endpoint=False):self.beam([xx,y+rr*.65*math.sin(t),z+rr*.65*math.cos(t)],[xx+side*.005,y+rr*.65*math.sin(t),z+rr*.65*math.cos(t)],.034,'dark',8)
            else:
                for t in np.linspace(0,math.tau,spokes,endpoint=False):
                    self.beam([xx-side*.018,y+rr*.16*math.sin(t+.10),z+rr*.16*math.cos(t+.10)],[xx,y+rr*.94*math.sin(t),z+rr*.94*math.cos(t)],.0037 if knobs else .021,rim if not knobs else 'alloy',4 if knobs else 5)
            if not knobs:
                for t in np.linspace(0,math.tau,6,endpoint=False):self.beam([xx,y+.055*math.sin(t),z+.055*math.cos(t)],[xx+side*.012,y+.055*math.sin(t),z+.055*math.cos(t)],.012,'alloy',6)
        # Actual raised tread blocks, distributed around the rolling surface.
        for i,t in enumerate(np.linspace(0,math.tau,n,endpoint=False)):
            tang=np.array([0,math.cos(t),-math.sin(t)]);rad=np.array([0,math.sin(t),math.cos(t)]);rot=np.c_[[1,0,0],rad,tang]
            for side in [-1,1]:
                c=[x+side*width*.25,y+(r+.006)*math.sin(t),z+(r+.006)*math.cos(t)]
                self.box(c,[width*.42,.026 if knobs else .018,.041 if knobs else .068],'tread',rot)
    def place(self,xz,heading,H):
        t=math.radians(heading);c,s=math.cos(t),math.sin(t);rotation=np.array([[c,0,s],[0,1,0],[-s,0,c]]);anchor=np.array([xz[0],float(ground(H,np.array([xz]))[0]),xz[1]])
        out=[]
        for part in self.parts.values():
            item=part.copy();item['vertices']=(np.array(part['vertices'])@rotation.T+anchor).tolist();out.append(item)
        return out
