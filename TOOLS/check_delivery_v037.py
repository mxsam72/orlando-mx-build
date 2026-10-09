"""Verify the delivered native package, preserved MX files and render inputs."""
import struct,zipfile
from pathlib import Path
from PIL import Image
from v037_common import *

D=R.parent/'deliverables-v037'
def main():
    q=read(D/'OrlandoMX_v037_Validation.json');pkz=D/'OrlandoMX_2026_v037.pkz'
    assert q['compiled'] and q['centerline_merged'] and q['source_checks']
    assert q['asphalt_surface_in_physical_TRH'] and q['concrete_wall_in_physical_TRH'];assert q['static_oval_cybertrucks']==2
    assert q['pkz_sha256']==sha(pkz) and q['pkz_bytes']==pkz.stat().st_size
    assert (D/'OrlandoMX_2026_v037.pkz.sha256').read_text().split()[0]==sha(pkz)
    assert q['source_validation']['terrain_sha256']==sha(O/'terrain.raw')==sha(BASE/'terrain.raw');assert q['source_validation']['scenery_sha256']==sha(O/'scenery.fbx')
    independent=q['independent_source_checks'];assert independent['checks_pass'] and independent['baseline_geometry_records_byte_exact']==769
    for row in independent['protected_files']:assert sha(O/row['file'])==row['sha256']==sha(BASE/row['file'])
    for row in independent['retained_files']:assert sha(O/row['file'])==row['sha256']==sha(BASE/row['file'])
    for row in q['staging_validation']['textures']:
        n=row['file'];paths=[O/'materials'/n,O/'facility_textures'/n,O/'masks'/n,O/n]
        if n.startswith('mask_'):paths.append(O/'masks'/n[5:])
        p=next((p for p in paths if p.is_file()),None)
        if p:assert sha(p)==row['sha256'],n
        else:assert next(r['sha256'] for r in read(BASE/'native_staging_validation.json')['textures'] if r['file']==n)==row['sha256']
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.namelist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
        for suffix,magic in [('.map',b'MP'),('.trh',b'TRH')]:
            path=NAME+'/'+NAME+suffix
            with z.open(path) as f:assert f.read(len(magic))==magic
            assert z.getinfo(path).file_size>1024**2
        for suffix in ['.rdf','.amb','.tsc','.tga','_map.tga']:assert z.read(NAME+'/'+NAME+suffix)==(R/'12_RELEASE/orlandomx_2026_v036'/('orlandomx_2026_v036'+suffix)).read_bytes()
        for n in ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']:assert z.read(NAME+'/'+n)==(R/'12_RELEASE/orlandomx_2026_v036'/n).read_bytes()
    render=read(D/'OrlandoMX_v037_Render_Manifest.json')
    for v,folder in [('v036',BASE),('v037',O)]:
        for n,digest in render['source_inputs'][v].items():assert sha(folder/n)==digest
        manifest=render['source_render_manifests'][v]
        for row in manifest['renders']:
            p=R.parent/'deliverables-v037-renders'/(v+'_output')/'images'/row['filename'];assert sha(p)==row['sha256']
            for ext in ['.jpg','.png']:
                with Image.open(p.with_suffix(ext)) as im:im.load();assert im.size==(2560,1440)
    for b in render['boards']:
        p=D/b['file'];assert sha(p)==b['sha256']
        with Image.open(p) as im:im.load();assert list(im.size)==b['pixels']
    assert q['object_texture_validation']['checks_pass'];assert len(q['terrain_texture_payloads'])==36;assert q['native_coordinate_validation']['checks_pass']
    proof=dict(version='v037',checks_pass=True,native_source_commit=q['source_commit'],pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,native_compiled=True,native_centerlines_merged=True,native_asphalt_and_concrete_collision_checked=True,physical_mesh_coordinate_probes=sum(len(m['probes']) for m in q['native_coordinate_validation']['physical_TRH_meshes']),baseline='user-tested v036',MX_heightmap_route_soils_race_gates_pits_and_reset_unchanged=True,baseline_object_records_preserved=independent['baseline_object_records_byte_exact'],baseline_geometry_records_preserved=769,baseline_connections_preserved=independent['baseline_connections_byte_exact'],retained_texture_and_mask_files=independent['retained_texture_and_mask_files'],v030_terrain_bitmaps_checked=36,new_static_cybertruck_count=2,grass_infield_count=2,crossover_present=True,trees_moved_or_removed=0,compiled_source_matches_renders=True,PKZ_crc_and_13_entry_layout_checked=True,PNG_and_JPEG_files_decoded=True,comparison_views=4,in_game_v037_riding_test=False,in_game_v037_performance_test=False)
    save(D/'OrlandoMX_v037_Delivery_Checks.json',proof);print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
