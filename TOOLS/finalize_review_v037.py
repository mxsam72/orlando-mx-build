"""Bundle the verified renders and checks without duplicating the game package."""
import zipfile
from v037_common import R, read, save, sha

D=R.parent/'deliverables-v037';MEDIA=R.parent/'deliverables-v037-renders'
def main():
    proof=read(D/'OrlandoMX_v037_Delivery_Checks.json');assert proof['checks_pass']
    manifest=read(D/'OrlandoMX_v037_Render_Manifest.json');archive=D/'OrlandoMX_v037_Renders_and_Checks.zip';temp=archive.with_suffix('.zip.tmp');catalog=[]
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for version,views in manifest['source_render_manifests'].items():
            for shot in views['renders']:
                p=MEDIA/(version+'_output')/'images'/shot['filename']
                for suffix in ['.jpg','.png']:
                    file=p.with_suffix(suffix);name=version+'/'+file.name;z.write(file,name);catalog.append(dict(path=name,bytes=file.stat().st_size,sha256=sha(file)))
        names=[b['file'] for b in manifest['boards']]+['OrlandoMX_v037_Render_Manifest.json','OrlandoMX_v037_Delivery_Checks.json','OrlandoMX_v037_Validation.json','Install_v037.txt','OrlandoMX_2026_v037.pkz.sha256']
        for name in names:
            p=D/name;target='checks_and_previews/'+name;z.write(p,target);catalog.append(dict(path=target,bytes=p.stat().st_size,sha256=sha(p)))
    with zipfile.ZipFile(temp) as z:
        assert z.testzip() is None and len(z.namelist())==len(catalog)
    temp.replace(archive)
    save(D/'OrlandoMX_v037_Render_Archive.json',dict(version='v037',checks_pass=True,file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),entries=catalog,source_render_views_v036=4,source_render_views_v037=7,external_source_renders_not_in_game_screenshots=True))
    print('Verified render bundle:',archive.name,'entries:',len(catalog),'bytes:',archive.stat().st_size,flush=True)
if __name__=='__main__':main()
