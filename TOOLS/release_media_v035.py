"""Compose truthful v033/v035 source comparisons and the downloadable render kit."""
from pathlib import Path
import io,json,zipfile
from PIL import Image,ImageDraw,ImageFont
from v033_common import atomic,sha
R=Path(__file__).resolve().parents[1];OUT=R.parent/'deliverables-v035';OLD=R.parent/'deliverables-v035-checks/v033_output';NEW=R.parent/'deliverables-v035-checks/v035_output'
def font(size,bold=False):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
def save_image(im,name):
    b=io.BytesIO();im.save(b,format='JPEG',quality=95,subsampling=0,optimize=True);atomic(OUT/name,b.getvalue())
def pair(rows,name,title):
    top=150;bottom=112;rowheight=934;im=Image.new('RGB',(3264,top+len(rows)*rowheight+bottom),(21,28,30));d=ImageDraw.Draw(im)
    d.text((24,15),title,font=font(40,True),fill=(244,242,236));d.text((24,69),'Built from v033 · Original main lap, corner and jumps preserved in place',font=font(26),fill=(185,198,191));d.text((24,112),'v033 · TESTED BASELINE',font=font(24,True),fill=(211,191,163));d.text((1640,112),'v035 · UPDATED START',font=font(24,True),fill=(203,224,196))
    for i,(file,label) in enumerate(rows):
        y=top+i*rowheight;d.text((24,y),label,font=font(22),fill=(236,237,232));y+=34
        for col,folder in enumerate([OLD,NEW]):
            src=Image.open(folder/'images'/file);src.load();im.paste(src.resize((1600,900),Image.Resampling.LANCZOS),(24+col*1616,y))
    y=im.height-bottom;d.line((24,y+12,3240,y+12),fill=(63,79,75),width=2);d.text((24,y+28),'Gate run-up: 15.1 m → 45.6 m   |   Straight apron: 38 m wide   |   Main corner movement: 0 m',font=font(26,True),fill=(231,235,223));d.text((24,y+71),'Actual source renders, not game screenshots. v035 in-game riding and full-pack gate-drop testing remain pending.',font=font(22),fill=(172,188,181));save_image(im,name)
def main():
    OUT.mkdir(exist_ok=True)
    pair([('05_Corner_Approach.jpg','Corner after the double: original T05 bank and hill'),('07_Entry_Fence.jpg','Practice entry: fence follows the clay edge and connects to its metal continuation')],'OrlandoMX_v035_Corner_and_Fence_Compare.jpg','Orlando MX · Original corner and connected fencing')
    pair([('03_Overhead.jpg','Overhead start-lane layout'),('02_Holeshot.jpg','Longer broad holeshot approach')],'OrlandoMX_v035_Start_Compare.jpg','Orlando MX · Wider start from the v033 baseline')
    manifest=dict(version='v035',baseline='v033',source_renders_not_game_captures=True,source_inputs={},render_files=[])
    for version,folder,source in [('v033',OLD,R/'V033_OUTPUT'),('v035',NEW,R/'V035_OUTPUT')]:
        proof=json.loads((folder/'manifest.json').read_text());manifest['source_inputs'][version]={fn:sha(source/fn) for fn in ['terrain.raw','scenery.fbx','main.tcl','start.tcl','compiled_track.hmf']};manifest['source_inputs'][version]['masks']={p.relative_to(source).as_posix():sha(p) for place in ['masks','materials'] for p in sorted((source/place).glob('*.tga')) if place=='masks' or p.name.startswith('mask_')};manifest['source_inputs'][version]['camera_manifest']=proof
        for p in sorted((folder/'images').glob('*.jpg')):
            if '_draft' in p.name:continue
            with Image.open(p) as im:im.load();size=list(im.size)
            manifest['render_files'].append(dict(version=version,name=p.name,size=size,sha256=sha(p)))
    atomic(OUT/'OrlandoMX_v035_Render_Manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for version,folder in [('v033_before',OLD),('v035_after',NEW)]:
            for p in sorted((folder/'images').glob('*.jpg')):
                if '_draft' not in p.name:z.writestr(version+'/'+p.name,p.read_bytes())
            for name in ['04_Gate_View.png','05_Corner_Approach.png','07_Entry_Fence.png']:z.writestr(version+'/'+name,(folder/'images'/name).read_bytes())
        for name in ['OrlandoMX_v035_Corner_and_Fence_Compare.jpg','OrlandoMX_v035_Start_Compare.jpg','OrlandoMX_v035_Render_Manifest.json']:z.writestr(name,(OUT/name).read_bytes())
        z.writestr('Independent_Source_Checks.json',(R/'V035_OUTPUT/holeshot_independent_validation.json').read_bytes());z.writestr('README.txt','Orlando MX v035, built directly from tested v033. Matched source renders use each version\'s actual native heightfield, FBX and v033 art/materials. These are external renders, not in-game MX Bikes screenshots. Includes seven views per version: overview, holeshot, overhead, gates, original corner, corner exit/ant hill and connected entry fencing. v035 in-game load/riding, full-pack starts, first-lap timing, resets and FPS remain to be tested.\n')
    atomic(OUT/'OrlandoMX_v035_Render_Kit.zip',buf.getvalue())
    with zipfile.ZipFile(OUT/'OrlandoMX_v035_Render_Kit.zip') as z:assert z.testzip() is None
    print(json.dumps([dict(name=p.name,bytes=p.stat().st_size) for p in OUT.iterdir()]),flush=True)
if __name__=='__main__':main()
