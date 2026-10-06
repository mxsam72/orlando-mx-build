"""Correct the native entry-board UVs on both faces, without moving scenery."""
from v029_common import *
from v027_scenery import parse, encode, child, values, fingerprint, geometry_records
from rebind_scenery import array, encoded_array

def main():
    original=(O/'scenery.fbx').read_bytes(); nodes,tail=parse(original)
    assert encode(nodes,tail)==original
    geometries=geometry_records(nodes); name='v028_track_entry_sign_entry_sign'
    g=geometries[name][0]; uvnode=child(child(g,b'LayerElementUV'),b'UV')
    before=array(uvnode).reshape(4,3,2); corrected=before.copy()
    # PiBoSo's native UV origin is bottom-left. The previous board had
    # V=1 at the bottom. Its reverse faces also need their own U orientation.
    corrected[...,1]=1-corrected[...,1]
    corrected[2:,:,0]=1-corrected[2:,:,0]
    old_fingerprint=fingerprint(g); old_uv=uvnode['props']
    uvnode['props']=encoded_array(corrected)
    output=encode(nodes,tail); again,_=parse(output)
    revised=geometry_records(again)[name][0]
    assert np.array_equal(array(child(child(revised,b'LayerElementUV'),b'UV')).reshape(4,3,2),corrected)
    # Prove that ONLY this single UV property changed in the whole FBX.
    uvnode['props']=old_uv
    assert encode(nodes,tail)==original and fingerprint(g)==old_fingerprint
    mesh=next(m for m in read(O/'pit_facility_meshes.json') if m['name']==name)
    vertex=np.asarray(mesh['vertices']); top=vertex[:,1].max(); low=vertex[:,1].min()
    # Stored native triangle vertex order is reversed from the authored mesh.
    for i,face in enumerate(mesh['faces']):
        y=vertex[list(reversed(face)),1]
        assert np.all(corrected[i,y==top,1]==1) and np.all(corrected[i,y==low,1]==0)
    allmeshes=read(O/'pit_facility_meshes.json')
    for m in allmeshes:
        if m['name']==name:m['uv']=corrected[:,::-1,:].tolist()
    save(O/'pit_facility_meshes.json',allmeshes)
    (O/'scenery.fbx').write_bytes(output)
    save(O/'entry_sign_validation.json',dict(checks_pass=True,mesh=name,
        prior_native_uv=before.tolist(),corrected_native_uv=corrected.tolist(),
        top_vertices_use_v_one=True,bottom_vertices_use_v_zero=True,
        reverse_faces_use_mirrored_u_for_readable_text=True,
        only_entry_board_uv_property_changed=True,vertices_materials_textures_connections_unchanged=True,
        in_game_visual_check=False))
    print('v029 native entry sign UV orientation corrected on both faces',flush=True)

if __name__=='__main__':main()
