"""Offline source screenshots for v067 approval; no native compilation.

Run: blender -b --factory-startup -t 8 --python TOOLS/v067_render_previews.py -- --draft
Cycles shading is illustrative; the sun direction and material maps come from
the candidate native inputs. These are not captured in MX Bikes.
"""
from pathlib import Path
import argparse,json,math,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector,Quaternion
import v065_cinematic_render as base

R=Path(__file__).resolve().parents[1]
base.W=R/'BUILD/v067_cinematic';base.B=R/'V067_OUTPUT'
OUT=R/'DOCUMENTATION/v067_review'

def lighting(scene):
    spec=base.read(R/'V067_SOURCE/visual_spec.json')
    az=math.radians(spec['sun_azimuth_xz_degrees']);el=math.radians(spec['sun_elevation_degrees'])
    sun=bpy.data.objects['Presentation sun'];sun.name='Candidate 11 a.m. sun'
    direction=Vector((math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)))
    sun.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    sun.data.energy=3.15;sun.data.angle=math.radians(.65);sun.data.color=spec['clear_sun_rgb']
    world=scene.world;world.name='Clear late morning review'
    for node in world.node_tree.nodes:
        if node.type=='TEX_SKY':
            node.sun_elevation=el;node.sun_rotation=az;node.dust_density=.22
        elif node.type=='BACKGROUND':
            if not node.inputs['Color'].is_linked:
                node.inputs['Color'].default_value=(.53,.59,.69,1);node.inputs['Strength'].default_value=.58
            else:
                node.inputs['Strength'].default_value=.12
    scene.view_settings.exposure=0.0
    return spec

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--draft',action='store_true');ap.add_argument('--shots',default='all')
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True,exist_ok=True)
    scene=base.load_scene();spec=lighting(scene)
    cameras=base.cameras()
    wanted={'09','02','03','04','06','07'}
    cameras=[c for c in cameras if c['name'].split('_')[0] in wanted]
    if args.shots!='all':cameras=[c for c in cameras if c['name'].split('_')[0] in args.shots.split(',')]
    for c in cameras:
        c['name']=c['name'].replace('orlando_','').replace('c_dirt_start_detail','rider_height_start')
    scene.render.resolution_x=1000 if args.draft else 1920
    scene.render.resolution_y=563 if args.draft else 1080
    scene.cycles.samples=20 if args.draft else 56
    scene.cycles.adaptive_min_samples=8 if args.draft else 16
    scene.cycles.adaptive_threshold=.08 if args.draft else .035
    scene.render.threads=8
    folder=OUT/'drafts' if args.draft else OUT;folder.mkdir(exist_ok=True)
    path=folder/'renders.json';manifest=base.read(path) if path.exists() else {}
    rows=[c for c in manifest.get('renders',[]) if c['name'] not in {c['name'] for c in cameras}]
    for cam in cameras:
        start=time.time();obj=scene.camera;obj.location=cam['eye'];direction=Vector(cam['target'])-obj.location
        rot=direction.to_track_quat('-Z','Y')
        if cam.get('roll_degrees'):rot=rot@Quaternion((0,0,1),math.radians(cam['roll_degrees']))
        obj.rotation_euler=rot.to_euler();obj.data.lens=cam['lens']
        # Review images use the whole depth of the scene to reveal defects.
        obj.data.dof.use_dof=False
        image=folder/(cam['name']+'.png');scene.render.filepath=str(image)
        print('V067_RENDER_START',cam['name'],flush=True);bpy.ops.render.render(write_still=True)
        rows.append(dict(cam,file=image.name,render_seconds=round(time.time()-start,1)))
        path.write_text(json.dumps(dict(source_version='v067',source_only=True,in_game_capture=False,
            native_compilation_started=False,lighting_spec=spec,
            preparation=base.read(base.W/'preparation.json'),renders=rows),indent=2)+'\n')
        print('V067_RENDER_SAVED',image,round(time.time()-start,1),flush=True)
    print('V067_REVIEW_COMPLETE',flush=True)
if __name__=='__main__':main()
