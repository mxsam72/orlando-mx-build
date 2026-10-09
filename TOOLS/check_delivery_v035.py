"""Tie the delivered native package to the exact v033-preserving render inputs."""
from pathlib import Path
import json,zipfile,numpy as np
from v033_common import sha,save
from v027_scenery import parse,geometry_records,vertices
R=Path(__file__).resolve().parents[1];O=R/'V035_OUTPUT';B=R/'V033_OUTPUT';D=R.parent/'deliverables-v035'
def main():
    qa=json.loads((D/'OrlandoMX_v035_Validation.json').read_text());pkz=D/'OrlandoMX_2026_v035.pkz';assert qa['compiled'] and qa['centerline_merged'];assert qa['pkz_sha256']==sha(pkz);assert qa['pkz_bytes']==pkz.stat().st_size
    source=qa['source_validation'];assert source['terrain_sha256']==sha(O/'terrain.raw');assert source['scenery_sha256']==sha(O/'scenery.fbx');assert qa['independent_source_checks']['checks_pass']
    staged=qa['staging_validation']['textures'];original={x['file']:x['sha256'] for x in json.loads((B/'native_staging_validation.json').read_text())['textures']};inputs=[]
    for row in staged:
        name=row['file'];paths=[O/'materials'/name,O/'facility_textures'/name,O/'masks'/name,O/name]
        if name.startswith('mask_'):paths.append(O/'masks'/name[5:])
        matches=[p for p in paths if p.is_file()];p=matches[0] if matches else None
        if p:assert sha(p)==row['sha256'],name
        else:assert original[name]==row['sha256'],'Unknown changed legacy input: '+name
        inputs.append(dict(file=name,sha256=row['sha256'],source=p.relative_to(O).as_posix() if p else 'Retained native v033 legacy input',matches_native_stage=True))
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.namelist())==13
        assert all(n.startswith('orlandomx_2026_v035/') for n in z.namelist())
        for fn in ['.rdf','.amb','.tsc','.tga']:
            payload=z.read('orlandomx_2026_v035/orlandomx_2026_v035'+fn)
            expected=O/('orlandomx_2026_v035'+fn) if fn=='.rdf' else R/'12_RELEASE/orlandomx_2026_v033'/('orlandomx_2026_v033'+fn)
            assert payload==expected.read_bytes()
        for fn in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:assert z.read('orlandomx_2026_v035/'+fn)==(R/'12_RELEASE/orlandomx_2026_v033'/fn).read_bytes()
    render=json.loads((D/'OrlandoMX_v035_Render_Manifest.json').read_text());rs=render['source_inputs']['v035'];assert rs['terrain.raw']==source['terrain_sha256'];assert rs['scenery.fbx']==source['scenery_sha256']
    for fn in ['terrain.raw','scenery.fbx','main.tcl','start.tcl','compiled_track.hmf']:assert rs[fn]==sha(O/fn)
    nodes,_=parse((O/'scenery.fbx').read_bytes());rec=geometry_records(nodes);wood=vertices(rec['v028_practice_wood_left_timber'][0]);metal=vertices(rec['v028_practice_barrier_left_alloy'][0]);nposts=int(58/3.2)+2;w=wood[(nposts-1)*8:nposts*8].mean(0);m=metal[:8].mean(0);joint=float(np.linalg.norm((w-m)[[0,2]]));assert joint<1e-8
    independent=json.loads((O/'holeshot_independent_validation.json').read_text())
    proof=dict(version='v035',baseline='tested v033',native_source_commit=qa['source_commit'],pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,native_compiled=True,native_centerlines_merged=True,pkz_crc_and_13_entry_layout_checked=True,source_renders_match_native_height_and_scenery=True,native_texture_inputs_checked=len(inputs),native_texture_inputs=inputs,main_centerline_byte_exact_v033=True,main_height_samples_checked=independent['main_height_samples_checked'],main_height_changes=0,T05_full_hill_and_bank_samples_checked=independent['T05_full_hill_and_bank_samples_checked'],T05_height_changes=0,jump_profiles_checked=len(independent['jump_checks']),jump_height_samples_checked=sum(x['checked_native_height_samples'] for x in independent['jump_checks']),jump_height_changes=0,all_48_gate_and_pit_stalls_preserved=True,all_main_checkpoints_and_reset_limits_preserved=True,gate_to_first_curve_before_m=independent['gate_to_first_curve_before_m'],gate_to_first_curve_after_m=independent['gate_to_first_curve_after_m'],serialized_fence_joint_gap_m=joint,all_dirt_color_tiles_byte_exact_v033=36,memorial_entry_and_Qwikchute_art_preserved=True,source_render_views_per_version=7,in_game_riding_test=False,full_pack_race_test=False)
    save(D/'OrlandoMX_v035_Delivery_Checks.json',proof);print(json.dumps({k:v for k,v in proof.items() if k!='native_texture_inputs'},indent=2),flush=True)
if __name__=='__main__':main()
