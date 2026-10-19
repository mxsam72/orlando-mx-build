"""Read native payloads rather than trusting converter exit codes or filenames."""
from pathlib import PurePosixPath
import hashlib, mmap, struct
import numpy as np
from PIL import Image


def valid_member(name, prefix):
    p=PurePosixPath(name)
    return not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and name.startswith(prefix)


def bitmap_signature(path):
    with Image.open(path) as im: im=im.convert('RGBA')
    w,h=im.size
    if w&(w-1) or h&(h-1): raise ValueError('Native textures require power-of-two sizes: '+str(path))
    return w,h,hashlib.md5(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()).digest()


def point_checks(data,points,tolerance=.001):
    results=[]
    for point in points:
        point=list(map(float,point));found=data.find(struct.pack('<3f',*point))>=0
        if not found:
            lo,hi=sorted(struct.unpack('<I',struct.pack('<f',point[0]+d))[0] for d in [-tolerance,tolerance])
            if hi-lo>65536: raise ValueError('Probe X crosses zero; choose positive game coordinates.')
            for bits in range(lo,hi+1):
                offset=data.find(struct.pack('<I',bits))
                while offset>=0 and offset+12<=len(data):
                    got=struct.unpack_from('<3f',data,offset)
                    if all(np.isfinite(got)) and max(abs(a-b) for a,b in zip(got,point))<tolerance:
                        found=True;break
                    offset=data.find(struct.pack('<I',bits),offset+1)
                if found:break
        results.append(found)
    if not results or not all(results):raise ValueError('Native scenery vertex mismatch: '+str(results))
    return dict(checks_pass=True,probes=len(results),tolerance_m=tolerance)


def height_checks(raw_path,map_path,trh_path,n=2049):
    expected=np.fromfile(raw_path,'<u2').reshape(n,n)
    with trh_path.open('rb') as f:
        if f.read(4)!=b'TRH\0' or struct.unpack('<2I',f.read(8))!=(n,n):raise ValueError('Native TRH header or dimensions mismatch')
    encoded=np.memmap(trh_path,mode='r',dtype='<u2',offset=12,shape=(n,n))
    got=((encoded.astype(np.uint32)-32768)&65535).astype('<u2')[::-1]
    if not np.array_equal(got,expected):raise ValueError('Native collision heights differ from source')
    flipped=np.ascontiguousarray(expected[::-1]).tobytes();prefix=struct.pack('<2I',n,n)+flipped[:512]
    with map_path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        if data[:4]!=b'MP2\0':raise ValueError('Unexpected native MAP header')
        start=0
        while True:
            at=data.find(prefix,start)
            if at<0:raise ValueError('Native visual height grid differs from source')
            if data[at+8:at+8+len(flipped)]==flipped:break
            start=at+1
    return dict(checks_pass=True,samples_per_grid=n*n,source_visual_and_collision_identical=True,map_height_offset=at+8)


def texture_checks(native_path,paths):
    records=[]
    with native_path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        for path in paths:
            w,h,md5=bitmap_signature(path);at=data.find(struct.pack('<2I',w,h)+md5)
            if at<0:raise ValueError('Native bitmap payload missing: '+path.name)
            records.append(dict(file=path.name,width=w,height=h,pixel_md5=md5.hex(),native_offset=at))
    return records


def package_identity(filename,names,name):
    if filename!=name+'.pkz':raise ValueError('PKZ basename must equal its internal track directory')
    if len(names)!=len(set(names)) or not names or not all(valid_member(n,name+'/') for n in names):raise ValueError('Invalid PKZ member set')
    required=[name+s for s in ['.map','.trh','.rdf','.ini','.amb','.tsc','.tga','_map.tga']]+['minrace.tl','maxrace.tl','checkleft.tl','checkright.tl','marshals.cfg']
    if set(names)!={name+'/'+n for n in required}:raise ValueError('Missing or unexpected game files')
    return True
