"""Recover an already verified native PKZ after Actions artifact quota failure.

The native build and all validations completed successfully before the upload
step failed. Pin the diagnostic checkpoint, restore its exact bytes, verify the
full package and source again, and save the normal private release delivery.
"""
import hashlib, json, os, sys, urllib.request, urllib.error, urllib.parse, zipfile
from pathlib import Path
import v039_release_transfer as transfer
from v039_common import atomic, R, O, BASE, NAME, read, sha

EXPECTED_PKZ_BYTES=423041686
EXPECTED_PKZ_SHA='dc09a98cfa76785a10a95ea4cc5ae5d6d4e53dcc02a6023db5ecc42246336d1a'
EXPECTED_NATIVE_SOURCE_COMMIT='886df32cf534e2895da9e9811f4731b9c2de84c7'

def main():
    repo=transfer.api('');assert repo['private']
    release=transfer.api('/releases/407729450');assert release['draft']
    assets=[a for a in release['assets'] if a['name']=='OrlandoMX-v039-diagnostics.zip'];assert len(assets)==1
    asset=assets[0];assert asset['size']==1260166427 and asset['digest']=='sha256:383e7afffac6b5f9bc9923550a309b3f49fd7ab6b680779ca365514187a471be'
    try:
        urllib.request.build_opener(transfer.NoRedirect).open(urllib.request.Request(asset['url'],headers=transfer.HEADERS|{'Accept':'application/octet-stream'}),timeout=120)
        raise RuntimeError('Expected private native checkpoint redirect')
    except urllib.error.HTTPError as e:
        if e.code not in (301,302,303,307,308):raise
        location=e.headers['Location']
    assert urllib.parse.urlparse(location).hostname in ('release-assets.githubusercontent.com','objects.githubusercontent.com')
    path=R/'BUILD/v039-verified-recovery.zip';path.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();count=0
    with urllib.request.urlopen(location,timeout=180) as response,path.open('wb') as out:
        while b:=response.read(4*1024*1024):out.write(b);digest.update(b);count+=len(b)
    assert count==asset['size'] and digest.hexdigest()==asset['digest'].removeprefix('sha256:')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for info in z.infolist():
            if info.is_dir():continue
            name=info.filename;assert '..' not in Path(name).parts
            if name.startswith(('V039_OUTPUT/','DOCUMENTATION/','12_RELEASE/orlandomx_2026_v039/')) or name=='12_RELEASE/OrlandoMX_2026_v039.pkz':atomic(R/name,z.read(info))
    # Restore the same frozen v038 source and original pit mesh manifests for
    # exact independent source comparison and the complete authoring checkpoint.
    transfer.source()
    from verify_v039_source import main as verify_source
    verify_source()
    qa=read(R/'DOCUMENTATION/v039_native_validation.json');pkz=R/'12_RELEASE/OrlandoMX_2026_v039.pkz'
    assert qa['compiled'] and qa['centerline_merged'] and qa['source_checks']
    assert qa['source_commit']==EXPECTED_NATIVE_SOURCE_COMMIT
    assert qa['pkz_sha256']==EXPECTED_PKZ_SHA==sha(pkz)
    assert qa['pkz_bytes']==EXPECTED_PKZ_BYTES==pkz.stat().st_size and EXPECTED_PKZ_BYTES<500000000
    assert qa['independent_source_checks']['checks_pass'] and qa['native_coordinate_validation']['checks_pass'] and qa['object_texture_validation']['checks_pass']
    assert qa['source_validation']['scenery_sha256']==sha(O/'scenery.fbx')
    dest=R/'12_RELEASE'/NAME
    with zipfile.ZipFile(pkz) as z:
        assert z.testzip() is None and len(z.infolist())==13 and all(n.startswith(NAME+'/') for n in z.namelist())
        for info in z.infolist():
            with z.open(info) as src:
                h=hashlib.sha256()
                while b:=src.read(4*1024*1024):h.update(b)
            assert h.hexdigest()==sha(dest/Path(info.filename).name)
    atomic(R/'12_RELEASE/OrlandoMX_v039_Validation.json',(json.dumps(qa,indent=2)+'\n').encode())
    atomic(R/'12_RELEASE/OrlandoMX_2026_v039.pkz.sha256',(EXPECTED_PKZ_SHA+'  OrlandoMX_2026_v039.pkz\n').encode())
    atomic(R/'12_RELEASE/Install_v039.txt',('Orlando MX 2026 v039\n\nCopy OrlandoMX_2026_v039.pkz to Documents\\PiBoSo\\MX Bikes\\mods\\tracks\\motocross\\ and select Orlando MX 2026 v039.\n\nThe Orlando Speed World graphic reads correctly on both sides. Both Qwikchute signs have flat opaque image faces with the black backboards removed and at least 18 cm support clearance. Textures, positions, track geometry, oval and red/black grass parking are retained from v038.\n\nOfficial Windows native compilation, geometry and texture probes, independent source preservation and archive CRC checks passed. In-game v039 riding/visibility verification remains pending. Keep v038 for comparison; all multiplayer clients and the server need the same v039 version.\n').encode())
    print('Recovered exact verified native v039 PKZ:',EXPECTED_PKZ_BYTES,EXPECTED_PKZ_SHA,flush=True)
    transfer.deliver()

if __name__=='__main__':main()
