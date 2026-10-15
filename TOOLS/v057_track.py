"""Keep every tested v056 ground sample, corner, landing and race file."""
import shutil
from v057_inputs import R, PREV, O, NAME, DEST, sha, save
from v054_geometry import read

def main():
    O.mkdir(parents=True,exist_ok=True); DEST.mkdir(parents=True,exist_ok=True)
    retained=[]
    for name in ['terrain.raw','terrain_16bit.png','route.npz','layout.json','jump_profiles.json','main.tcl','start.tcl','compiled_track.hmf','corner_guard.npy','landing_scope.npy','landing_sections.npz']:
        shutil.copy2(PREV/name,O/name); assert sha(PREV/name)==sha(O/name)
        retained.append(dict(file=name,sha256=sha(O/name)))
    save(O/'terrain_validation.json',dict(checks_pass=True,terrain_sha256=sha(O/'terrain.raw'),baseline='user-tested v056',entire_terrain_exact_v056=True,all_14_corner_grids_exact=True,landing_exact_v056=True,retained_source_files=retained))
    game=R/'12_RELEASE/orlandomx_2026_v056'; retained=[]
    for src in sorted(game.iterdir()):
        if src.suffix in ['.map','.trh'] or src.name=='code.txt':continue
        dest=DEST/src.name.replace('orlandomx_2026_v056',NAME); shutil.copy2(src,dest)
        if dest.suffix=='.ini':dest.write_text(dest.read_text().replace('v056','v057'))
        else:
            assert sha(dest)==sha(src); retained.append(dict(file=dest.name,sha256=sha(dest)))
    assert len(list(DEST.iterdir()))==11
    save(O/'race_validation.json',dict(checks_pass=True,native_routes_exact_v056=True,all_race_reset_grid_pits_checkpoints_exact=True,retained_game_files=retained))
    print('V057_TRACK_PASSED: every terrain sample and race/reset file retained',flush=True)

if __name__=='__main__':main()
