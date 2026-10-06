"""Corrected grass scope with the tested v028 coordinates and terrain."""
from v028_common import *
S=R/'V030_SOURCE'; O=R/'V030_OUTPUT'; M=O/'materials'
BASE=R/'V028_OUTPUT'
NAME='orlandomx_2026_v030'

def save_png(image_or_figure,path,**kwargs):
    """Verify buffered PNG bytes before atomically publishing a preview."""
    import io
    from PIL import Image
    buffer=io.BytesIO()
    if hasattr(image_or_figure,'savefig'):
        image_or_figure.savefig(buffer,format='png',**kwargs)
    else:
        image_or_figure.save(buffer,format='PNG',**kwargs)
    raw=buffer.getvalue();Image.open(io.BytesIO(raw)).verify()
    path=Path(path);temporary=path.with_suffix('.png.tmp')
    with temporary.open('wb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    Image.open(temporary).verify();temporary.replace(path)
