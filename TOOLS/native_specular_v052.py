"""Verify actual PiBoSo alpha-only specular records against captured native data.

This format is separate from diffuse RGBA and normal-map records. The official
exporter stores a bottom-up 8-bit alpha digest and a small raw-deflate packet.
The layout was inspected in run 38536643719, using the pinned v052 EDF.
"""
import hashlib,struct,zlib
from pathlib import Path
from PIL import Image

def specular_records(raw,path,minimum_records=1):
 path=Path(path)
 with Image.open(path) as source:
  alpha=source.convert('RGBA').getchannel('A');w,h=alpha.size
  expected=alpha.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
 assert w>0 and h>0 and not w&(w-1) and not h&(h-1)
 assert len(expected)==w*h
 digest=hashlib.md5(expected).digest();name=path.stem.encode('ascii')
 assert len(name)<100
 key=name+bytes(100-len(name));pos=raw.find(key);rows=[];candidates=[]
 while pos>=0:
  if pos+136<=len(raw):
   width,height=struct.unpack_from('<2I',raw,pos+100)
   got=raw[pos+108:pos+124];packet=struct.unpack_from('<I',raw,pos+124)[0]
   markers=struct.unpack_from('<2I',raw,pos+128)
   candidates.append(dict(offset=pos,width=width,height=height,alpha_md5=got.hex(),packet_bytes=packet,packet_markers=list(markers)))
   end=pos+128+packet
   if (width,height)==(w,h) and got==digest and 8<packet<128*1024*1024 and end<=len(raw) and markers==(2,0):
    compressed=raw[pos+136:end]
    decoder=zlib.decompressobj(-15);decoded=decoder.decompress(compressed,len(expected)+1)
    decoded+=decoder.flush()
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'Invalid native specular deflate stream'
    assert decoded==expected and hashlib.md5(decoded).digest()==digest,'Native specular pixels differ from source alpha'
    rows.append(dict(texture=path.name,native_name=path.stem,native_record_kind='alpha_only_specular_map',
     record_offset=pos,width=w,height=h,alpha_pixel_md5=digest.hex(),packet_bytes=packet,compressed_bytes=len(compressed),
     decoded_alpha_bytes=len(decoded),decoded_alpha_min=min(decoded),decoded_alpha_max=max(decoded),
     every_decoded_pixel_matches_source=True,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
     checks_pass=True,format_probe_run=38536643719))
  pos=raw.find(key,pos+1)
 if len(rows)<minimum_records:raise RuntimeError('Missing or mismatched alpha-only specular bitmap '+path.name+': '+str(candidates))
 return dict(checks_pass=True,texture=path.name,width=w,height=h,alpha_pixel_md5=digest.hex(),records=rows,
  source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),actual_exported_alpha_verified=True)
