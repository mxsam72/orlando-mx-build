"""Fetch pinned CC0 material bytes, checking source and local hashes."""
import concurrent.futures, hashlib, urllib.request
from v031_common import *

def main():
    catalog = read(S/'scan_catalog.json'); SCANS.mkdir(parents=True,exist_ok=True)
    def transfer(record):
        p=SCANS/record['file']
        if p.is_file() and p.stat().st_size==record['size'] and sha(p)==record['sha256']:return
        request=urllib.request.Request(record['url'],headers={'User-Agent':'OrlandoMX-private-soil-authoring/1.0'})
        with urllib.request.urlopen(request,timeout=150) as response:data=response.read()
        assert len(data)==record['size'] and hashlib.md5(data).hexdigest()==record['md5']
        assert hashlib.sha256(data).hexdigest()==record['sha256']
        atomic(p,data);assert sha(p)==record['sha256']
        print('Verified scan:',p.name,flush=True)
    records=[f for a in catalog['assets'] for f in a['files'].values()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(transfer,records))
    print('Pinned independent soil scan sets verified:',len(catalog['assets']),flush=True)

if __name__=='__main__':main()
