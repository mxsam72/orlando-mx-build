"""Correct horizontal orientation using native polygon projections on both faces."""
from v032_common import *
from v027_scenery import parse,encode,child,geometry_records,fingerprint
from rebind_scenery import array,encoded_array
from PIL import ImageDraw
from scipy.ndimage import map_coordinates

def projected(vertices,indices):
    face=vertices[indices]
    normal=np.cross(face[1]-face[0],face[2]-face[0]);normal/=np.linalg.norm(normal)
    right=np.cross([0.,1.,0.],normal);right/=np.linalg.norm(right)
    x=vertices@right
    u=(x[indices]-x.min())/(x.max()-x.min())
    y=vertices[indices,1]
    v=(y-vertices[:,1].min())/np.ptp(vertices[:,1])
    return np.column_stack([u,v]),normal

def render_side(vertices,faces,uv,texture,offset,w=360,h=500):
    out=np.full((h,w,3),234,dtype=np.uint8)
    for i in range(offset,offset+2):
        expected,_=projected(vertices,faces[i]);xy=np.column_stack([expected[:,0]*(w-1),(1-expected[:,1])*(h-1)])
        yy,xx=np.mgrid[:h,:w];a,b,c=xy
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb
        inside=(wa>=-1e-6)&(wb>=-1e-6)&(wc>=-1e-6)
        u=wa*uv[i,0,0]+wb*uv[i,1,0]+wc*uv[i,2,0]
        v=wa*uv[i,0,1]+wb*uv[i,1,1]+wc*uv[i,2,1]
        coords=np.array([(1-v)*(texture.shape[0]-1),u*(texture.shape[1]-1)])
        rgb=np.stack([map_coordinates(texture[...,k],coords,order=1,mode='nearest') for k in range(3)],axis=-1)
        out[inside]=rgb[inside]
    return Image.fromarray(out)

def main():
    original=(O/'scenery.fbx').read_bytes();nodes,tail=parse(original)
    assert encode(nodes,tail)==original
    name='v028_track_entry_sign_entry_sign';g=geometry_records(nodes)[name][0]
    vertices=array(child(g,b'Vertices')).reshape(-1,3)*[.01,.01,-.01]
    faces=[];face=[]
    for index in array(child(g,b'PolygonVertexIndex')):
        face.append(int(index) if index>=0 else -int(index)-1)
        if index<0:faces.append(face);face=[]
    assert not face and len(faces)==4 and all(len(f)==3 for f in faces)
    node=child(child(g,b'LayerElementUV'),b'UV');before=array(node).reshape(4,3,2);corrected=before.copy()
    corrected[...,0]=1-corrected[...,0]
    checks=[]
    for i,f in enumerate(faces):
        expected,normal=projected(vertices,f)
        assert np.allclose(before[i,:,0],1-expected[:,0],atol=1e-10),'Unexpected tested-v030 U orientation'
        assert np.allclose(corrected[i],expected,atol=1e-10),'Native viewing-direction projection mismatch'
        checks.append(dict(triangle=i,normal=normal.tolist(),expected_uv=expected.tolist(),horizontal_orientation_readable=True))
    assert np.array_equal(before[...,1],corrected[...,1])
    old_properties=node['props'];old_fingerprint=fingerprint(g)
    node['props']=encoded_array(corrected);output=encode(nodes,tail)
    again,_=parse(output);revised=geometry_records(again)[name][0]
    assert np.array_equal(array(child(child(revised,b'LayerElementUV'),b'UV')).reshape(4,3,2),corrected)
    node['props']=old_properties;assert encode(nodes,tail)==original and fingerprint(g)==old_fingerprint
    atomic(O/'scenery.fbx',output)
    meshes=read(O/'pit_facility_meshes.json')
    for mesh in meshes:
        if mesh['name']==name:mesh['uv']=corrected[:,::-1,:].tolist()
    save(O/'pit_facility_meshes.json',meshes)
    save(O/'entry_sign_validation.json',dict(checks_pass=True,mesh=name,prior_native_uv=before.tolist(),corrected_native_uv=corrected.tolist(),all_native_u_flipped=True,vertical_orientation_unchanged=True,view_projection_checks=checks,both_faces_readable_in_native_projection=True,only_entry_board_uv_property_changed=True,vertices_materials_textures_connections_unchanged=True,in_game_visual_check=False))
    texture=np.asarray(Image.open(O/'facility_textures/v028_entry_sign.tga').convert('RGB'))
    preview=Image.new('RGB',(820,1160),(246,245,241));draw=ImageDraw.Draw(preview)
    draw.text((24,12),'Native polygon UV projection - source check, not game screenshots',fill=(30,30,30))
    for row,offset in enumerate((0,2)):
        y=52+row*554
        for col,(label,uv) in enumerate((('v030: mirrored',before),('v032: readable',corrected))):
            x=28+col*410;draw.text((x,y),f'Face {row+1} | '+label,fill=(30,30,30))
            preview.paste(render_side(vertices,faces,uv,texture,offset),(x,y+24))
    save_png(preview,O/'sign_projection_check.png')
    print('Both native sign-face projections are upright and horizontally readable.',flush=True)

if __name__=='__main__':main()
