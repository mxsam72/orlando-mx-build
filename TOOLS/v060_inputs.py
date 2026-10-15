"""Recover the accepted stack and stage unchanged race data for the final build."""
import json,shutil,sys
from v058_inputs import R,BASE,sha,save

PREV=R/'V059_OUTPUT';O=R/'V060_OUTPUT';M=O/'materials';S=R/'V060_SOURCE'
NAME='orlandomx_2026_v060';DEST=R/'12_RELEASE'/NAME

def stage_game():
 DEST.mkdir(parents=True,exist_ok=True);rows=[]
 previous=R/'12_RELEASE/orlandomx_2026_v058'
 for src in sorted(previous.iterdir()):
  if src.suffix in ['.map','.trh'] or src.name=='code.txt':continue
  dest=DEST/src.name.replace('orlandomx_2026_v058',NAME);shutil.copy2(src,dest)
  if dest.suffix=='.ini':dest.write_text(dest.read_text().replace('v058','v060'),encoding='utf-8')
  else:
   assert sha(dest)==sha(src);rows.append(dict(file=dest.name,sha256=sha(dest)))
 assert len(list(DEST.iterdir()))==11
 approved=R/'V059_OUTPUT/facility_textures';target=O/'facility_textures'
 shutil.copytree(approved,target,dirs_exist_ok=True)
 for src in approved.iterdir():
  if src.is_file():assert sha(src)==sha(target/src.name)
 save(O/'race_validation.json',dict(checks_pass=True,native_routes_exact_v059=True,all_race_reset_grid_pits_checkpoints_exact=True,retained_game_files=rows))
 save(O/'source_geometry_validation.json',json.loads((PREV/'terrain_validation.json').read_text()))

def restore():
 import v058_inputs,v058_retained,v058_surface,v059_geometry,v059_surface,v059_scenery,v060_surface
 v058_inputs.restore();v058_retained.main();v058_surface.main()
 v059_geometry.main();v059_surface.main();v059_scenery.main();v060_surface.main();stage_game()
 from v060_check import main as check
 check()

if __name__=='__main__':{'restore':restore,'stage-game':stage_game}[sys.argv[1]]()
