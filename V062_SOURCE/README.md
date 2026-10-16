# v062 dirt and grooming comparison trials

Baseline: commit `1002097379ee7e74b57971bd26f29c40eee98144`, including the
new v061 speedway wall roller. Every candidate hardlinks the exact accepted
terrain, scenery, route, main/start centreline and jump profiles. No native
compilation or PKZ release is started by this branch.

The v060 test-lap video shows two relevant failures: dense crosswise normal
stripes cut across turns, and high-frequency photographic dirt loses contrast
on approach. The source used a 3 m repeated photograph for both fine and macro
colour; it lacked unique larger-scale albedo variation. The requested extra
crosswise pass in v059/v060 made the flow cues worse when ridden.

Three candidates replace that crosswise pass:

- A: irregular chunky till through corners, with broken lengthwise cultivation
  on jump faces. The corner clods are normal relief, not collision changes.
- B: unequal-spaced cultivation furrows following a continuous projection of
  the real riding line, throughout corners and along jump faces.
- C: fewer, wider, broken riding ruts in mixed loam with churned shoulders.

All three add clod/patch-scale albedo variation through the existing packed-soil
blend mask and a darker photographic packed-soil tile. The detailed loose
photograph keeps its accepted 3 m repeats and receives a 22% increase in fine
contrast around a 10 pixel local blur. The fine scanned normals remain exact.
The same 8K macro normal slot and wear mask are reused. Normal alpha remains
unchanged. All 14 terrain layers, all image sizes and base RGBA8 image
allocation are unchanged in every candidate. No coarse colour overlay is used.

The proposed clear-day lighting lowers ambient fill from [0.44, 0.49, 0.56]
to [0.30, 0.34, 0.40] and clear fog density from 0.00030 to 0.00018. Sun colour
and position remain exact, keeping the light direction aligned with existing
native shadow generation. Cloudy/rainy settings remain unchanged. Rendering
uses approximate ambient/direct shading, actual normal maps and terrain
shadows; it cannot guarantee the native engine's final look or filtering.

Seven matching cameras cover corner 01 approach and berm, the R03 takeoff,
corner 03 approach and full-width turn, R04 and corner 09 after R10. Current
v060 dirt and all three candidates use matching proposed daylight for the
design comparisons. A separate control holds style B fixed while comparing
the original/proposed ambient and fog. Scenery is omitted from dirt studies.

Reproduce from the repository root (NumPy, SciPy, Pillow, Matplotlib, Shapely
and Numba installed):

```bash
python TOOLS/v061_inputs.py
python TOOLS/v061_roller.py
python - <<'PY'
from pathlib import Path
import zipfile
p=Path('BUILD/v062_inputs');p.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('BUILD/v061_inputs/OrlandoMX-v060-source-checkpoint.zip') as z:
    name=next(n for n in z.namelist() if n.endswith('.amb'))
    (p/'baseline_v060.amb').write_bytes(z.read(name))
PY
OPENBLAS_NUM_THREADS=1 python TOOLS/v062_trials.py
OPENBLAS_NUM_THREADS=1 python TOOLS/v062_review.py
```

`trial_validation.json` documents actual retained file hashes, candidate image
inventory, unchanged allocation and source checks. `preview_review.json`
documents cameras, file hashes, layer sampling and distance contrast. An
in-game test after selecting a design remains necessary. No unseen native
lighting or performance verification is claimed.
