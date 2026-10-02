"""v023 readable-graphics QA.

v020 in-game footage showed a horizontal native UV handedness reversal on
readable vehicle/bike decals. v023 compensates by pre-flipping only those
bitmaps before FBX/EDF compilation; the approved Bithlo sign is untouched.
"""
from v023_common import *

EXPECTED={
    'premier_wrap','premier_wrap_right','premier_tail',
    'ford_badge','king_ranch','four_by_four','chevy_badge',
    'jordan_number','premier_number','sam_number','shane_number',
    'jordan_shroud','premier_shroud','sam_shroud','shane_shroud'
}

def main():
    mats=read(S/'vehicle_materials.json')
    fixed={k for k,v in mats.items() if v.get('native_u_preflipped')}
    assert fixed==EXPECTED,(sorted(fixed),sorted(EXPECTED))
    assert 'bithlo_photo' in mats and not mats['bithlo_photo'].get('native_u_preflipped',False)
    meshes=read(O/'vehicle_meshes.json')
    used={m['material'] for m in meshes}
    missing=EXPECTED-used
    assert not missing,('corrected graphic material not used by a mesh',sorted(missing))
    # User specifically called out these surfaces in the v020 in-game test.
    required_user={'premier_wrap','premier_wrap_right','ford_badge','four_by_four',
                   'jordan_number','premier_number','sam_number','shane_number',
                   'jordan_shroud','premier_shroud','sam_shroud','shane_shroud'}
    assert required_user<=fixed
    report=dict(
        version='v023',checks_pass=True,
        correction='horizontal bitmap preflip compensating native MX Bikes UV handedness',
        corrected_materials=sorted(fixed),
        user_reported_surfaces=sorted(required_user),
        ford_front_badge_fixed=True,ford_4x4_fixed=True,
        premier_wrap_fixed=True,bike_numbers_fixed=True,bike_shrouds_fixed=True,
        bithlo_sign_texture_unchanged=True,
        geometry_or_placement_change_required=False,
        in_game_visual_confirmation_pending=True)
    save(R/'DOCUMENTATION/v023_graphics_validation.json',report)
    print('v023 readable graphic handedness checks passed:',len(fixed))
if __name__=='__main__':main()
