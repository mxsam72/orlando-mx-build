#!/usr/bin/env python3
"""Run the validated native Windows compiler as a separate Orlando MX v008b build."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve();ROOT=HERE.parents[1];ORIGINAL=ROOT/'TOOLS/build_windows.py'
if not ORIGINAL.is_file(): raise SystemExit('Missing TOOLS/build_windows.py')
src=ORIGINAL.read_text(encoding='utf-8')
old_name="NAME='orlandomx_2026_v007'"; new_name="NAME='orlandomx_2026_v008b'"
old_dest="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'"; new_dest="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v008b.pkz'"
if old_name not in src or old_dest not in src: raise SystemExit('Validated v007 build script changed; stop and inspect.')
src=src.replace(old_name,new_name,1).replace(old_dest,new_dest,1)
ns={'__name__':'__main__','__file__':str(HERE)}
exec(compile(src,str(HERE),'exec'),ns,ns)
validation=ROOT/'DOCUMENTATION/native_build_validation.json'
if validation.is_file(): shutil.copy2(validation,ROOT/'12_RELEASE/OrlandoMX_v008b_Validation.json')
pkz=ROOT/'12_RELEASE/OrlandoMX_2026_v008b.pkz'
if pkz.is_file():
    install=ROOT/'12_RELEASE/Install_v008b.txt'
    install.write_text(
        'Orlando MX 2026 v008b - color and scenery correction\n\n'
        'Copy OrlandoMX_2026_v008b.pkz into:\nDocuments\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\\n\n'
        'Do not extract or rename the PKZ. v007 and v008 may remain installed separately.\n'
        'v008b preserves v008/v007 track geometry and physics while correcting dirt color and thinning/rescaling tree scenery.\n',encoding='utf-8')
    print('\nSUCCESS:',pkz);print('Also created:',install)
