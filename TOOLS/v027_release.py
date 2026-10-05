"""Copy accepted v026 support files for v027, retagging version identity once."""
from pathlib import Path
import shutil,hashlib

R=Path(__file__).resolve().parents[1]
NAME='orlandomx_2026_v027'
BASE_NAME='orlandomx_2026_v026'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def copy_release_inputs():
    src=R/'12_RELEASE'/BASE_NAME
    dst=R/'12_RELEASE'/NAME
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    text_suffixes={'.rdf','.ini','.amb','.tsc','.cfg','.txt'}
    renamed=[]
    for p in src.iterdir():
        if not p.is_file():
            continue
        newname=p.name.replace('v026','v027').replace('V026','V027')
        target=dst/newname
        data=p.read_bytes()
        if p.suffix.lower() in text_suffixes:
            # Retag exactly once and preserve original newline/encoding bytes.
            data=data.replace(b'v026',b'v027').replace(b'V026',b'V027')
        target.write_bytes(data)
        renamed.append(dict(source=p.name,target=newname,source_sha256=sha(p),
                            output_sha256=sha(target)))
    required=[NAME+'.rdf',NAME+'.ini',NAME+'.amb',NAME+'.tsc',NAME+'.tga',NAME+'_map.tga',
              'minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']
    missing=[x for x in required if not (dst/x).is_file()]
    if missing:
        raise RuntimeError('Missing v026b release source files: '+repr(missing))
    if any('v02727' in p.name.lower() for p in dst.iterdir()):
        raise RuntimeError('Release identity was renamed more than once')
    # Race, reset and marshal data contain no version aliases and stay exact.
    protected=[(BASE_NAME+'.rdf',NAME+'.rdf')]+[(x,x) for x in
               ['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']]
    for a,b in protected:
        if sha(src/a)!=sha(dst/b):
            raise RuntimeError('Protected release race/reset data changed: '+a)
    return dict(release_inputs_checked=True,race_reset_marshals_exact_v026=True,
                identity_retagged_once=True,files=renamed)
