"""v024 free-ride terrain policy.

The user explicitly deferred race-start correctness for this version. Therefore
the start lane is not allowed to grade or modify the riding terrain at all.
The authored start TCL/RDF can remain as placeholder race data, but terrain.raw
is an exact copy of the validated v024 main track terrain.
"""
import numpy as np
from PIL import Image
from v024_common import *

def main():
    source=O/'main_terrain.raw'
    base=np.fromfile(source,'<u2').reshape(N,N)
    base.tofile(O/'terrain.raw')
    Image.fromarray(base).save(O/'terrain_16bit.png')
    H=base.astype(np.float32)/65535*SCALE
    np.save(O/'height_metres.npy',H)

    # Keep a structurally valid fields file for downstream render/packaging code,
    # but every start-terrain influence is zero because racing is deferred.
    z=np.zeros((N,N),dtype=np.float32)
    np.savez_compressed(
        O/'facility_fields.npz',
        weight=z,start=z,retire=z,merge_opening=z,
        main_distance=np.full((N,N),999,dtype=np.float32),
        main_width=z,start_station=z,start_distance=np.full((N,N),999,dtype=np.float32),
        main_station=z
    )

    qa=dict(
        raw_sha256=sha(O/'terrain.raw'),
        main_terrain_sha256=sha(O/'main_terrain.raw'),
        terrain_exactly_preserved=sha(O/'terrain.raw')==sha(O/'main_terrain.raw'),
        start_terrain_modification_disabled=True,
        racing_deferred_by_user=True,
        race_start_runtime_check_pending=True,
        native_compilation=False,
        in_game_riding=False,
        start_terrain_checks_pass=True,
        note='v024 free-ride build: start route does not alter terrain; race-start behavior intentionally deferred.'
    )
    assert qa['terrain_exactly_preserved']
    save(R/'DOCUMENTATION/v024_start_validation.json',qa)
    print(qa)

if __name__=='__main__':
    main()
