"""Read CRC-checked render inputs from the private compiled-source checkpoint."""
from pathlib import Path
import hashlib, io, json, shutil, sys, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'V035_OUTPUT'
QA = json.loads((ROOT.parent / 'deliverables-v035/OrlandoMX_v035_Validation.json').read_text())

class RemoteZip(io.RawIOBase):
    def __init__(self, asset):
        self.url = asset['download_url']; self.size = asset['bytes']; self.pos = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if self.pos < 0: raise ValueError('Negative archive offset')
        return self.pos
    def read(self, n=-1):
        n = self.size-self.pos if n < 0 else min(n, self.size-self.pos)
        if n <= 0: return b''
        first = self.pos; last = first+n-1
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={first}-{last}'})
        with urllib.request.urlopen(req, timeout=180) as response:
            assert response.status == 206, 'Source server did not honor the byte range'
            assert response.headers['Content-Range'] == f'bytes {first}-{last}/{self.size}'
            data = response.read()
        assert len(data) == n
        self.pos += len(data)
        return data

def main():
    request = json.load(sys.stdin)
    assert request['release_id'] == 407384908 and len(request['assets']) == 1
    asset = request['assets'][0]
    assert asset['name'] == 'OrlandoMX-v035-source-checkpoint.zip'
    assert asset['bytes'] == 975720535
    assert asset['digest'] == 'sha256:24fc8fa0dd7d4e43a1bd513be8933fba595397c588212d0c9c3d4e59d5a6c2fd'
    expected = QA['source_validation']['scenery_sha256']
    with zipfile.ZipFile(RemoteZip(asset)) as archive:
        scene = archive.read('V035_OUTPUT/scenery.fbx')
        assert hashlib.sha256(scene).hexdigest() == expected
        reports = {name: archive.read('V035_OUTPUT/'+name) for name in ['source_validation.json', 'holeshot_scenery_validation.json']}
        assert json.loads(reports['source_validation.json'])['scenery_sha256'] == expected
        assert json.loads(reports['holeshot_scenery_validation.json'])['output_sha256'] == expected
    backup = ROOT.parent / 'private-transfer/v035-linux-scenery.fbx'
    if not backup.exists(): shutil.copyfile(OUT/'scenery.fbx', backup)
    for name, data in {'scenery.fbx': scene, **reports}.items():
        temp = (OUT/name).with_suffix('.native-restore-tmp')
        temp.write_bytes(data); temp.replace(OUT/name)
    print(json.dumps(dict(scenery_bytes=len(scene),scenery_sha256=expected,archive_entry_crc_checked=True,native_compiled_source_matches=True)), flush=True)

if __name__ == '__main__': main()
