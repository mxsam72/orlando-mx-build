"""v006: constrained refinements of the user-traced route from the full GoPro lap.

The old source station is retained only as a correspondence coordinate. All
output stations are recomputed from the new native centerline, including jumps,
timing, berms and start-lane joins. Dimensions remain construction estimates.
"""
from pathlib import Path
import json, sys
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
from reference_route import native_segments, sample_native, write_tcl, validate_route
ROOT=Path(__file__).resolve().parents[1]

def main():
    old=ROOT/'01_GIS_AERIAL/v005_route.npz'
    d=np.load(old);q=d['q'];L=q[-1,3]
    info=json.loads((ROOT/'01_GIS_AERIAL/v005_geometry.json').read_text())
    ss=np.linspace(0,L,round(L/.2)+1)
    xy=np.c_[np.interp(ss,q[:,3],q[:,0]),np.interp(ss,q[:,3],q[:,1])]
    # Local landmark constraints, not a newly invented circuit. Straighten the
    # fence lanes, open their end turn, ease the wooded-lane hairpins and shape
    # the left setup into the final right-left section.
    constraints=[
        (0,298.41,184.99),(20,318.4,185.8),(40,338.3,186.7),
        (60,358.1,188.8),(80,377.5,197.0),(96.8,383.0,212.0),
        (113,369,221.8),(140,342,221.8),(170,312,221.8),
        (195,287.0,222.0),(207.6,275,225),(222,265,235),
        (250,254,258),(267,247.5,275),(282,245,288),
        (295,252,296),(309,262.0,285.0),(333,274,264),
        (358.7,289,244),(382,310,239),(409,337,241),
        (433,359,245),(450,368,258),(463.2,359,272),
        (485,337,271),(509.4,318,258),(530,298,262),
        (556,294,285),(586.9,308,309),(611,330,304),
        (640,356,292),(656,371,289),(671.1,382,298),
        (689,378,314),(715,364,336),(760,340,374),
        (797,318,401),(814,304,413),(828.8,292,409),
        (845,294,394),(870,309,374),(900,325,350),
        (916,330,335),(927.7,326,325),(939,315,331),
        (958,302,349),(996,279,378),(1045,250,415),
        (1066,232,424),(1087.6,215,421),(1106,215,404),
        (1130,219,381),(1150,223,361),(1171,231,342),
        (1190,246,334),(1204,258,331),(1213,264,323),
        (1225,259,313),(1244,241,308),(1260,226,301),
        (1280.4,220,285),(1296,228,272),(1320,236,249),
        (1350,241,220),(1375,245,195),(1390.7,253,183),
        (1410,272,184),(1430,288,185),(L,298.41,184.99)]
    a=np.asarray(constraints);base=np.c_[np.interp(a[:,0],q[:,3],q[:,0]),np.interp(a[:,0],q[:,3],q[:,1])]
    delta=a[:,1:]-base;delta[-1]=delta[0]
    xy+=CubicSpline(a[:,0],delta,bc_type='periodic')(ss)
    # A small fairing pass removes residual mosaic wiggles without rounding
    # away the constrained corner/straight arrangement.
    xy[:-1]=gaussian_filter1d(xy[:-1],2.0/.2,axis=0,mode='wrap');xy[-1]=xy[0]
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
    heading=np.unwrap(np.arctan2(np.gradient(xy[:,1]),np.gradient(xy[:,0])))
    source=np.c_[xy,heading,arc,np.zeros(len(arc))]
    origin,theta,segs=native_segments(source,1.8)
    native=sample_native(origin,theta,segs,.22)
    nq=np.c_[native,np.zeros(len(native))];newL=nq[-1,3]
    # Closest source point gives continuous old/new station correspondence.
    ii=cKDTree(xy[:-1]).query(nq[:-1,:2])[1]
    old_s=ss[ii];old_s=np.maximum.accumulate(old_s);old_s=np.r_[old_s,L]
    width=10.8+np.zeros(len(nq))
    # Full racing width plus separate sand shoulders. Broader open corners,
    # narrower wooded rhythm lanes, as seen in the new recording.
    wk=np.array([[0,11.8],[75,12.3],[98,13.0],[125,11.2],[180,11.4],
        [208,12.8],[248,10.4],[290,11.4],[355,12.6],[410,12.2],
        [463,13.5],[509,12.7],[540,11.6],[587,12.4],[650,12.0],
        [680,11.6],[730,10.0],[790,10.0],[829,12.3],[870,10.0],
        [928,11.6],[970,10.4],[1040,10.7],[1088,12.0],[1150,10.7],
        [1213,12.5],[1280,12.2],[1340,11.0],[1391,12.0],[L,11.8]])
    width=PchipInterpolator(wk[:,0],wk[:,1])(old_s);width[-1]=width[0]
    curvature=np.gradient(gaussian_filter1d(np.unwrap(nq[:,2]),12),nq[:,3])
    qa=validate_route(nq,width)
    qa.update(native_centerline_length_m=newL,native_segment_count=len(segs),native_closure_m=float(np.linalg.norm(nq[-1,:2]-nq[0,:2])),source='v005 user trace refined using new full GoPro lap; estimated metres')
    def remap(s):return float(np.interp(s,old_s,nq[:,3]))
    features=[]
    # The full lap resolves lip placement inside the old aerial jump groups.
    lip_changes={'J01':39,'J02':130,'J03':236,'J04':407,'J05':492,
        'J06':541,'J07':618,'J08a':708,'J08b':764,'J09a':853,
        'J09b':880,'J10a':961,'J10b':998,'J11':1112,
        'J12a':1310,'J12b':1355}
    for f in info['features']:
        oldstation=lip_changes.get(f['id'],f['native_s_m']);ns=remap(oldstation)
        f.update(v005_station_m=oldstation,native_s_m=ns,xz_m=[float(np.interp(ns,nq[:,3],nq[:,k])) for k in range(2)])
        features.append(f)
    for jid,os,rt in [('J03b',335,37.2),('J11b',1153,107.6)]:
        ns=remap(os);features.append(dict(id=jid,v005_station_m=os,native_s_m=ns,xz_m=[float(np.interp(ns,nq[:,3],nq[:,k])) for k in range(2)],real_video_seconds=rt,evidence='Additional distinct crest resolved by complete lap'))
    for e in info['turns']:
        oldmid=e['mid'];e['mid']=remap(oldmid);e['arc_start']=remap(e['arc_start']);e['arc_end']=remap(e['arc_end']);e['width']=float(np.interp(e['mid'],nq[:,3],width))
    info.update(name='orlandomx_2026_v006',features=features,model_lap_length_m=newL,native_origin_xz=origin.tolist(),native_origin_heading_rad=theta,native_origin_source_s=0.,width_range_m=[float(width.min()),float(width.max())],revision_basis='New complete GoPro lap + user ridden v005 video; aerial connectivity retained',metric_status='Video-guided construction estimates; not surveyed',fairing='Local corner/straight constraints, 2m fairing; no arbitrary closure leg')
    np.savez_compressed(ROOT/'01_GIS_AERIAL/route.npz',q=nq,width=width,curvature=curvature,v005_s=old_s)
    write_tcl(ROOT/'09_TRACKED/main.tcl',origin,theta,segs)
    (ROOT/'01_GIS_AERIAL/geometry.json').write_text(json.dumps(info,indent=2)+'\n')
    (ROOT/'DOCUMENTATION/route_validation.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
