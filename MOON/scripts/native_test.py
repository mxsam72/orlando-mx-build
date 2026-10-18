"""Compile and validate Moon v002 with pinned official Windows authoring tools."""
from pathlib import Path
import argparse,hashlib,json,mmap,os,queue,re,shutil,struct,subprocess,sys,threading,time,urllib.request,zipfile
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[2];M=R/'MOON';B=M/'build';G=B/'game';NAME='taurus_littrow_mx_v002';LOG=M/'native_logs';LOG.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'TOOLS'))
from validate_native_textures_v024 import bitmap_signature,texture_record
from native_coordinate_scan_v044 import scan_points

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8',newline='\n')
def run(exe,args,label,timeout=10800):
 print('MOON_NATIVE_START',label,flush=True)
 start=time.monotonic();last=start;q=queue.Queue();tail='';error=False
 p=subprocess.Popen([str(exe),*map(str,args)],cwd=B,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
 try:
  import psutil
  process=psutil.Process(p.pid)
 except Exception as exc:
  process=None;print('MOON_PROCESS_MONITOR_UNAVAILABLE',type(exc).__name__,flush=True)
 def reader():
  try:
   while True:
    block=os.read(p.stdout.fileno(),4096)
    if not block:break
    q.put(block.decode('utf-8',errors='replace'))
  except OSError:pass
  finally:q.put(None)
 t=threading.Thread(target=reader,daemon=True);t.start()
 def snapshot():
  state=dict(label=label,elapsed_seconds=round(time.monotonic()-start,1),pid=p.pid)
  if process is not None:
   try:
    cpu=process.cpu_times();mem=process.memory_info();io=process.io_counters()
    state.update(cpu_seconds=round(cpu.user+cpu.system,1),rss_mib=round(mem.rss/1048576,1),vms_mib=round(mem.vms/1048576,1),io_read_bytes=io.read_bytes,io_write_bytes=io.write_bytes)
   except Exception as exc:state['process_stat_error']=type(exc).__name__
  paths=list(B.glob('*.edf'))+list(G.glob('*.map'))+list(G.glob('*.trh'))
  state['output_bytes']={}
  for path in paths:
   try:state['output_bytes'][str(path.relative_to(M))]=path.stat().st_size
   except OSError:pass
  state['free_disk_gib']=round(shutil.disk_usage(B).free/1073741824,2)
  with (LOG/(label+'_status.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(state)+'\n')
  print('MOON_NATIVE_STATUS',json.dumps(state),flush=True)
  return state
 try:
  with (LOG/(label+'.log')).open('w',encoding='utf-8') as log:
   snapshot()
   while True:
    if time.monotonic()-start>timeout:
     snapshot();print(tail,flush=True);raise TimeoutError(label)
    try:chunk=q.get(timeout=1)
    except queue.Empty:chunk=''
    if chunk is None:break
    if chunk:
     log.write(chunk);log.flush();tail=(tail+chunk)[-6000:];error|='ERROR:' in tail.upper();print(chunk,end='',flush=True)
    if time.monotonic()-last>45:snapshot();last=time.monotonic()
  code=p.wait(timeout=60);assert code==0 and not error,(label,code,tail)
  result=dict(returncode=code,seconds=round(time.monotonic()-start,1));print('MOON_NATIVE_COMPLETE',label,json.dumps(result),flush=True)
  return result
 finally:
  if p.poll() is None:
   if process is not None:
    try:
     for child in process.children(recursive=True):child.kill()
    except Exception:pass
   p.kill();p.wait()
  t.join(timeout=5);p.stdout.close()

def tools():
 root=M/'native_tools';root.mkdir(exist_ok=True)
 for name,v in json.loads((R/'BUILD/tool_versions.json').read_text()).items():
  p=root/name
  if not p.exists():
   with urllib.request.urlopen(v['url'],timeout=120) as src,p.open('wb') as out:shutil.copyfileobj(src,out)
  assert sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
  with zipfile.ZipFile(p) as z:
   assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist());z.extractall(root)
 return root/'fbx2edf/fbx2edf_x64.exe',root/'terrained/terrained.exe',root/'tracked/tracked.exe'

def preflight():
 # Blender embeds the diffuse pixels but references its relative .fbm folder.
 # Stage colors and companion shaders/normals there for the Windows importer.
 for folder,names in [('scenery',['v002_context','v002_marker_white','v002_marker_blue','v002_panel','v002_rock']),('moon_sky',['NOLIGHTING_moon_black'])]:
  dest=B/(folder+'.fbm');dest.mkdir(exist_ok=True)
  for name in names:
   for suffix in ['.tga','.shd','_n.tga']:
    path=B/(name+suffix)
    if path.exists():shutil.copy2(path,dest/path.name)
 source=json.loads((B/'v002_source_validation.json').read_text());scene=json.loads((B/'scenery_source_validation.json').read_text());assert source['checks_pass'] and scene['checks_pass'];assert sha(B/'terrain.raw')==source['source_raw_sha256'];assert sha(B/'scenery.fbx')==scene['native_fbx_sha256']
 for path in list(B.glob('*.hmf'))+list(B.glob('*.tht'))+list(B.glob('*.shd')):
  for ref in re.findall(r'(?m)^\s*(?:map|mask|data)\s*=\s*(\S+)',path.read_text()):assert Path(ref).name==ref and (B/ref).is_file(),(path.name,ref)
 for path in B.glob('*.tga'):bitmap_signature(path)
 assert (B/'terrain.raw').stat().st_size==2049*2049*2
 # Match runtime and baked native sun exactly, no Earth sky or fog fallback.
 amb=(G/(NAME+'.amb')).read_text();params=(B/'map_params.ini').read_text()
 assert amb.count('sky = moon_sky.edf')==3 and amb.count('density = 0')==3 and '*' not in amb
 for axis in ['x','y','z']:
  runtime=float(re.search(r'\b'+axis+r'\s*=\s*([-\d.]+)',amb)[1]);baked=float(re.search('lightdir_'+axis+r'=([-\d.]+)',params)[1]);assert abs(runtime-baked)<1e-6
 return source,scene

def validate_heights(mappath,trhpath):
 expected=np.fromfile(B/'terrain.raw','<u2').reshape(2049,2049)
 with trhpath.open('rb') as f:assert f.read(4)==b'TRH\0' and struct.unpack('<2I',f.read(8))==(2049,2049)
 encoded=np.memmap(trhpath,mode='r',dtype='<u2',offset=12,shape=(2049,2049));got=((encoded.astype(np.uint32)-32768)&65535).astype('<u2')[::-1];assert np.array_equal(got,expected)
 flipped=np.ascontiguousarray(expected[::-1]).tobytes();prefix=struct.pack('<2I',2049,2049)+flipped[:512]
 with mappath.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
  assert data[:4]==b'MP2\0';start=0
  while True:
   at=data.find(prefix,start);assert at>=0,'Visual terrain grid missing'
   if data[at+8:at+8+len(flipped)]==flipped:break
   start=at+1
 return dict(checks_pass=True,samples_per_grid=int(expected.size),visual_collision_and_source_grids_identical=True,map_height_offset=at+8)

def compile_all():
 assert os.name=='nt','Official native authoring tools require the Windows workflow'
 source,scenery=preflight();edf,terrain,tracked=tools();result={}
 result['sky']=run(edf,['moon_sky.fbx',G/'moon_sky.edf','edf_params.ini','-q'],'moon_sky',1800);assert (G/'moon_sky.edf').read_bytes()[:4]==b'EDF\0'
 result['scenery']=run(edf,['scenery.fbx','scenery.edf','edf_params.ini','-q'],'moon_scenery',3600);assert (B/'scenery.edf').read_bytes()[:4]==b'EDF\0'
 # Validate exporter coordinates before the costly terrain compile.
 local=scenery['native_probe_local_xyz_m'];assert len(local)>=6
 with (B/'scenery.edf').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
  errors=scan_points(data,local,tolerance=.001);assert all(e is not None for e in errors),('EDF coordinate mismatch',local,errors)
 trh=G/(NAME+'.trh');mp=G/(NAME+'.map')
 for p in [trh,mp]:p.unlink(missing_ok=True)
 result['collision']=run(terrain,['track.tht',trh,'trh_params.ini'],'moon_collision',3600);before=sha(trh)
 result['centerline']=run(tracked,['-merge',trh,'cl',B/'main.tcl'],'moon_route_merge',1800);assert sha(trh)!=before
 result['graphics']=run(terrain,['track.hmf',mp,'map_params.ini'],'moon_terrain',10800)
 return validate_package(source,scenery,result)

def validate_package(source,scenery,result,bake_profile=None,diagnostic=False):
 trh=G/(NAME+'.trh');mp=G/(NAME+'.map');local=scenery['native_probe_local_xyz_m']
 if bake_profile is None:
  import configparser
  cfg=configparser.ConfigParser();cfg.read(B/'map_params.ini');params=cfg['params']
  bake_profile=dict(name='native-map-params',shadowmaps=bool(int(params['shadowmaps_create'])),scale=float(params['shadowmaps_scale']),supersampling=int(params['shadowmaps_supersampling']))
 height=validate_heights(mp,trh);bitmaps=[]
 with mp.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
  expected_points=[[p[0]+800,p[1],p[2]+800] for p in local];errors=scan_points(data,expected_points,tolerance=.001);assert all(e is not None for e in errors),('MAP placement mismatch',errors)
  for name in ['v002_regolith.tga','v002_regolith_n.tga','v002_route.tga','v002_route_n.tga','v002_fine.tga','v002_fine_n.tga']:
   w,h,digest=bitmap_signature(B/name);pos=data.find(struct.pack('<2I',w,h)+digest);assert pos>=0,('Native material missing',name);bitmaps.append(dict(file=name,width=w,height=h,pixel_md5=digest.hex(),map_offset=pos))
 # Every reset line must have exactly its declared number of finite points.
 for p in G.glob('*.tl'):
  data=p.read_bytes();assert data[:4]==b'TL \0';count=struct.unpack_from('<I',data,4)[0];assert len(data)==8+count*8 and np.isfinite(np.frombuffer(data[8:],'<f4')).all()
 for suffix in ['.rdf','.ini','.amb','.tga','_map.tga']:assert (G/(NAME+suffix)).is_file()
 for file,preview in [(NAME+'.tga','01_full_loop.png')]:
  with Image.open(M/'previews_v002'/preview) as im:im.convert('RGB').resize((1024,1024)).save(G/file)
 pkz=M/('Taurus_Littrow_MX_v002_Diagnostic_No_Baked_Shadows.pkz' if diagnostic else 'Taurus_Littrow_MX_v002.pkz')
 with zipfile.ZipFile(pkz,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(G.iterdir()):
   if p.is_file():z.write(p,NAME+'/'+p.name)
 with zipfile.ZipFile(pkz) as z:assert z.testzip() is None and all(n.startswith(NAME+'/') for n in z.namelist())
 assert pkz.stat().st_size<500_000_000,'Test package exceeds the 500 MB target'
 report=dict(version='moon-v002',bake_profile=bake_profile,diagnostic_only=diagnostic,compiled=True,checks_pass=True,centerline_merged=True,native_height_validation=height,native_coordinate_probe_count=len(errors),native_material_signatures=bitmaps,source_validation=source,native_compilers=result,pkz_sha256=sha(pkz),pkz_bytes=pkz.stat().st_size,source_commit=os.environ.get('GITHUB_SHA','local'),run_id=os.environ.get('GITHUB_RUN_ID'),in_game_load_test=False,in_game_riding_test=False,in_game_visual_check=False,multiplayer_supported=False,pending=['Load and ride in single-player Testing with Quiet Gravity v4 preset=half.','Verify pit entry, direction, lap timing and resets.','Assess jump airtime, grip, native lighting and FPS.'])
 save(M/('Moon_v002_Diagnostic_Validation.json' if diagnostic else 'Moon_v002_Validation.json'),report);pkz.with_suffix(pkz.suffix+'.sha256').write_text(sha(pkz)+'  '+pkz.name+'\n');print('MOON_V002_NATIVE_PASS',pkz.stat().st_size,sha(pkz),flush=True)
 return report
if __name__=='__main__':compile_all()
