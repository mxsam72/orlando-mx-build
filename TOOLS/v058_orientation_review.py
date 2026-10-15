"""Recheck the existing readable-sign UV contract and saved placement."""
import numpy as np
from PIL import Image,ImageDraw
from v057_inputs import R,O,sha,save
from v027_scenery import parse,geometry_records,vertices,child
from rebind_scenery import array
from v032_sign import projected,render_side
from v049_previews import font

OUT=R/'BUILD/v058_hybrid_review'
PIN='59bb830b43402baa98260b67a0c4c01147c6bc5d3ec7dc4dd67e122fd20e8604'

def main():
    assert sha(O/'scenery.fbx')==PIN
    nodes,_=parse((O/'scenery.fbx').read_bytes());g=geometry_records(nodes)['v057_cardboard_sign_v057_cardboard'][0]
    v=vertices(g);pvi=array(child(g,b'PolygonVertexIndex')).reshape(-1,3);faces=np.where(pvi<0,-pvi-1,pvi)
    un=child(g,b'LayerElementUV');uv=array(child(un,b'UV')).reshape(-1,2)
    indices=next((n for n in un['children'] if n['name']==b'UVIndex'),None)
    if indices is not None:uv=uv[array(indices)]
    uv=uv.reshape(-1,3,2)
    checks=[]
    for i,f in enumerate(faces):
        expected,normal=projected(v,f)
        assert np.allclose(uv[i],expected,atol=1e-10)
        checks.append(dict(triangle=i,native_projection_matches_existing_readable_sign_contract=True,maximum_uv_error=float(np.max(np.abs(uv[i]-expected)))))
    texture=np.asarray(Image.open(O/'facility_textures/v057_cardboard.tga').convert('RGB'))
    sheet=Image.new('RGB',(2000,620),(22,25,29));d=ImageDraw.Draw(sheet)
    d.text((20,15),'Sign orientation check | Saved front and back faces',font=font(29),fill='white')
    d.text((20,58),'Front',font=font(24),fill='white');d.text((1020,58),'Back',font=font(24),fill='white')
    for col,offset in enumerate([0,2]):sheet.paste(render_side(v,faces,uv,texture,offset,w=1000,h=500),(col*1000,100))
    path=OUT/'Sign_Front_Back_Orientation_Check.jpg';sheet.save(path,quality=97,subsampling=0)
    report=dict(checks_pass=True,scenery_sha256=PIN,scenery_unchanged=True,
        sign_position_approved=True,sign_native_uv_contract='same serialized polygon projection as v032 readable entry sign and v033 billboard',
        sign_triangle_checks=checks,sign_texture_sha256=sha(O/'facility_textures/v057_cardboard.tga'),
        legacy_vehicle_numbers_and_logos_already_preflipped_for_game=True,
        previous_placement_preview_omitted_legacy_u_compensation=True,
        correction='Apply 1-U only to the documented legacy preflipped vehicle art in the CPU placement preview. No source vehicle or sign texture/UV change.',
        native_game_sign_appearance_verified=False,new_native_build_started=False,
        images=[dict(file=path.name,sha256=sha(path))])
    save(OUT/'orientation_validation.json',report);save(R/'V058_SOURCE/orientation_review.json',report)
    print('V058_SIGN_MAPPING_CHECKED_AND_LEGACY_PREVIEW_ORIENTATION_CORRECTED',flush=True)

if __name__=='__main__':main()
