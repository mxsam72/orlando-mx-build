"""Preserve the exact corrected Orlando MX Park preview, separately from map."""
import base64,zlib,hashlib
from v024_common import *

def main():
    src=read(S/'menu_logo_tga.json');data=zlib.decompress(base64.b64decode(src['data']));assert hashlib.sha256(data).hexdigest()==src['sha256'];assert len(data)==src['bytes']
    dest=R/'12_RELEASE'/NAME;dest.mkdir(parents=True,exist_ok=True);p=dest/(NAME+'.tga');p.write_bytes(data)
    course=dest/(NAME+'_map.tga');assert course.exists() and sha(course)!=src['sha256']
    report=dict(checks_pass=True,logo_sha256=sha(p),exact_corrected_v018_logo=True,course_map_sha256=sha(course),separate_files=True)
    save(R/'DOCUMENTATION/v024_menu_logo_validation.json',report);print('Exact Orlando MX Park menu logo preserved')
if __name__=='__main__':main()
