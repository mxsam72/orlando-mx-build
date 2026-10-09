"""Package checked source renders, comparisons and native build evidence."""
import json,zipfile
from pathlib import Path
from PIL import Image
from v036_common import sha,read,save
from check_delivery_v036 import main as verify,D,R

def main():
    verify()
    qa=read(D/'OrlandoMX_v036_Validation.json')
    manifest=read(D/'OrlandoMX_v036_Render_Manifest.json')
    manifest.update(native_source_commit=qa['source_commit'],native_pkz_sha256=qa['pkz_sha256'],
        native_input_match_verified=True,native_texture_inputs_checked=len(qa['staging_validation']['textures']))
    archive_inputs=[]
    for version,part in manifest['source_render_manifests'].items():
        for row in part['renders']:
            images=R.parent/'deliverables-v036-renders'/(version+'_output')/'images'
            jpg=images/row['filename'];png=jpg.with_suffix('.png')
            with Image.open(jpg) as im:im.load();assert list(im.size)==row['pixels']
            with Image.open(png) as im:im.load();assert list(im.size)==row['pixels']
            assert sha(jpg)==row['sha256']
            row.update(png_filename=png.name,png_sha256=sha(png))
            archive_inputs.extend([(png,version+'/'+png.name),(jpg,version+'/'+jpg.name)])
    for row in manifest['comparison_boards']:
        p=D/row['file'];assert sha(p)==row['sha256']
        with Image.open(p) as im:im.load();assert list(im.size)==row['pixels']
        archive_inputs.append((p,'Comparisons/'+p.name))
    identity=R.parent/'v036-review/compiled_source_identity.json'
    if identity.is_file():manifest['compiler_source_archive']=read(identity)
    save(D/'OrlandoMX_v036_Render_Manifest.json',manifest)
    for name in ['OrlandoMX_v036_Render_Manifest.json','OrlandoMX_v036_Delivery_Checks.json','OrlandoMX_v036_Validation.json']:
        archive_inputs.append((D/name,'Verification/'+name))
    path=D/'OrlandoMX_v036_Renders.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
        z.writestr('README.txt',
            'Orlando MX 2026 v036 - source render review\n\n'
            'Includes eight v036 views, seven matched v035 views, and three before/after comparison boards.\n'
            'The renders use the actual terrain, scenery and texture inputs checked against the compiled Windows build.\n'
            'These are external source renders, not MX Bikes screenshots. Lighting may differ in game.\n\n'
            'Approved changes: unified start/merge soil, a new rounded entry single, 30% taller existing small jumps,\n'
            'and the eight-roller corridor shifted to the rider-right line with a later left sweep.\n'
            'Tested start geometry, the double-to-ant-hill corner, other jump cores, v030 palette and pit signage are retained.\n\n'
            'Native compilation and package/source checks passed. In-game riding, full-pack starts, timing, resets and FPS testing remain pending.\n')
        for source,name in archive_inputs:z.write(source,name)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None and len(z.namelist())==37
    print(json.dumps(dict(archive=path.name,bytes=path.stat().st_size,sha256=sha(path),CRC_checked=True,entries=37),indent=2))

if __name__=='__main__':main()
