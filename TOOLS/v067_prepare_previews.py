"""Prepare actual v067 geometry/textures for offline source-review renders."""
import json
import v065_cinematic_prepare as prep
import v067_surface as candidate

def main():
    prep.O=candidate.O;prep.S=candidate.S;prep.source=candidate.source
    prep.W=candidate.R/'BUILD/v067_cinematic';prep.T=prep.W/'textures'
    prep.IMAGE_CACHE.clear()
    # Keep source detail at full 4K for the three dirt colors/tiled normals.
    original=prep.image_file
    def high_quality(path,kind='color',limit=2048):
        if path.name in candidate.CHANGED and limit==2048:limit=4096
        return original(path,kind,limit)
    prep.image_file=high_quality
    prep.main()
    data=json.loads((prep.W/'preparation.json').read_text())
    data.update(source_version='v067',native_compilation_started=False,
        lighting_spec_sha256=candidate.sha(candidate.S/'visual_spec.json'))
    candidate.save(prep.W/'preparation.json',data)
if __name__=='__main__':main()
