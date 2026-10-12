"""Author the complete dry-weather visual candidate on authenticated v043."""
import shutil,sys,subprocess,base64,io
from PIL import Image
from v044_common import *
def main():
    assert sha(BASE/'terrain.raw')==read(R/'BUILD/v044_baseline_native_validation.json')['source_validation']['terrain_sha256']
    if O.exists():shutil.rmtree(O)
    shutil.copytree(BASE,O)
    from v044_surface_detail import main as surfaces
    from v044_scenery import main as scenery
    from v044_assets import finish
    surfaces();scenery();finish()
    from verify_v044_source import main as verify
    verify()
    # Small diagnostic previews are source authoring views, never game-render claims.
    from v044_source import blob
    summary={key:read(O/key) for key in ['v044_source_validation.json','v044_surface_validation.json','v044_scenery_validation.json']}
    print('CODEX_V044_SOURCE_SUMMARY_BLOB '+blob(json.dumps(summary)),flush=True)
    for fn in ['v044_corner_surface_preview.png','v044_route_atlas_preview.tga']:
        im=Image.open(O/fn);im.thumbnail((1400,1400));buf=io.BytesIO();im.convert('RGB').save(buf,format='JPEG',quality=90)
        print('CODEX_V044_PREVIEW_'+fn.split('.')[0]+'_BLOB '+blob(base64.b64encode(buf.getvalue()).decode()),flush=True)
    print('v044 full standard-weather visuals authored and independently verified.',flush=True)
if __name__=='__main__':main()
