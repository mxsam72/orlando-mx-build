"""Assemble the v032 release-post draft and verified source-render gallery."""
from pathlib import Path
import hashlib,json,math,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables-v032-media'

def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    shots=manifest['renders'];assert len(shots)==18
    assert manifest['track_sources_unchanged']
    for s in shots:
        p=OUT/'images'/s['filename'];assert sha(p)==s['sha256']
        with Image.open(p) as im:assert im.size==(2560,1440)
    # Cover typography is over the actual overview, with the same provenance.
    cover=Image.open(OUT/'images/01_Track_Overview.jpg').convert('RGBA')
    overlay=Image.new('RGBA',cover.size);d=ImageDraw.Draw(overlay)
    for y in range(1080,1440):
        alpha=int(218*min(1,(y-1080)/100))
        d.line((0,y,2560,y),fill=(14,20,20,alpha))
    d.rectangle((80,1190,91,1360),fill=(204,52,47,255))
    d.text((120,1180),'ORLANDO MX',font=font(110,True),fill=(247,244,235,255))
    d.text((125,1310),'2026  /  v032  /  Pup Whatley Memorial Edition',font=font(38),fill=(247,244,235,255))
    note='ACTUAL v032 SOURCE RENDER · NOT AN IN-GAME SCREENSHOT'
    d.text((125,1375),note,font=font(22),fill=(191,197,191,255))
    cover=Image.alpha_composite(cover,overlay).convert('RGB')
    cover.save(OUT/'00_MXB_Cover.jpg',quality=95,subsampling=0,optimize=True)
    cols=3;pad=24;cw=640;ih=360;caption=66;rowgap=18;header=132
    rows=math.ceil(len(shots)/cols);width=pad*2+cols*cw+(cols-1)*pad
    height=header+rows*(ih+caption)+(rows-1)*rowgap+pad
    sheet=Image.new('RGB',(width,height),(17,24,23));d=ImageDraw.Draw(sheet)
    d.text((pad,24),'ORLANDO MX 2026 / v032',font=font(44,True),fill=(244,242,233))
    d.text((pad,83),'18 source renders · 2560 × 1440 originals · not in-game screenshots',font=font(24),fill=(178,189,181))
    captions=[]
    for i,s in enumerate(shots):
        x=pad+(i%cols)*(cw+pad);y=header+(i//cols)*(ih+caption+rowgap)
        im=Image.open(OUT/'images'/s['filename']).convert('RGB').resize((cw,ih),Image.Resampling.LANCZOS)
        sheet.paste(im,(x,y));d.rectangle((x,y+ih,x+cw,y+ih+caption),fill=(29,37,33))
        title=f'{i+1:02}  {s["title"]}'
        d.text((x+14,y+ih+8),title,font=font(23,True),fill=(247,246,238))
        subtitle=s['subtitle'].split(' · ')[-1] if s['subtitle'].startswith('R') else s['subtitle']
        if len(subtitle)>49:subtitle=subtitle[:46]+'...'
        d.text((x+14,y+ih+37),subtitle,font=font(18),fill=(180,193,179))
        captions.append(f'{s["filename"]}\n{s["title"]}. {s["subtitle"]}. Actual v032 source render, not an in-game screenshot.\n')
    sheet.save(OUT/'OrlandoMX_v032_Gallery_Preview.jpg',quality=93,subsampling=0,optimize=True)
    (OUT/'Gallery_Captions.txt').write_text('Orlando MX v032 - gallery captions\n\n'+ '\n'.join(captions))
    readme='''Orlando MX v032 - MXB Mods release kit

Start with OrlandoMX_v032_MXB_Post.txt for the post wording. The reusable
structure, suggested form values, gallery order and examples are in
MXB_Track_Post_Template.md.

Images contains 18 full-resolution 2560 x 1440 JPG views. The memorial,
entry sign and Bithlo sign also have lossless PNG versions. 00_MXB_Cover.jpg
is a ready-to-use cover. OrlandoMX_v032_Gallery_Preview.jpg shows all views.
Gallery_Captions.txt provides matching captions.

These are external source renders of actual v032 assets, not game captures.
The terrain, connected textures, vehicles, signs and jumps come from v032.
The rendering camera, daylight, background and shading are set externally.
This renderer does not reproduce all game shaders or vegetation effects.
The images retain a source-render label and are not AI-generated track views.
Some textures and artwork in the existing track were created with AI assistance.

The PKZ is not included in this media kit. Use OrlandoMX_2026_v032.pkz
(523,827,448 bytes), already supplied separately. Add its public download
link, tested game version and any missing contributor credits to the draft.

Visual observation: the current v032 memorial support posts cross narrow
strips of the artwork on both faces. The gallery shows this faithfully;
the source meshes and the PKZ have not been changed for the pictures.

For game screenshots, load v032 and capture the same angles in game.
Check the entry sign on both faces, the memorial, each vehicle pair,
and the takeoffs/landings before selecting a tested version for the post.
'''
    (OUT/'Readme_Release_Kit.txt').write_text(readme)
    # Save reproducibility data, while keeping private repository links out of
    # the public-facing post and image package.
    manifest['cover']=dict(filename='00_MXB_Cover.jpg',sha256=sha(OUT/'00_MXB_Cover.jpg'),provenance='Typography applied to actual overview render; no scene alterations.')
    manifest['gallery_preview']=dict(filename='OrlandoMX_v032_Gallery_Preview.jpg',sha256=sha(OUT/'OrlandoMX_v032_Gallery_Preview.jpg'))
    (OUT/'Render_Provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    pack=OUT/'OrlandoMX_v032_MXB_Release_Kit.zip'
    files=[OUT/'OrlandoMX_v032_MXB_Post.txt',OUT/'MXB_Track_Post_Template.md',OUT/'00_MXB_Cover.jpg',OUT/'OrlandoMX_v032_Gallery_Preview.jpg',OUT/'Gallery_Captions.txt',OUT/'Readme_Release_Kit.txt',OUT/'Render_Provenance.json']
    files+=sorted(p for p in (OUT/'images').iterdir() if p.suffix.lower() in ['.jpg','.png'] and '_draft' not in p.name)
    assert len([p for p in files if p.parent.name=='images'])==21
    with zipfile.ZipFile(pack,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(OUT))
    with zipfile.ZipFile(pack) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
    report=dict(track_sources_unchanged=True,views=18,image_pixels=[2560,1440],lossless_sign_views=3,archive_files=len(files),archive_bytes=pack.stat().st_size,archive_sha256=sha(pack),ready_to_post_after_filling_download_and_test_fields=True)
    (ROOT/'v032-media-work/package_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
