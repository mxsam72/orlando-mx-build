"""Check actual encoded geometry and record before/after profiles against v009."""
from v010_common import *
from scipy.ndimage import map_coordinates

def main():
    source=(R/'TOOLS/qa_v009_geometry.py').read_text(encoding='utf-8').replace('v009','v010').replace('V009','V010')
    for name in ['baseline_route.npz','baseline_geometry.json','section_station_map.json']:
        source=source.replace("S/'"+name+"'", "R/'V009_SOURCE/"+name+"'")
    source=source.replace("R/'BUILD/v010_baseline/terrain.raw'", "R/'V009_OUTPUT/terrain.raw'")
    source=source.replace("R/'V010_OUTPUT/terrain.raw'", "R/'V010_OUTPUT/main_terrain.raw'")
    source=source.replace('v008b','v009 baseline')
    ns={'__name__':'v010_qa','__file__':__file__};exec(compile(source,__file__,'exec'),ns,ns);ns['main']()
    q,w=route(); before=np.fromfile(R/'V009_OUTPUT/terrain.raw','<u2').reshape(N,N)/65535*SCALE;after=np.fromfile(O/'main_terrain.raw','<u2').reshape(N,N)/65535*SCALE
    metrics=[]
    for j in read(S/'v010_geometry_spec.json')['profiles']:
        ss=np.linspace(j['lip_s']-j['face_m']-3,j['lip_s']+j['rollover_m']+j['crest_bridge_m']+j['landing_m']+3,350)
        pos=np.c_[np.interp(ss,q[:,3],q[:,0]),np.interp(ss,q[:,3],q[:,1])]
        a,b=ground(after,pos),ground(before,pos);face=ss<j['lip_s'];land=ss>j['lip_s']+j['rollover_m']+j['crest_bridge_m']
        metrics.append(dict(id=j['id'],station_m=j['lip_s'],v009_face_max_grade=float(np.gradient(b,ss)[face].max()),v010_face_max_grade=float(np.gradient(a,ss)[face].max()),v010_landing_max_down_grade=float(-np.gradient(a,ss)[land].min()),max_height_delta_m=float(abs(a-b).max())))
    qa=read(R/'DOCUMENTATION/v010_geometry_validation.json');qa['actual_obstacle_profiles']=metrics;qa['comparison_baseline']='Reconstructed exact v009 source terrain';qa['provisional_features_disabled']=['EX1','EX2'];qa['main_horizontal_route_changed']=False
    save(R/'DOCUMENTATION/v010_geometry_validation.json',qa)
    print('Actual encoded obstacle metrics saved:',len(metrics))
if __name__=='__main__':main()
