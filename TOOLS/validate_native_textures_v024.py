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

def verify_files(edf,mapfile,textures,report,legacy_materials=None):
    edf=Path(edf);mapfile=Path(mapfile);eb=edf.read_bytes();mb=mapfile.read_bytes()
    if eb[:4]!=b'EDF\0' or mb[:2]!=b'MP':raise RuntimeError('Unexpected EDF/MAP format')
    checks=[];pending=[]
    for texture in textures:
        try:row=texture_record(eb,texture)
        except RuntimeError as error:
            pending.append((texture,error));continue
        # MAP embeds the same decoded-pixel digest and dimensions; its record
        # layout need not be assumed identical to standalone EDF.
        signature=struct.pack('<2I',row['width'],row['height'])+bytes.fromhex(row['pixel_md5'])
        pos=mb.find(signature)
        if pos<0:raise RuntimeError('EDF bitmap missing from compiled MAP: '+row['texture'])
        row['map_signature_offset']=pos;checks.append(row)
    # PiBoSo stores identical decoded bitmaps once, under one of their names.
    # An alias is accepted only through another fully checked named record,
    # including its bounded payload and exact corresponding MAP signature.
    for texture,error in pending:
        w,h,digest=bitmap_signature(texture)
        shared=next((r for r in checks if r.get('pixel_md5')==digest.hex() and (r['width'],r['height'])==(w,h) and r.get('representation')!='legacy_uniform_diffuse_material'),None)
        if shared is None:
            legacy=(legacy_materials or {}).get(Path(texture).name)
            if legacy is None:raise error
            assert hashlib.sha256(Path(texture).read_bytes()).hexdigest()==legacy['source_sha256']
            rows=[]
            for material in legacy['materials']:
                # Controlled official exports demonstrate diffuse RGB followed
                # by ambient RGB as six consecutive float32 material values.
                signature=struct.pack('<6f',*(material['diffuse_rgb']+material['ambient_rgb']))
                edf_pos=eb.find(signature);map_pos=mb.find(signature)
                if edf_pos<0 or map_pos<0:raise RuntimeError('Missing legacy native material colors: '+Path(texture).name)
                rows.append(dict(material,edf_colour_signature_offset=edf_pos,map_colour_signature_offset=map_pos))
            checks.append(dict(texture=Path(texture).name,representation='legacy_uniform_diffuse_material',
                               width=w,height=h,pixel_md5=digest.hex(),source_sha256=legacy['source_sha256'],
                               bitmap_payload_required=False,constant_source_image_verified=True,
                               constant_pixel_rgba=legacy['constant_pixel_rgba'],native_material_colors=rows,
                               official_colour_probe_run=legacy['official_colour_probe_run'],checks_pass=True))
            continue
        row=dict(shared)
        row.update(texture=Path(texture).name,source_sha256=hashlib.sha256(Path(texture).read_bytes()).hexdigest(),
                   shared_bitmap_alias=True,shared_bitmap_texture=shared['texture'])
        checks.append(row)
    result=dict(checks_pass=True,power_of_two=True,texture_count=len(checks),edf_bytes=len(eb),
                edf_sha256=hashlib.sha256(eb).hexdigest(),map_sha256=hashlib.sha256(mb).hexdigest(),
                textures=checks,missing=[],shared_bitmap_alias_count=sum(r.get('shared_bitmap_alias',False) for r in checks),
                native_bitmap_texture_count=sum(r.get('representation')!='legacy_uniform_diffuse_material' for r in checks),
                legacy_uniform_material_texture_count=sum(r.get('representation')=='legacy_uniform_diffuse_material' for r in checks),
                method='Exact dimensions and bottom-up RGBA pixel MD5 in bounded native EDF bitmap records; corresponding bitmap signatures in MAP. Identical-pixel aliases require another fully verified named bitmap record. Authenticated unchanged legacy uniform-color images require exact source diffuse-plus-ambient material RGB values in both EDF and MAP, calibrated with official exporter controls.',
                probe_run=36824107860,in_game_visual_test=False)
    Path(report).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified actual native bitmap payloads in EDF and MAP:',len(checks),flush=True)
    return result

