"""User-authoritative v021 obstacle primitives, in metres along the native route.

Overall length is toe to end of landing/runout, excluding zero-height sampling
padding. Gaps have independent backsides, valley floors and landing fronts.
"""
import math
import numpy as np
from refine_jumps import add_grade_segment,smooth

def make_profile(source):
    p=source.copy();kind=p['kind'];start=p['station_start_m'];end=p['station_end_m'];F=p['face_m'];H=p['crest_height_m'];L=p['landing_m']
    p['lip_s']=start+F;xs=[-F-3,-F];ys=[0.,0.];ds=[0.,0.];marks={'toe':-F};crests=[];valleys=[];g=0.
    def grade(length,a,b):
        if length>1e-8:add_grade_segment(xs,ys,ds,length,a,b)
    def rounded(length,height):
        slope=2*(height-ys[-1])/length;grade(length/2,0,slope);grade(length/2,slope,0);ys[-1]=height
    def ramp(length,height,transition=.6):
        edge=min(transition,length*.22);slope=(height-ys[-1])/(length-edge)
        grade(edge,0,slope);grade(length-2*edge,slope,slope);grade(edge,slope,0);ys[-1]=height
    def landing(length):
        rounding=float(p.get('landing_rounding_scale',1.0))
        entry=min(1.4*rounding,length*.28);run=min(4.0*rounding,length*.42)
        if entry+run>length*.80:
            k=(length*.80)/(entry+run);entry*=k;run*=k
        slope=-ys[-1]/(length-(entry+run)/2)
        grade(entry,0,slope);grade(length-entry-run,slope,slope);grade(run,slope,0);ys[-1]=0.
    def gap(span,valley,height,number):
        a=xs[-1];ramp(span*.45,valley);v0=xs[-1];grade(span*.10,0,0);v1=xs[-1];ramp(span*.45,height)
        valleys.append(dict(start=v0,end=v1,height=valley));marks[f'gap_{number}_start']=a;marks[f'gap_{number}_end']=xs[-1];crests.append(xs[-1])
    if kind=='none':
        grade(end-start,0,0)
    elif kind in ['single','ant_hill','inside_roller']:
        rounded(F,H);crests.append(xs[-1]);marks['single_crest']=xs[-1];rounded(L,0);g=2*H/F
    elif kind=='roller_sequence':
        spacing=p['spacing_m'];heights=p['roller_heights_m']
        custom=p.get('crest_spacings_m')
        if custom:
            # Non-uniform rolling-single sequence.  v021 uses this for R12 so
            # the final crest sits only ~5 m after the third while the first
            # two crest gaps remain ~10 m.  Build a dense smooth composite
            # profile so the final two singles may overlap naturally.
            width=float(p.get('roller_width_m',spacing))
            startx=-F;endx=end-p['lip_s']
            centers=[startx+width/2]
            for ds_gap in custom:centers.append(centers[-1]+float(ds_gap))
            assert len(centers)==len(heights)
            assert centers[-1]+width/2<=endx+1e-6,(p['id'],'custom rollers exceed section',centers,endx)
            xcore=np.linspace(startx,endx,max(40,int((endx-startx)/.10)+1))
            ycore=np.zeros_like(xcore)
            for i,(center,h) in enumerate(zip(centers,heights)):
                u=(xcore-center)/(width/2)
                bump=np.where(np.abs(u)<=1,h*.5*(1+np.cos(np.pi*u)),0.)
                ycore=np.maximum(ycore,bump);crests.append(center);marks[f'roller_{i+1}']=center
            dcore=np.gradient(ycore,xcore);dcore[0]=0.;dcore[-1]=0.
            xs=[startx-3.0]+xcore.tolist();ys=[0.0]+ycore.tolist();ds=[0.0]+dcore.tolist()
            g=float(np.max(np.abs(dcore)))
        else:
            for i,h in enumerate(heights):
                rounded(spacing/2,h);crests.append(xs[-1]);marks[f'roller_{i+1}']=xs[-1];rounded(spacing/2,0)
            g=4*max(heights)/spacing
    else:
        lip=p['lip_transition_m'];split=p.get('face_progression',.5);ratio=p.get('lower_face_grade_ratio',.6)
        g=H/(F*(split*ratio/2+(1-split)*(ratio+1)/2)+lip/2)
        grade(F*split,0,ratio*g);grade(F*(1-split),ratio*g,g);marks['lip']=xs[-1];grade(lip,g,0);ys[-1]=H;crests.append(xs[-1])
        if kind in ['tabletop','table_single']:
            marks['deck_start']=xs[-1];grade(p['deck_m'],0,0);marks['deck_end']=xs[-1]
        if kind in ['double','table_single','triple']:
            for i,part in enumerate(p['gaps']):gap(part['span_m'],part['valley_height_m'],part['landing_crest_height_m'],i+1)
        marks['landing_break']=xs[-1];landing(L)
    marks['runout_end']=xs[-1]
    assert abs(xs[-1]+p['lip_s']-end)<1e-6,(p['id'],'length differs',xs[-1]+p['lip_s'],end)
    assert min(ys)>-1e-8 and abs(ys[-1])<1e-8
    assert max(abs(np.array(ds)))<.80,(p['id'],'excessive designed slope',max(abs(np.array(ds))))
    grade(3,0,0)
    p.update(profile_s=xs,profile_h=ys,profile_derivative=ds,landmarks_m=marks,crest_offsets_m=crests,valleys=valleys,
             takeoff_angle_deg=math.degrees(math.atan(g)),authored_total_length_m=end-start,
             status='User-authoritative type/count/length; other dimensions are authoring estimates; riding pending')
    return p

def envelope(pts,items):
    output=np.zeros(len(pts))
    for j,s,p,th,width,tree,f in items:
        if j['kind']=='none':continue
        half=j.get('racing_width_m',10)/2;taper=j.get('side_taper_m',7.5);offset=j.get('lateral_offset_m',0);margin=half+taper+abs(offset)+2
        box=(pts[:,0]>p[:,0].min()-margin)&(pts[:,0]<p[:,0].max()+margin)&(pts[:,1]>p[:,1].min()-margin)&(pts[:,1]<p[:,1].max()+margin)
        if not box.any():continue
        _,i=tree.query(pts[box]);d=pts[box]-p[i];along=d[:,0]*np.cos(th[i])+d[:,1]*np.sin(th[i]);lat=-d[:,0]*np.sin(th[i])+d[:,1]*np.cos(th[i]);x=s[i]+along-j['lip_s']
        y=f(np.clip(x,j['profile_s'][0],j['profile_s'][-1]));y*=1-smooth((abs(lat-offset)-half)/taper)
        if j['kind']=='inside_roller':y*=smooth((lat-1.2)/.6)
        output[box]=np.maximum(output[box],np.maximum(y,0))
    return output
