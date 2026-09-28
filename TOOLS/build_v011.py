"""Reproducible isolated v011 build with validation after each stage."""
import argparse, subprocess, sys, os
from v011_common import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-only',action='store_true');args=ap.parse_args()
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OPENBLAS_NUM_THREADS='2')
    # Rebuild exact old terrain as an honest comparison baseline. Large inputs
    # restore in BUILD/v009_work and are never modified by v011.
    scripts=['materialize_v009_baseline.py','rebuild_v009_geometry.py','v011_common.py','rebuild_v011_geometry.py','qa_v011_geometry.py','build_v011_start_terrain.py','build_v011_race.py','rebind_v011_scenery.py','facility_mesh_v011.py','append_facilities_v011.py','prepare_v011_release.py','pit_roads_v011.py','render_facilities_v011.py','render_v011_layout.py']
    for script in scripts:
        print('RUN',script,flush=True);subprocess.run([sys.executable,str(R/'TOOLS'/script)],cwd=R,env=env,check=True)
    save(R/'DOCUMENTATION/v011_source_checkpoint.json',dict(version='v011',source_commit=os.environ.get('GITHUB_SHA','local build; see source hashes'),geometry_spec_sha256=sha(S/'v011_geometry_spec.json'),facilities_spec_sha256=sha(S/'facilities.json'),source_checks_pass=True,native_compilation=False,in_game_riding=False,raw_sha256=sha(O/'terrain.raw'),scenery_sha256=sha(O/'scenery.fbx'),start_tcl_sha256=sha(O/'start.tcl'),rdf_sha256=sha(O/(NAME+'.rdf')),provisional_features_disabled=['EX1','EX2']))
    if not args.source_only:subprocess.run([sys.executable,str(R/'TOOLS/build_windows_v011.py')],cwd=R,env=env,check=True)
if __name__=='__main__':main()
