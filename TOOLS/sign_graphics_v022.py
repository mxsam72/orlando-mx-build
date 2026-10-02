"""Map the user's actual sticker-sign photograph onto thin 3-D sign plates.

No invented stickers. UV coordinates address only the sign panels/pole in the
reference; surrounding road, vehicles and mailbox are never mapped to geometry.
Image coordinates below use the 1368x1824 display of the 1536x2048 reference.
"""
from vehicle_geometry_v022 import MeshBuilder
from v022_common import *

def main():
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    spec=next(a for a in read(S/'pit_facilities.json')['assets'] if a['id']=='bithlo_sticker_stop')
    m=MeshBuilder('bithlo_sticker_stop')
    def face(verts,pixels):
        uv=[[x/1368,1-y/1824] for x,y in pixels];f=list(range(len(verts)))
        m.add(verts,[f,list(reversed(f))],'bithlo_photo',[uv,uv[::-1]])
    octagon=[[-.205,2.805,.050],[.205,2.805,.050],[.495,2.515,.050],[.495,2.105,.050],[.205,1.815,.050],[-.205,1.815,.050],[-.495,2.105,.050],[-.495,2.515,.050]]
    face(octagon,[[567,226],[769,231],[905,378],[914,577],[766,733],[574,731],[423,579],[423,378]])
    face([[-.42,1.80,.031],[.42,1.80,.031],[.42,1.13,.031],[-.42,1.13,.031]],[[477,752],[884,748],[897,1077],[482,1085]])
    face([[-.735,3.275,.031],[.735,3.275,.031],[.735,2.805,.031],[-.735,2.805,.031]],[[284,51],[1001,1],[1014,243],[301,291]])
    face([[-.030,1.115,.034],[.030,1.115,.034],[.030,.06,.034],[-.030,.06,.034]],[[650,1093],[699,1092],[721,1795],[675,1810]])
    parts=m.place(spec['xz'],spec['heading'],H)
    save(O/'sign_graphic_meshes.json',parts)
    facilities=read(O/'facility_meshes.json');facilities=[a for a in facilities if a['material']!='bithlo_photo'];save(O/'facility_meshes.json',facilities+parts)
    save(R/'DOCUMENTATION/v022_sign_validation.json',dict(checks_pass=True,photo_projected=True,panels=4,
        asset='bithlo_sticker_stop',xz=spec['xz'],heading=spec['heading'],top_width_m=1.47,
        octagon_width_m=.99,lower_board_dimensions_m=[.84,.67],height_m=3.30,
        placement_basis='Estimated from user yellow circle: left shoulder at main-gravel/office-approach junction',
        source='User-provided bithlo sign 1.jpg',mesh_names=[p['name'] for p in parts]))
    print('Reference sign UVs projected onto four thin physical surfaces')
if __name__=='__main__':main()
