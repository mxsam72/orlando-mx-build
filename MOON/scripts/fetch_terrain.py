"""Extract LROC lunar DEM windows with checked HTTP byte ranges."""
from pathlib import Path
import concurrent.futures as cf
import hashlib,json,math,tempfile,time,urllib.request
import numpy as np
import rasterio,tifffile
from rasterio.windows import Window,from_bounds
from pyproj import CRS,Transformer
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pds.mcp.nasa.gov/data/store/img/lunar_reconnaissance_orbiter/pds4/lroc/lro-l-lroc-5-rdr/LROLRC_2001/DATA/SDP/NAC_DTM/'
LON,LAT=30.625359173611393,20.217170263230255

def get_range(url,start,end):
 for attempt in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'}),timeout=120) as r:
    data=r.read();assert r.status==206 and r.headers['Content-Range'].startswith(f'bytes {start}-{end}/') and len(data)==end-start+1
    return data,int(r.headers['Content-Range'].split('/')[-1])
  except Exception:
   if attempt==3:raise
   time.sleep(1+attempt)

def extract(product,folder,half_extent,outname,stride=1):
 dest=ROOT/'source'/outname
 if dest.exists():return
 url=BASE+folder+'/'+product+'.TIF';header,total=get_range(url,0,262143)
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'transport.tif'
  with path.open('wb') as f:f.write(header);f.truncate(total)
  with rasterio.open(path) as ds:
   crs=CRS.from_wkt(ds.crs.to_wkt());cx,cy=Transformer.from_crs(crs.geodetic_crs,crs,always_xy=True).transform(LON,LAT)
   w=from_bounds(cx-half_extent,cy-half_extent,cx+half_extent,cy+half_extent,ds.transform)
   c0,r0=math.floor(w.col_off),math.floor(w.row_off);c1,r1=math.ceil(w.col_off+w.width),math.ceil(w.row_off+w.height)
   assert 0<=c0<c1<=ds.width and 0<=r0<r1<=ds.height;w=Window(c0,r0,c1-c0,r1-r0)
  with tifffile.TiffFile(path) as t:
   p=t.pages[0];assert p.compression==1 and p.rowsperstrip==1
   start=p.dataoffsets[r0];end=p.dataoffsets[r1-1]+p.databytecounts[r1-1]-1
  chunks=[(s,min(end,s+8388607)) for s in range(start,end+1,8388608)]
  print(product,round((end-start+1)/1e6,1),'MB',flush=True)
  with cf.ThreadPoolExecutor(max_workers=6) as pool,path.open('r+b') as f:
   futures={pool.submit(get_range,url,a,b):a for a,b in chunks}
   for future in cf.as_completed(futures):
    data,_=future.result();f.seek(futures[future]);f.write(data)
  with rasterio.open(path) as ds:
   data=ds.read(1,window=w)[::stride,::stride]
   transform=ds.window_transform(w)*rasterio.Affine.translation((1-stride)/2,(1-stride)/2)*rasterio.Affine.scale(stride)
   profile=ds.profile.copy();profile.update(width=data.shape[1],height=data.shape[0],transform=transform,compress='deflate',predictor=3)
   profile.pop('blockysize',None);profile.pop('blockxsize',None)
   with rasterio.open(dest,'w',**profile) as out:out.write(data,1)
  meta=dict(product=product,url=url,source_pixel_size_m=2 if '2M' in product else 5,extraction_window_pixels=[c0,r0,c1-c0,r1-r0],sample_stride=stride,sample_centers_preserved=True,shorty_reference_lonlat=[LON,LAT],shorty_projected_xy_m=[cx,cy],sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),source_vertical_exaggeration=1,crs=profile['crs'].to_wkt(),valid_fraction=float(np.mean(data>-1e20)),height_range_m=[float(data[data>-1e20].min()),float(data.max())])
  dest.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print('Saved',outname,flush=True)

if __name__=='__main__':
 (ROOT/'source').mkdir(parents=True,exist_ok=True)
 extract('NAC_DTM_APOLLO17_2M','APOLLO17_2M',1800,'shorty_2m.tif')
 extract('NAC_DTM_APOLLO17','APOLLO17',12000,'valley_context_20m.tif',4)
