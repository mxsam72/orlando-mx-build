"""Verify real bitmap payloads in PiBoSo native EDF and final MAP.

Calibrated against native FBX2EDF probes from Actions 36824107860. Native
records contain a 100-byte zero-padded extensionless name, width/height,
MD5 of bottom-up RGBA pixels, and a length-delimited compressed payload.
The NPOT negative control has no texture record. A source filename ending
in .tga is not stored in EDF and must never be used as a presence check.
"""
from pathlib import Path
import hashlib,json,struct
from PIL import Image

def bitmap_signature(path):
    with Image.open(path) as source:
        im=source.convert('RGBA')
    w,h=im.size
    if w<1 or h<1 or w&(w-1) or h&(h-1):
        raise ValueError('Unsupported non-power-of-two bitmap: '+str(path))
    digest=hashlib.md5(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()).digest()
    return w,h,digest

def texture_record(raw,path):
    path=Path(path);w,h,digest=bitmap_signature(path);name=path.stem.encode('ascii')
    if len(name)>=100:raise ValueError('Native texture name exceeds known record size')
    key=name+bytes(100-len(name));pos=raw.find(key);candidates=[]
    while pos>=0:
        if pos+144<=len(raw):
            width,height=struct.unpack_from('<2I',raw,pos+104)
            got=raw[pos+112:pos+128];payload=struct.unpack_from('<I',raw,pos+132)[0]
            if (width,height)==(w,h) and got==digest and payload>0 and pos+144+payload<=len(raw):
                return dict(texture=path.name,native_name=path.stem,width=w,height=h,
                            pixel_md5=digest.hex(),record_offset=pos,payload_bytes=payload,
                            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks_pass=True)
            candidates.append(dict(offset=pos,width=width,height=height,md5=got.hex(),payload_bytes=payload))
        pos=raw.find(key,pos+1)
    raise RuntimeError('Missing or mismatched native bitmap payload '+path.name+': '+str(candidates))

def verify_files(edf,mapfile,textures,report):
    edf=Path(edf);mapfile=Path(mapfile);eb=edf.read_bytes();mb=mapfile.read_bytes()
    if eb[:4]!=b'EDF\0' or mb[:2]!=b'MP':raise RuntimeError('Unexpected EDF/MAP format')
    checks=[]
    for texture in textures:
        row=texture_record(eb,texture)
        # MAP embeds the same decoded-pixel digest and dimensions; its record
        # layout need not be assumed identical to standalone EDF.
        signature=struct.pack('<2I',row['width'],row['height'])+bytes.fromhex(row['pixel_md5'])
        pos=mb.find(signature)
        if pos<0:raise RuntimeError('EDF bitmap missing from compiled MAP: '+row['texture'])
        row['map_signature_offset']=pos;checks.append(row)
    result=dict(checks_pass=True,power_of_two=True,texture_count=len(checks),edf_bytes=len(eb),
                edf_sha256=hashlib.sha256(eb).hexdigest(),map_sha256=hashlib.sha256(mb).hexdigest(),
                textures=checks,missing=[],method='Exact dimensions and bottom-up RGBA pixel MD5 in native EDF bitmap records; corresponding bitmap signatures in MAP',
                probe_run=36824107860,in_game_visual_test=False)
    Path(report).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified actual native bitmap payloads in EDF and MAP:',len(checks),flush=True)
    return result
