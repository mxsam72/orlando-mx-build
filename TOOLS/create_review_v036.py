"""Assemble comparisons from matched, actual source renders."""
import hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'deliverables-v036-renders'
D=ROOT/'deliverables-v036'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b)
    return h.hexdigest()

def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)

def main():
    D.mkdir(exist_ok=True)
    before=json.loads((R/'v035_output/manifest_01,02,03,04,05,06,07.json').read_text())
    after=json.loads((R/'v036_output/manifest.json').read_text())
    old={r['id']:r for r in before['renders']}
    new={r['id']:r for r in after['renders']}
    groups=[('Start','Clear start and merge surface','The tested start shape, gate positions and fence remain in place.',[
        ('01_Start_Overhead','Start overhead','Conflicting pale and groomed bands removed from the riding lane.'),
        ('02_Start_View','View from the gates','One brown surface makes the run toward the first corner clear.')]),
        ('Small_Jumps','Extra single and 30% taller small jumps','Existing jump footprints and spacing are retained.',[
        ('03_Small_Jumps','Rhythm section overview','Existing low double and four rolling singles raised by 30%.'),
        ('04_New_Single','New entry single','Rounded 0.75 m single after the tabletop corner, before the low double.')]),
        ('Rollers','The right-hand line becomes the centre','Eight rollers retained; the route holds right longer before the left sweep.',[
        ('05_Rollers_Overhead','Roller corridor overhead','Centre shifted up to 4.8 m to the rider\'s right.'),
        ('06_Rollers_Entry','Approach through the rollers','Terrain, soil masks and markers follow the new corridor together.'),
        ('07_Rollers_Exit','Roller exit','The route blends back before the unchanged final inside roller.')])]
    boards=[];metrics=[]
    W=3840;pad=40;gap=28;col=(W-pad*2-gap)//2;ih=round(col*1440/2560)
    for stem,title,subtitle,rows in groups:
        H=260+len(rows)*(ih+104)+94
        board=Image.new('RGB',(W,H),(20,26,29));dr=ImageDraw.Draw(board)
        dr.text((pad,26),'ORLANDO MX 2026  /  v036',font=font(29,True),fill=(223,187,83))
        dr.text((pad,74),title,font=font(55,True),fill=(245,244,239))
        dr.text((pad,146),subtitle,font=font(29),fill=(190,200,202))
        dr.text((pad,211),'v035  ·  BEFORE',font=font(31,True),fill=(200,205,207))
        dr.text((pad+col+gap,211),'v036  ·  APPROVED UPDATE',font=font(31,True),fill=(223,187,83))
        for i,(key,label,caption) in enumerate(rows):
            a,b=old[key],new[key]
            for c in ('pos','focus','fov','box','tex','step'):
                assert a[c]==b[c],(key,c,'Camera/input mismatch')
            ims=[]
            for version,record in [('v035',a),('v036',b)]:
                file=R/(version+'_output')/'images'/record['filename']
                assert sha(file)==record['sha256']
                im=Image.open(file).convert('RGB');assert im.size==(2560,1440)
                ims.append(im)
            import numpy as np
            aa,bb=(np.asarray(im).astype('int16') for im in ims)
            # Exclude the provenance label from the physical comparison.
            delta=np.abs(aa[:1340]-bb[:1340]);changed=float((delta.max(axis=2)>3).mean())
            assert changed>.0005,(key,'No visible update')
            metrics.append(dict(view=key,cameras_identical=True,changed_pixel_fraction=changed,mean_absolute_RGB_difference=float(delta.mean())))
            y=260+i*(ih+104)
            for j,im in enumerate(ims):board.paste(im.resize((col,ih),Image.Resampling.LANCZOS),(pad+j*(col+gap),y))
            dr.text((pad,y+ih+14),label,font=font(30,True),fill=(245,244,239))
            dr.text((pad+690,y+ih+15),caption,font=font(27),fill=(190,200,202))
        dr.text((pad,H-64),'Matched views of actual track source. External renders; not MX Bikes screenshots. In-game testing is pending.',font=font(27),fill=(171,182,184))
        p=D/('OrlandoMX_v036_'+stem+'_Comparison.png');board.save(p)
        boards.append(dict(file=p.name,pixels=[W,H],sha256=sha(p),views=[x[0] for x in rows]))
    source_inputs={}
    for version,manifest in [('v035',before),('v036',after)]:
        o=ROOT/'v036-work'/(version.upper()+'_OUTPUT')
        source_inputs[version]={name:sha(o/name) for name in ('terrain.raw','scenery.fbx','main.tcl','start.tcl','compiled_track.hmf')}
        for key,value in manifest['source_sha256'].items():assert source_inputs[version][key]==value
    result=dict(version='v036',baseline='tested v035',source_inputs=source_inputs,matched_cameras=True,render_comparisons=metrics,comparison_boards=boards,source_render_manifests={'v035':before,'v036':after},render_type='External source renders, not MX Bikes screenshots',in_game_riding_test=False)
    (D/'OrlandoMX_v036_Render_Manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(boards=boards,matched_views=len(metrics)),indent=2))

if __name__=='__main__':main()
