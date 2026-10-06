"""Retag the tested v027 support files once; retain races, resets and logo."""
from v028_common import *
import shutil

def copy_release_inputs():
    src=R/'12_RELEASE/orlandomx_2026_v027';dst=R/'12_RELEASE'/NAME
    if dst.exists():shutil.rmtree(dst)
    dst.mkdir(parents=True);records=[]
    for p in src.iterdir():
        if not p.is_file() or p.suffix.lower() in ['.map','.trh']:continue
        target=dst/p.name.replace('v027','v028').replace('V027','V028');data=p.read_bytes()
        if p.suffix.lower() in ['.rdf','.ini','.amb','.tsc','.cfg','.txt']:data=data.replace(b'v027',b'v028').replace(b'V027',b'V028')
        target.write_bytes(data);records.append(dict(source=p.name,target=target.name,source_sha256=sha(p),output_sha256=sha(target)))
    required=[NAME+x for x in ['.rdf','.ini','.amb','.tsc','.tga','_map.tga']]+['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']
    assert sorted(p.name for p in dst.iterdir())==sorted(required),'Unexpected v028 release support set'
    for a,b in [('orlandomx_2026_v027.rdf',NAME+'.rdf')]+[(x,x) for x in required if not x.startswith(NAME)]+[('orlandomx_2026_v027.tga',NAME+'.tga')]:
        assert sha(src/a)==sha(dst/b),'Protected race/reset/logo bytes changed'
    return dict(release_inputs_checked=True,race_reset_marshals_and_menu_logo_exact_v027=True,identity_retagged_once=True,files=records)
