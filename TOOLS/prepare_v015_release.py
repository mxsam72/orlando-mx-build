"""Assemble v015 with new start/retirement masks and updated race data."""
import shutil, re
import numpy as np
from PIL import Image
from v015_common import *
from build_v015_start_terrain import fields

def main():
    # Reuse the tested camera/marshal height updates and source texture checks.
    # RDF preservation is checked against the baseline before replacing it below.
    code=(R/'TOOLS/prepare_v009_release.py').read_text(encoding='utf-8')
    code=code.replace('V009_OUTPUT','V015_OUTPUT').replace("NAME='orlandomx_2026_v009'","NAME='orlandomx_2026_v015'")
    code=code.replace('v009_geometry_validation','v015_geometry_validation').replace('V009_SOURCE/v009_geometry_spec','V015_SOURCE/v015_geometry_spec')
    code=code.replace('v009_release_validation','v015_release_validation').replace('Orlando MX 2026 v009','Orlando MX 2026 v015')
    ns={'__name__':'v015_prepare','__file__':__file__};exec(compile(code,__file__,'exec'),ns,ns);ns['main']()
    W=R/'BUILD/v009_work';dest=R/'12_RELEASE'/NAME
    for name in [NAME+'.rdf','minrace.tl','maxrace.tl','checkleft.tl','checkright.tl']:shutil.copy2(O/name,dest/name)
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE
    f=fields(H,(2048,2048)); main=f['main_distance']<f['main_width']/2+1
    maskdir=O/'masks';maskdir.mkdir(exist_ok=True)
    def alpha(name):return np.array(Image.open(W/'03_MASKS'/f'{name}.tga').convert('RGBA').getchannel('A').resize((2048,2048)),dtype=np.float32)/255
    old_start=alpha('start');pits=alpha('pits');retire=old_start*(1-main)*(1-pits)
    start=f['start']*ease((f['main_distance']-f['main_width']/2)/2)
    clear=np.maximum(start,retire)
    outputs={}
    for name in ['start','off','racing','shoulder','grass','sand','worked','visual_racing','visual_worked','visual_grass']:
        original=alpha(name)
        if name=='start':a=start
        elif name=='off':a=np.maximum(original,retire)*(1-start)
        elif name in ['racing','shoulder']:a=np.maximum(original*(1-retire),start)
        elif name in ['grass','visual_grass']:a=np.maximum(original,retire*.75)*(1-start)
        elif name=='sand':a=original*(1-start)
        elif name=='worked':a=original*(1-clear)
        elif name=='visual_racing':
            v=np.array(Image.open(O/'visual_masks'/f'{name}.tga').getchannel('A'),dtype=np.float32)/255;a=np.maximum(v*(1-retire),start*.98)
        else:
            # Remove the old repeated painted twin grooves. Physical corner
            # ruts now follow individually authored paths in the terrain.
            v=np.array(Image.open(O/'visual_masks'/f'{name}.tga').getchannel('A'),dtype=np.float32)/255
            a=np.maximum(v*.45*(1-retire),start*.20)
        a=np.clip(a,0,1);im=Image.new('RGBA',(2048,2048),'white');im.putalpha(Image.fromarray(np.uint8(np.round(a*255))));im.save(maskdir/f'{name}.tga');outputs[name]=a
    # Physics declarations still use existing native surface/material names.
    # Only their masks change. Shared gate model is spawned by the native grid.
    qa=read(R/'DOCUMENTATION/v015_release_validation.json')
    startqa=read(R/'DOCUMENTATION/v015_start_validation.json');raceqa=read(R/'DOCUMENTATION/v015_race_validation.json');sceneqa=read(R/'DOCUMENTATION/v015_scenery_validation.json')
    retired=retire>.95;active=start>.95
    qa.update(version='v015',physics_materials_unchanged=True,physics_surface_masks_changed=True,race_rdf_unchanged=False,main_centerline_alignment_unchanged=True,start_centerline_replaced=True,old_start_alpha_max=float(outputs['start'][retired].max()),new_start_off_alpha_max=float(outputs['off'][active].max()),main_reset_boundaries_preserved=True,shared_native_gate=True,native_compilation=False,in_game_test=False)
    layoutqa=read(R/'DOCUMENTATION/v015_layout_validation.json');geometryqa=read(R/'DOCUMENTATION/v015_geometry_validation.json')
    qa['release_source_checks_pass']=bool(geometryqa['geometry_checks_pass'] and layoutqa['layout_checks_pass'] and startqa['start_terrain_checks_pass'] and raceqa['race_source_checks_pass'] and sceneqa['scenery_checks_pass'] and sceneqa['material_checks_pass'] and qa['old_start_alpha_max']==0 and qa['new_start_off_alpha_max']<.05)
    qa['input_sha256']={str(p.relative_to(R)):sha(p) for p in [O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),*sorted(maskdir.glob('*.tga'))]}
    save(R/'DOCUMENTATION/v015_release_validation.json',qa)
    if not qa['release_source_checks_pass']:raise RuntimeError('v015 release preflight failed')
    print('v015 release support ready; new masks replace old start surface.')
if __name__=='__main__':main()
