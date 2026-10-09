"""Tie the delivered native v036 package to the actual render inputs."""
import json,zipfile
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter1d
from scipy.signal import find_peaks
from v036_common import R,O,BASE,NAME,sha,save,read

D=R.parent/'deliverables-v036'

def roller_peaks(folder):
    p=next(p for p in read(folder/'jump_profiles.json') if p['id']=='R17')
    q=np.load(folder/'route.npz')['q'];ss=p['station_start_m']+np.arange(801)*.1
    xx=np.interp(ss,q[:,3],q[:,0]);zz=np.interp(ss,q[:,3],q[:,1])
    h=np.fromfile(folder/'terrain.raw','<u2').reshape(2049,2049).astype(float)/65535*18
    profile=map_coordinates(h,[(600-zz)/600*2048,xx/600*2048],order=1)
    smooth=gaussian_filter1d(profile,1.3)
    peaks,props=find_peaks(smooth,prominence=.08,distance=65)
    assert len(peaks)==8,(folder,len(peaks))
    return dict(offsets_m=(peaks*.1).tolist(),absolute_crest_heights_m=smooth[peaks].tolist(),peak_prominences_m=props['prominences'].tolist())

def main():
    qa=read(D/'OrlandoMX_v036_Validation.json');pkz=D/'OrlandoMX_2026_v036.pkz'
    assert qa['compiled'] and qa['centerline_merged']
    assert qa['source_commit']=='00b6d460451b02aa1aedb19b7c6b4b894b460357'
    assert qa['pkz_sha256']==sha(pkz) and qa['pkz_bytes']==pkz.stat().st_size
    assert (D/'OrlandoMX_2026_v036.pkz.sha256').read_text().split()[0]==sha(pkz)
    source=qa['source_validation'];assert source['source_checks_pass']
    assert source['terrain_sha256']==sha(O/'terrain.raw')
    assert source['scenery_sha256']==sha(O/'scenery.fbx')
    independent=qa['independent_source_checks'];assert independent['checks_pass']
    render=read(D/'OrlandoMX_v036_Render_Manifest.json')
    for version,folder in [('v035',BASE),('v036',O)]:
        for name,value in render['source_inputs'][version].items():assert value==sha(folder/name),(version,name)
    assert render['source_inputs']['v036']['terrain.raw']==source['terrain_sha256']
    assert render['source_inputs']['v036']['scenery.fbx']==source['scenery_sha256']
    retained={row['file']:row['sha256'] for row in read(BASE/'native_staging_validation.json')['textures']}
    inputs=[]
    for row in qa['staging_validation']['textures']:
        name=row['file'];paths=[O/'materials'/name,O/'facility_textures'/name,O/'masks'/name,O/name]
        if name.startswith('mask_'):paths.append(O/'masks'/name[5:])
        p=next((p for p in paths if p.is_file()),None)
        if p:assert sha(p)==row['sha256'],name
        else:assert retained[name]==row['sha256'],('Changed legacy input',name)
        inputs.append(dict(file=name,sha256=row['sha256'],source=p.relative_to(O).as_posix() if p else 'Retained native v035 input',matches_native_stage=True))
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.namelist())==13
        assert all(name.startswith(NAME+'/') for name in z.namelist())
        for suffix in ['.map','.trh']:
            with z.open(NAME+'/'+NAME+suffix) as f:head=f.read(4)
            with (R/'12_RELEASE/orlandomx_2026_v035'/('orlandomx_2026_v035'+suffix)).open('rb') as f:assert head==f.read(4)
            assert z.getinfo(NAME+'/'+NAME+suffix).file_size>1024**2
        for suffix in ['.rdf','.amb','.tsc','.tga']:
            payload=z.read(NAME+'/'+NAME+suffix)
            expected=O/(NAME+suffix) if suffix=='.rdf' else R/'12_RELEASE/orlandomx_2026_v035'/('orlandomx_2026_v035'+suffix)
            assert payload==expected.read_bytes(),suffix
        for name in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:
            assert z.read(NAME+'/'+name)==(O/name).read_bytes(),name
    before=roller_peaks(BASE);after=roller_peaks(O)
    difference=np.asarray(after['absolute_crest_heights_m'])-before['absolute_crest_heights_m']
    offset_difference=np.asarray(after['offsets_m'])-before['offsets_m']
    assert np.max(np.abs(difference))<.05,('Roller height drift',difference)
    assert np.max(np.abs(offset_difference))<.8,('Roller spacing drift',offset_difference)
    assert independent['T05_changed_samples']==0 and independent['start_apron_changed_height_samples']==0
    assert all(row['changed_samples']==0 for row in independent['unchanged_jump_checks'])
    assert len(independent['small_jump_measured_height_checks'])==6 and independent['height_factor']==1.3
    assert independent['preserved_gate_pit_start_blocks']==51 and independent['v030_tiles_byte_exact']==36
    assert independent['facility_art_textures_byte_exact'] and not independent['roller_corridor_obstructions']
    assert qa['memorial_native_coordinate_checks']['checks_pass']
    assert qa['object_texture_validation']['checks_pass']
    assert len(qa['terrain_texture_payloads'])==36
    assert qa['update_scenery_validation']['all_other_records_byte_exact']
    assert qa['update_scenery_validation']['all_connections_byte_exact']
    assert qa['update_race_validation']['checks_pass']
    proof=dict(version='v036',baseline='tested v035',native_source_commit=qa['source_commit'],checks_pass=True,
        pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,native_compiled=True,native_centerlines_merged=True,
        pkz_crc_and_13_entry_layout_checked=True,source_renders_match_native_height_and_scenery=True,
        native_texture_inputs_checked=len(inputs),native_texture_inputs=inputs,compiled_terrain_bitmaps_checked=36,
        T05_samples_checked=independent['T05_checked_samples'],T05_height_changes=0,start_apron_height_changes=0,
        unchanged_jump_checks=independent['unchanged_jump_checks'],small_jump_factor=1.3,
        small_jump_native_height_checks=independent['small_jump_measured_height_checks'],
        new_single_native_height_m=independent['new_single_measured_height_m'],
        roller_count_before=8,roller_count_after=8,roller_native_surface_checks=dict(before=before,after=after,
        maximum_absolute_crest_height_difference_m=float(np.max(np.abs(difference))),maximum_peak_station_difference_m=float(np.max(np.abs(offset_difference)))),
        gates_pits_and_start_checkpoint_blocks_preserved=51,v030_palette_tiles_byte_exact=36,
        memorial_Qwikchute_entry_art_and_pit_vehicles_preserved=True,protected_scenery_and_connections_preserved=True,
        source_render_views_v035=7,source_render_views_v036=8,matched_comparison_views=7,
        in_game_riding_test=False,in_game_visual_test=False,full_pack_race_test=False,performance_test=False)
    save(D/'OrlandoMX_v036_Delivery_Checks.json',proof)
    print(json.dumps({k:v for k,v in proof.items() if k not in ['native_texture_inputs','unchanged_jump_checks','small_jump_native_height_checks']},indent=2))

if __name__=='__main__':main()
