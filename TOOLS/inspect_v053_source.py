"""Prepare accepted photographic soil and route inputs for local v053 authoring QA."""
import json,zipfile
from pathlib import Path
from PIL import Image
from v052_transfer import restore
from v052_surface import R,BASE,DIRT,sha,save

def main():
    restore()
    files=[BASE/'terrain.raw',BASE/'route.npz',BASE/'jump_profiles.json',DIRT/'compiled_track.hmf',DIRT/'materials/mask_v046_section.tga']
    for family in ['loose','packed']:
        files.extend(DIRT/'materials'/f'v045_{family}{suffix}' for suffix in ['.tga','_n.tga','.shd'])
    out=R/'BUILD/v053_authoring_inputs';out.mkdir(parents=True,exist_ok=True)
    report={'files':{p.relative_to(R).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files}}
    for p in files:
        if p.suffix=='.tga' and 'mask_' not in p.name:
            im=Image.open(p);report[p.name]={'size':list(im.size),'mode':im.mode}
            im.convert('RGB').resize((1024,1024),Image.Resampling.BOX).save(out/(p.stem+'.jpg'),quality=95)
    save(out/'source_report.json',report)
    archive=out/'v053_authoring_inputs.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(R).as_posix())
    print((DIRT/'compiled_track.hmf').read_text(),flush=True)
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
