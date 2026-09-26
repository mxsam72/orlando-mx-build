#!/usr/bin/env python3
"""Run the existing validated Windows native compiler as v008 without editing v007."""
from pathlib import Path
import json, shutil

HERE=Path(__file__).resolve()
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'TOOLS/build_windows.py'
if not ORIGINAL.is_file():
    raise SystemExit('Missing TOOLS/build_windows.py from the v007 repository.')

src=ORIGINAL.read_text(encoding='utf-8')
old_name="NAME='orlandomx_2026_v007'"
new_name="NAME='orlandomx_2026_v008'"
old_dest="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v007.pkz'"
new_dest="destination=ROOT/'12_RELEASE/OrlandoMX_2026_v008.pkz'"
if old_name not in src or old_dest not in src:
    raise SystemExit('The v007 build script differs from the validated source. Stop and inspect instead of patching blindly.')
src=src.replace(old_name,new_name,1).replace(old_dest,new_dest,1)

# Execute an in-memory v008 variant. The original v007 script on disk is untouched.
ns={'__name__':'__main__','__file__':str(HERE)}
exec(compile(src,str(HERE), 'exec'),ns,ns)

# If the native build returned normally, preserve a version-specific validation copy.
validation=ROOT/'DOCUMENTATION/native_build_validation.json'
if validation.is_file():
    shutil.copy2(validation,ROOT/'12_RELEASE/OrlandoMX_v008_Validation.json')

pkz=ROOT/'12_RELEASE/OrlandoMX_2026_v008.pkz'
if pkz.is_file():
    install=ROOT/'12_RELEASE/Install_v008.txt'
    install.write_text(
        'Orlando MX 2026 v008 - visual update\n\n'
        'Copy OrlandoMX_2026_v008.pkz into:\n'
        'Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\\n\n'
        'Do not extract or rename the PKZ. v007 may remain installed separately.\n'
        'v008 retains v007 geometry and physics masks and changes visual terrain materials/masks.\n',
        encoding='utf-8')
    print('\nSUCCESS:',pkz)
    print('Also created:',install)
