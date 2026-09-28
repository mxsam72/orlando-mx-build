"""Assemble v011 with new start/retirement masks and updated race data."""
import shutil, re
import numpy as np
from PIL import Image
from v011_common import *
from build_v011_start_terrain import fields

def main():
    # Reuse the tested camera/marshal height updates and source texture checks.
    # RDF preservation is checked against the baseline before replacing it below.
    code=(R/'TOOLS/prepare_v009_release.py').read_text(encoding='utf-8')
    code=code.replace('V009_OUTPUT','V011_OUTPUT').replace("NAME='orlandomx_2026_v009'","NAME='orlandomx_2026_v011'")
    code=code.replace('v009_geometry_validation','v011_geometry_validation').replace('V009_SOURCE/v009_geometry_spec','V011_SOURCE/v011_geometry_spec')
    code=code.replace('v009_release_validation','v011_release_validation').replace('Orlando MX 2026 v009','Orlando MX 2026 v011')
    ns={'__name__':'v011_prepare','__file__':__file__};exec(compile(code,__file__,'exec'),ns,ns);ns['main']()
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
    qa=read(R/'DOCUMENTATION/v011_release_validation.json')
    startqa=read(R/'DOCUMENTATION/v011_start_validation.json');raceqa=read(R/'DOCUMENTATION/v011_race_validation.json');sceneqa=read(R/'DOCUMENTATION/v011_scenery_validation.json')
    retired=retire>.95;active=start>.95
    qa.update(version='v011',physics_materials_unchanged=True,physics_surface_masks_changed=True,race_rdf_unchanged=False,main_centerline_alignment_unchanged=True,start_centerline_replaced=True,old_start_alpha_max=float(outputs['start'][retired].max()),new_start_off_alpha_max=float(outputs['off'][active].max()),main_reset_boundaries_preserved=True,shared_native_gate=True,native_compilation=False,in_game_test=False)
    qa['release_source_checks_pass']=bool(startqa['start_terrain_checks_pass'] and raceqa['race_source_checks_pass'] and sceneqa['scenery_checks_pass'] and qa['old_start_alpha_max']==0 and qa['new_start_off_alpha_max']<.05)
    qa['input_sha256']={str(p.relative_to(R)):sha(p) for p in [O/'terrain.raw',O/'scenery.fbx',O/'start.tcl',O/(NAME+'.rdf'),*sorted(maskdir.glob('*.tga'))]}
    save(R/'DOCUMENTATION/v011_release_validation.json',qa)
    if not qa['release_source_checks_pass']:raise RuntimeError('v011 release preflight failed')
    print('v011 release support ready; new masks replace old start surface.')
if __name__=='__main__':main()
