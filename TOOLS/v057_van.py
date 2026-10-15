"""Regular-wheelbase, low-roof Chevrolet Express cargo van, local +Z nose.

Silhouette derived from the user's two photos; 135-inch wheelbase / 224-inch
length checked against GM Upfitter Express cargo drawings. No new paint maps.
"""
import math
import numpy as np
from vehicle_geometry_v024 import MeshBuilder
from model_vehicles_v024 import arch_profile


def rounded_outline(z0,z1,y0,y1,r=.07,n=5):
    out=[]
    for cz,cy,a in [(z1-r,y1-r,0),(z0+r,y1-r,90),(z0+r,y0+r,180),(z1-r,y0+r,270)]:
        for t in np.deg2rad(np.linspace(a,a+90,n)):
            out.append([cz+r*math.cos(t),cy+r*math.sin(t)])
    return out+[out[0]]


def build():
    m=MeshBuilder('van_shane'); w=1.007; L=5.692; axles=[-1.592,1.837]
    m.box([0,.44,0],[1.65,.18,5.35],'dark')
    for side in [-1,1]:
        # Real wheel openings: the lower sill does not cut through the tires.
        m.prism(arch_profile(L-.18,axles,.457,1.39,1.26),side*w-.028,side*w+.028,'van_paint')
    sections=[(-2.73,.90,1.82,2.08,.965,.80),(-2.57,.90,1.88,2.138,w,.845),(.52,.90,1.88,2.138,w,.845),
              (1.22,.90,1.86,2.128,.985,.823),(1.34,.90,1.75,2.03,.976,.824),(1.86,.90,1.31,1.405,.97,.82)]
    vs=[]; ring=15
    for z,b,sh,top,wide,roof in sections:
        cross=[[-wide,b],[wide,b],[wide,sh]]
        for a in np.linspace(0,math.pi/2,6)[1:]:cross.append([roof+(wide-roof)*math.cos(a),sh+(top-sh)*math.sin(a)])
        cross.append([-roof,top])
        for a in np.linspace(math.pi/2,math.pi,6)[1:]:cross.append([-roof+(wide-roof)*math.cos(a),sh+(top-sh)*math.sin(a)])
        # 14 points, with the last exactly at the left vertical shoulder.
        if z==sections[0][0]:ring=len(cross)
        vs.extend([[x,y,z] for x,y in cross])
    faces=[]
    for k in range(len(sections)-1):
        for i in range(ring):faces.append([k*ring+i,k*ring+(i+1)%ring,(k+1)*ring+(i+1)%ring,(k+1)*ring+i])
    faces += [list(range(ring-1,-1,-1)),list(range((len(sections)-1)*ring,len(vs)))]
    m.add(vs,faces,'van_paint')
    # Short rounded bonnet and the broad, upright Express front, rather than
    # the long wedge-shaped nose / rearward cab of the old model.
    m.loft([[1.78,.84,1.30,1.397,.972,.85],[2.30,.80,1.26,1.365,.97,.85],[2.66,.74,1.20,1.29,.94,.82],[2.765,.73,1.16,1.23,.90,.80]],'van_paint')
    m.panel([[-.842,1.432,1.845],[.842,1.432,1.845],[.806,2.065,1.278],[-.806,2.065,1.278]],'glass')
    # Windshield gasket and two fine wipers, all separated from the glass.
    for side in [-1,1]:
        m.beam([side*.854,1.414,1.856],[side*.819,2.082,1.284],.022,'dark',8)
        m.tube([[side*.69,1.452,1.855],[side*.34,1.492,1.819],[side*.04,1.488,1.822]],.008,'dark',5)
        # Side cab window (rear vertical B-pillar, steep front A-pillar).
        x=side*1.012
        m.panel([[x,1.415,.60],[x,1.415,1.77],[side*.945,2.055,1.22],[side*.970,2.075,.60]],'glass',side>0)
        outline=[[side*1.021,1.398,.57],[side*1.021,1.398,1.79],[side*.952,2.071,1.231],[side*.977,2.091,.57],[side*1.021,1.398,.57]]
        m.tube(outline,.011,'steel',6)
        # Door seams, recessed vertical handle, and solid cargo panel pressing.
        m.tube([[side*1.036,.405,.52],[side*1.039,1.39,.52],[side*.981,2.096,.52]],.006,'dark',5)
        m.tube([[side*1.038,.405,.52],[side*1.038,.405,1.24],[side*1.038,.81,1.26],[side*1.025,1.36,1.80]],.006,'dark',5)
        m.box([side*1.044,1.205,.61],[.027,.193,.071],'steel')
        m.box([side*1.062,1.213,.61],[.016,.143,.037],'dark')
        contour=rounded_outline(-2.52,.38,1.405,2.025,.105,7)
        m.tube([[side*1.014,y,z] for z,y in contour],.006,'dark',5)
        # Long body crease, fuel cap and a few subtle lower rub-strip features.
        m.tube([[side*1.040,1.095,-2.54],[side*1.044,1.075,-.9],[side*1.042,1.09,.40]],.012,'van_paint',6)
        if side<0:
            pts=[[side*1.041,.78+.096*math.sin(t),-.65+.096*math.cos(t)] for t in np.linspace(0,math.tau,25)]
            m.tube(pts,.005,'dark',5)
        for axle in axles:
            pts=[[side*1.041,.405+.457*math.sin(t),axle+.457*math.cos(t)] for t in np.linspace(0,math.pi,25)]
            m.tube(pts,.018,'van_paint',8)
        m.beam([side*.99,1.40,1.66],[side*1.19,1.46,1.63],.031,'dark',8)
        m.box([side*1.235,1.526,1.62],[.135,.29,.22],'dark')
        m.box([side*1.24,1.526,1.502],[.12,.25,.012],'glass')
    # Barn-door rear, raised hinges, tall lamps and chrome rear step bumper.
    m.beam([0,.52,-2.748],[0,2.075,-2.748],.007,'dark',5)
    for side in [-1,1]:
        for y in [.69,1.60]:m.box([side*.87,y,-2.755],[.095,.11,.038],'van_paint')
        m.box([side*.928,1.70,-2.757],[.123,.425,.038],'red_light')
        m.box([side*.928,1.615,-2.782],[.12,.059,.017],'headlight')
        m.box([side*.055,1.10,-2.766],[.039,.145,.025],'dark')
    m.box([0,.59,-2.815],[2.025,.205,.17],'alloy')
    m.box([0,.705,-2.83],[1.19,.055,.18],'dark')
    m.box([0,2.087,-2.70],[.26,.052,.038],'red_light')
    m.box([0,.79,-2.766],[.36,.16,.022],'dark')
    # Express grille: two stacked lamp units, horizontal chrome grille bar,
    # body-height black grille surround and real Chevrolet bowtie silhouette.
    m.box([0,.61,2.798],[2.015,.22,.17],'alloy')
    m.box([0,.735,2.799],[1.95,.046,.16],'dark')
    m.box([0,1.035,2.753],[1.15,.335,.066],'dark')
    for yy in [.919,.971,1.085,1.139]:m.box([0,yy,2.793],[1.10,.017,.016],'steel')
    m.box([0,1.028,2.81],[1.155,.047,.019],'alloy')
    badge=[[-.18,.998],[-.075,.998],[-.075,.966],[.075,.966],[.075,.998],[.18,.998],[.18,1.058],[.075,1.058],[.075,1.090],[-.075,1.090],[-.075,1.058],[-.18,1.058]]
    from vehicle_geometry_v024 import triangulate
    m.add([[x,y,2.826] for x,y in badge],triangulate(badge),'chevy_badge')
    for side in [-1,1]:
        m.box([side*.771,1.125,2.737],[.346,.213,.070],'headlight')
        m.box([side*.774,.944,2.774],[.349,.092,.052],'headlight')
        m.box([side*.771,.856,2.773],[.347,.062,.052],'amber')
        m.box([side*.95,.98,2.69],[.044,.30,.07],'amber')
        for yy in [1.085,1.135,1.185]:m.box([side*.771,yy,2.777],[.321,.006,.006],'alloy')
    for z in axles:
        m.beam([-.88,.386,z],[.88,.386,z],.055,'dark',10)
        for side in [-1,1]:m.wheel(side*.88,.386,z,.386,.235,'steel','steel',6)
    return list(m.parts.values())
