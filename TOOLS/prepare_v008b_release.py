#!/usr/bin/env python3
"""Create separate v008b support/release folder after v008 preparation and v008b visual fix."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'12_RELEASE/orlandomx_2026_v008'
DST=ROOT/'12_RELEASE/orlandomx_2026_v008b'
if not SRC.is_dir(): raise SystemExit('Missing v008 support folder. Run TOOLS/prepare_v008_local.py first.')
if DST.exists(): shutil.rmtree(DST)
shutil.copytree(SRC,DST)
for p in list(DST.glob('*.map'))+list(DST.glob('*.trh')):
    p.unlink()
old='orlandomx_2026_v008';new='orlandomx_2026_v008b'
for p in list(DST.iterdir()):
    if p.is_file() and p.name.startswith(old):
        p.rename(DST/(new+p.name[len(old):]))
ini=DST/(new+'.ini')
if not ini.is_file(): raise SystemExit('v008b .ini preparation failed')
t=ini.read_text(encoding='utf-8')
t=t.replace('name=Orlando MX 2026 v008','name=Orlando MX 2026 v008b')
t=t.replace('orlandomx_2026_v008.tga','orlandomx_2026_v008b.tga')
t=t.replace('orlandomx_2026_v008_map.tga','orlandomx_2026_v008b_map.tga')
ini.write_text(t,encoding='utf-8')
print('Prepared separate release support folder:',DST)
