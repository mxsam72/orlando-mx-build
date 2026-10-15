"""Orthographic textured-mesh preview with a software depth buffer."""
import numpy as np
from numba import njit
from vtk.util.numpy_support import vtk_to_numpy

@njit(cache=True)
def raster(p,n,uv,faces,tex,depth,image,light,fill,spec):
    H,W=depth.shape;th,tw,channels=tex.shape
    for face in faces:
        ia,ib,ic=face; a=p[ia];b=p[ib];c=p[ic]
        x0=max(0,int(np.floor(min(a[0],b[0],c[0]))));x1=min(W-1,int(np.ceil(max(a[0],b[0],c[0]))))
        y0=max(0,int(np.floor(min(a[1],b[1],c[1]))));y1=min(H-1,int(np.ceil(max(a[1],b[1],c[1]))))
        denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(denominator)<1e-9:continue
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                wa=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/denominator
                wb=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/denominator
                wc=1-wa-wb
                if wa<0 or wb<0 or wc<0:continue
                d=wa*a[2]+wb*b[2]+wc*c[2]
                if d>=depth[y,x]:continue
                u=wa*uv[ia,0]+wb*uv[ib,0]+wc*uv[ic,0]
                v=wa*uv[ia,1]+wb*uv[ib,1]+wc*uv[ic,1]
                tx=(u%1)*tw-.5;ty=(v%1)*th-.5
                ix=int(np.floor(tx));iy=int(np.floor(ty));fx=tx-ix;fy=ty-iy
                colour=np.empty(channels,np.float64)
                for k in range(channels):
                    colour[k]=(tex[iy%th,ix%tw,k]*(1-fx)+tex[iy%th,(ix+1)%tw,k]*fx)*(1-fy)+(tex[(iy+1)%th,ix%tw,k]*(1-fx)+tex[(iy+1)%th,(ix+1)%tw,k]*fx)*fy
                if channels==4 and colour[3]<145:continue
                normal=wa*n[ia]+wb*n[ib]+wc*n[ic]
                norm=np.sqrt(np.sum(normal*normal))
                if norm>1e-9:normal/=norm
                # Two printed sign faces and foliage are two-sided in this
                # review. Both use their saved UVs; no text flip is applied.
                if normal[2]<0:normal=-normal
                diffuse=.35+.65*max(0.,np.sum(normal*light))+.16*max(0.,np.sum(normal*fill))
                half=light+np.array([0.,0.,1.]);half/=np.sqrt(np.sum(half*half))
                highlight=spec*max(0.,np.sum(normal*half))**36*.45
                for k in range(3):image[y,x,k]=min(255.,max(0.,((colour[k]/255)**2.2*diffuse+highlight)**(1/2.2)*255))
                depth[y,x]=d

def render(renderer,width=1800,height=1100):
    cam=renderer.GetActiveCamera();eye=np.array(cam.GetPosition());target=np.array(cam.GetFocalPoint())
    forward=(target-eye);forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,1.,0.]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    basis=np.stack([right,up,-forward],1);scale=height/(2*cam.GetParallelScale())
    depth=np.full((height,width),np.inf,np.float64);image=np.empty((height,width,3),np.float64)
    image[:]=[195.,207.,218.]
    light=np.array([-7.,12.,10.]);light/=np.linalg.norm(light);light=light@basis
    fill=np.array([9.,7.,2.]);fill/=np.linalg.norm(fill);fill=fill@basis
    actors=renderer.GetActors();actors.InitTraversal()
    while True:
        actor=actors.GetNextActor()
        if actor is None:break
        data=actor.GetMapper().GetInput();verts=vtk_to_numpy(data.GetPoints().GetData())
        cells=vtk_to_numpy(data.GetPolys().GetData());faces=[];i=0
        while i<len(cells):
            count=int(cells[i]);poly=cells[i+1:i+1+count]
            for j in range(1,count-1):faces.append([poly[0],poly[j],poly[j+1]])
            i+=count+1
        faces=np.asarray(faces,dtype=np.int64);p=(verts-eye)@basis
        projected=p.copy();projected[:,0]=width/2+p[:,0]*scale;projected[:,1]=height/2-p[:,1]*scale;projected[:,2]=-p[:,2]
        ns=data.GetPointData().GetNormals()
        if ns is None:
            normal=np.zeros_like(verts)
            for f in faces:
                face_normal=np.cross(verts[f[1]]-verts[f[0]],verts[f[2]]-verts[f[0]])
                if face_normal[1]<0:face_normal=-face_normal
                normal[f]+=face_normal
            normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-10)
        else:normal=vtk_to_numpy(ns)
        normal=np.ascontiguousarray(normal@basis)
        tc=data.GetPointData().GetTCoords();uv=vtk_to_numpy(tc) if tc is not None else np.zeros((len(verts),2))
        texture=actor.GetTexture()
        if texture:
            td=texture.GetInput();w,h,_=td.GetDimensions();tex=vtk_to_numpy(td.GetPointData().GetScalars()).reshape(h,w,-1)
        else:tex=np.uint8(np.array(actor.GetProperty().GetColor()).reshape(1,1,3)*255)
        raster(np.ascontiguousarray(projected),normal,np.ascontiguousarray(uv),faces,np.ascontiguousarray(tex),depth,image,light,fill,actor.GetProperty().GetSpecular())
    return np.uint8(np.rint(image))
