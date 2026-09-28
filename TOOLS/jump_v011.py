"""Explicit earthwork primitives. Units metres; all parameters are authoring estimates.

lip_s is the end of the rising face, before the short lip-to-deck transition.
A double has two separate crests and a depressed valley, never a filled deck.
"""
import math
import numpy as np
from refine_jumps import add_grade_segment, smooth

def make_profile(src):
    p=src.copy(); kind=p['kind']; F=p['face_m']; H=p['crest_height_m']; L=p['landing_m']
    xs,ys,ds=[-F-3,-F],[0.,0.],[0.,0.]
    def grade(length,g0,g1): add_grade_segment(xs,ys,ds,length,g0,g1)
    def transition(length,end):
        # S-curve with zero end slopes; exact endpoint height and continuous grade.
        g=2*(end-ys[-1])/length
        grade(length/2,0,g);grade(length/2,g,0);ys[-1]=end
    def descent(length,end=0):
        entry=min(2.2,length*.18);run=min(4.5,length*.3)
        g=(end-ys[-1])/(length-(entry+run)/2)
        grade(entry,0,g);grade(length-entry-run,g,g);grade(run,g,0);ys[-1]=end
    marks={}
    if kind in ['roller','natural_crest']:
        transition(F,H);marks['crest']=xs[-1];transition(L,0);g=2*H/F
    else:
        lip=p.get('lip_transition_m',1.2);split=p.get('face_progression',.48)
        # Separate lower and upper face curvature. Brief lip transition instead
        # of smoothing the entire feature into one mound.
        ratio=p.get('lower_face_grade_ratio',.72)
        g=H/(F*(split*ratio/2+(1-split)*(ratio+1)/2)+lip/2)
        grade(F*split,0,ratio*g);grade(F*(1-split),ratio*g,g)
        marks['lip']=xs[-1];grade(lip,g,0);ys[-1]=H;marks['deck_start']=xs[-1]
        if kind=='double':
            gap=p['gap_m']; valley=p['valley_height_m']; landing=p['landing_crest_height_m']
            marks['gap_start']=xs[-1]
            # Back of takeoff, rollable valley floor, front of landing mound.
            transition(gap*.43,valley);marks['valley_start']=xs[-1]
            grade(gap*.14,0,0);marks['valley_end']=xs[-1]
            transition(gap*.43,landing);marks['landing_crest']=xs[-1]
            marks['landing_break']=xs[-1];descent(L)
        elif kind in ['tabletop','step_up','step_down','jump_out_of_turn']:
            deck=p.get('deck_m',4);offset=p.get('landing_offset_m',0)
            # A real finite deck, with a separately controlled landing shelf.
            if offset:transition(deck,H+offset)
            else:grade(deck,0,0)
            marks['deck_end']=xs[-1];marks['landing_break']=xs[-1];descent(L)
        else:raise ValueError('Unknown jump primitive '+kind)
    marks['runout_end']=xs[-1];grade(3,0,0)
    assert abs(ys[-1])<1e-9 and min(ys)>-1e-9
    assert max(abs(np.array(ds)))<.8, (p['id'],'authoring slope too steep')
    p.update(profile_s=xs,profile_h=ys,profile_derivative=ds,landmarks_m=marks,
             takeoff_angle_deg=math.degrees(math.atan(g)),
             status='Video-guided estimate; native/game ride validation separate')
    return p

def envelope(pts,items):
    """Independent riding width and earthen sidewalls for each primitive."""
    output=np.zeros(len(pts))
    for j,s,p,th,width,tree,f in items:
        half=j.get('racing_width_m',float(np.median(width))-.5)/2
        taper=j.get('side_taper_m',7.0); margin=half+taper+2
        box=(pts[:,0]>p[:,0].min()-margin)&(pts[:,0]<p[:,0].max()+margin)&(pts[:,1]>p[:,1].min()-margin)&(pts[:,1]<p[:,1].max()+margin)
        if not box.any():continue
        _,i=tree.query(pts[box]);d=pts[box]-p[i]
        along=d[:,0]*np.cos(th[i])+d[:,1]*np.sin(th[i])
        lat=-d[:,0]*np.sin(th[i])+d[:,1]*np.cos(th[i]);x=s[i]+along-j['lip_s']
        y=f(np.clip(x,j['profile_s'][0],j['profile_s'][-1]))
        y*=1-smooth((abs(lat)-half)/taper)
        output[box]=np.maximum(output[box],np.maximum(y,0))
    return output
