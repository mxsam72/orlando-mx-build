"""Authenticate recreated v048 bitmaps and require correct matte/size metadata."""
import json
from v049_surface import R,sha
def main():
    q=json.loads((R/'BUILD/v048_inputs/v048_validation.json').read_text())
    assert q['compiled'] and q['source_checks'] and q['source_commit']=='36ae77927e30d749adc60936fcc548de331927e6'
    for name,row in q['surface_validation']['files'].items():
        if name.endswith('.tga'):assert sha(R/'V048_OUTPUT'/name)==row['sha256'],name
    print('Recreated v048 bitmap reference is exact to the published build.',flush=True)
if __name__=='__main__':main()
