"""Photo-derived owner vehicles and bikes. Dimensions are conservative estimates.
Distinct Cybertruck, King Ranch pickup, wrapped squared-body pickup and Chevy van.
"""
import math
import numpy as np
from vehicle_geometry_v019 import MeshBuilder
from v019_common import *

def arch_profile(length,axles,r,top):
    # Monotonic lower outline with semicircular wheel openings, closed along top.
    pts=[[-length/2,.45]]
    for axle in sorted(axles):
        pts += [[axle-r,.45]]
        for t in np.linspace(math.pi,0,13):pts.append([axle+r*math.cos(t),.45+r*math.sin(t)])
    pts += [[length/2,.45],[length/2,top],[-length/2,top]]
    # Suppress repeated lower-arc endpoint vertices.
    clean=[]
    for p in pts:
        if not clean or np.linalg.norm(np.array(p)-clean[-1])>1e-7:clean.append(p)
    return clean

def fender(m,x,axle,r,mat,square=False):
    if square:
        pts=[[x,.47,axle-r],[x,.94,axle-r*.9],[x,1.10,axle-r*.62],[x,1.10,axle+r*.62],[x,.94,axle+r*.9],[x,.47,axle+r]]
    else:pts=[[x,.45+r*math.sin(t),axle+r*math.cos(t)] for t in np.linspace(0,math.pi,17)]
    m.tube(pts,.043,mat,6)

def vehicle_wheels(m,axles,halfwidth,r,style,rim):
    for z in axles:
        m.beam([-halfwidth,.39,z],[halfwidth,.39,z],.065,'dark',10)
        for side in [-1,1]:m.wheel(side*halfwidth,r,z,r,.265,rim,style,spokes=10 if style!='cyber' else 12)

def pickup(owner):
    sam=owner=='sam';m=MeshBuilder('truck_'+owner);L=5.88 if sam else 5.82;w=1.02 if sam else 1.04;axles=[-1.83,1.81];paint='sam_paint' if sam else 'white';lower='sam_tan' if sam else 'dark';r=.415 if sam else .465
    m.box([0,.45,0],[1.6,.23,L-.2],'dark')
    for side in [-1,1]:
        m.prism(arch_profile(L,axles,.54,1.38),side*w-.05,side*w+.05,paint)
        # Lower trim interrupted at the wheel openings, not painted across tires.
        for a,b in [(-L/2,-2.39),(-1.27,1.25),(2.37,L/2)]:m.box([side*(w+.035),.64,(a+b)/2],[.04,.24,b-a],lower)
        for axle in axles:fender(m,side*(w+.045),axle,.545,lower if sam else 'dark',not sam)
        m.beam([side*(w+.14),.42,-1.25],[side*(w+.14),.42,1.13],.045,'alloy' if sam else 'steel',10)
        for z in [-.75,.65]:m.box([side*(w+.14),.43,z],[.28,.04,.56],'dark')
    # Hood is a tapered six-sided loft; cab has sloped windshield and roof edges.
    m.loft([[1.10,.90,1.34,1.39,w-.02,w-.19],[2.40,.85,1.26,1.33,w-.02,w-.17],[2.92,.77,1.18,1.23,w-.06,w-.21]],paint)
    m.loft([[-1.11,.76,1.77,1.98,w-.07,w-.21],[-.88,.76,1.87,2.04,w-.06,w-.21],[.47,.76,1.87,2.02,w-.08,w-.21],[1.30,.76,1.31,1.39,w-.04,w-.12]],paint)
    m.panel([[-.78,1.42,1.285],[.78,1.42,1.285],[.79,2.02,.49],[-.79,2.02,.49]],'glass')
    m.panel([[.78,1.40,-1.12],[-.78,1.40,-1.12],[-.78,1.90,-1.12],[.78,1.90,-1.12]],'glass')
    for side in [-1,1]:
        x=side*(w-.06)
        for z0,z1 in [(-.98,-.30),(-.22,.45)]:
            m.panel([[x,1.44,z0],[x,1.44,z1+.40 if z1>0 else z1],[x,1.90,z1],[x,1.92,z0]],'glass',side>0)
        # Door seams, handles and separate sculpted mirrors.
        for zz in [-1.04,-.26,.90]:m.beam([side*(w+.054),.79,zz],[side*(w-.038),1.48,zz],.009,'dark',4)
        for zz in [-.55,.58]:m.box([side*(w+.070),1.29,zz],[.035,.048,.17],'alloy' if sam else 'dark')
        m.beam([side*w,1.52,.97],[side*(w+.25),1.55,1.02],.036,'dark',6);m.box([side*(w+.29),1.59,1.03],[.20,.20,.30],'alloy' if sam else 'steel');m.box([side*(w+.295),1.60,.87],[.15,.15,.018],'glass')
        if sam:
            m.panel([[side*(w+.057),.92,.98],[side*(w+.057),.92,1.21],[side*(w+.057),1.04,1.21],[side*(w+.057),1.04,.98]],'king_ranch',side>0)
            m.panel([[side*(w+.063),1.05,-2.63],[side*(w+.063),1.05,-2.06],[side*(w+.063),1.29,-2.06],[side*(w+.063),1.29,-2.63]],'four_by_four',side>0)
        else:
            # Door/bed wrap remains outside the body; wheel arches stay exposed.
            # Full side wrap cut to the rear wheel arch. UVs preserve the graphic.
            poly=[[-2.62,.80],[-2.37,.80]]
            for t in np.linspace(math.pi*.80,math.pi*.20,15):
                poly.append([-1.83+.57*math.cos(t),.45+.57*math.sin(t)])
            poly += [[-1.29,.80],[1.07,.80],[1.07,1.39],[-2.62,1.39]]
            from vehicle_geometry_v019 import triangulate
            vs=[[side*(w+.064),yy,zz] for zz,yy in poly]
            for tri in triangulate(poly):
                uv=[[(poly[i][0]+2.62)/3.69,(poly[i][1]-.80)/.59] for i in tri]
                m.add(vs,[tri], 'premier_wrap', [uv])
                m.add(vs,[list(reversed(tri))], 'premier_wrap', [list(reversed(uv))])
            m.panel([[side*(w-.038),1.40,-1.02],[side*(w-.038),1.40,-.27],[side*(w-.19),1.95,-.27],[side*(w-.19),1.95,-1.02]],'premier_wrap',side>0)
    # Real bed cavity: floor, raised rails, front bulkhead and tailgate.
    m.box([0,.93,-2.0],[1.80,.10,1.65],'rubber')
    for side in [-1,1]:m.box([side*.95,1.43,-2.0],[.15,.12,1.73],'dark' if not sam else paint)
    m.box([0,1.20,-2.91],[2.02,.56,.11],paint);m.box([0,1.46,-2.93],[2.02,.08,.15],'dark');m.box([0,1.32,-2.985],[.28,.05,.024],'dark')
    m.box([0,.62,-2.99],[2.13,.20,.22],'alloy' if sam else 'steel');m.box([0,.71,-3.015],[1.30,.04,.23],'dark');m.box([0,.48,-3.08],[.22,.10,.28],'dark')
    for side in [-1,1]:m.box([side*.88,1.12,-2.995],[.23,.47,.045],'red_light');m.box([side*.88,1.12,-3.022],[.22,.055,.015],'headlight')
    # Front fascia: chrome surround, inset grille bars, rectangular lamp clusters.
    m.box([0,.76,2.99],[2.03,.23,.18],lower);m.box([0,1.04,2.94],[1.12,.45,.14],'alloy');m.box([0,1.04,3.018],[.99,.33,.025],'dark')
    for zrow in range(4):m.box([0,.91+zrow*.086,3.04],[.96,.021,.015],'alloy')
    m.panel([[-.14,.98,3.054],[.14,.98,3.054],[.14,1.10,3.054],[-.14,1.10,3.054]],'ford_badge' if sam else 'chevy_badge')
    for side in [-1,1]:
        m.box([side*.78,1.04,2.99],[.42,.39,.075],'headlight');m.box([side*.968,1.04,3.037],[.07,.33,.03],'amber');m.beam([side*.73,.71,3.07],[side*.73,.71,3.089],.069,'dark',12);m.beam([side*.73,.71,3.09],[side*.73,.71,3.096],.049,'headlight',12)
    vehicle_wheels(m,axles,w+.035,r,'spoke','alloy' if sam else 'wheel_black');return m

def cybertruck():
    m=MeshBuilder('truck_jordan');w=1.06;L=5.67;axles=[-1.88,1.74]
    m.box([0,.43,0],[1.83,.21,5.45],'dark')
    for side in [-1,1]:m.prism(arch_profile(L,axles,.57,1.34),side*w-.048,side*w+.048,'cyber_steel')
    m.loft([[-2.835,.85,1.40,1.45,1.055,.99],[-1.02,.92,1.58,1.89,1.055,.87],[.06,.92,1.61,1.92,1.055,.84],[2.82,.84,1.08,1.18,1.01,.97]],'cyber_steel')
    # Windshield forms the long planar nose slope; four trapezoidal side windows.
    m.panel([[-.92,1.285,2.48],[.92,1.285,2.48],[.82,1.925,.10],[-.82,1.925,.10]],'glass')
    for side in [-1,1]:
        x=side*1.060
        m.panel([[x,1.42,-.96],[x,1.42,-.12],[side*.893,1.86,-.04],[side*.925,1.83,-.96]],'glass',side>0)
        m.panel([[x,1.42,-.04],[side*1.038,1.29,1.86],[side*.915,1.84,.10],[side*.893,1.86,-.04]],'glass',side>0)
        for zz in [-1.01,-.08,1.70]:m.beam([x,.64,zz],[x,1.43,zz],.008,'dark',4)
        for axle in axles:fender(m,side*1.115,axle,.58,'dark',True)
        m.prism([[.78,1.43],[1.01,1.35],[1.01,1.54]],side*1.13-.045,side*1.13+.045,'dark')
        m.box([side*1.09,.51,0],[.12,.13,3.10],'dark')
    # Black ribbed tonneau with tall stainless rear sail edges.
    m.panel([[-.89,1.505,-2.70],[.89,1.505,-2.70],[.88,1.898,-1.06],[-.88,1.898,-1.06]],'rubber')
    for z in np.linspace(-2.68,-1.08,19):
        y=1.505+(z+2.70)/1.64*.393;m.beam([-.88,y+.008,z],[.88,y+.008,z],.008,'steel',4)
    m.box([0,.79,2.84],[2.03,.25,.12],'dark');m.box([0,1.15,2.84],[1.97,.027,.04],'headlight');m.box([0,.71,-2.87],[2.05,.24,.15],'dark');m.box([0,1.40,-2.853],[1.96,.035,.04],'red_light')
    vehicle_wheels(m,axles,1.085,.455,'cyber','wheel_black');return m

def van():
    m=MeshBuilder('van_shane');w=1.02;L=5.69;axles=[-1.70,1.84]
    m.box([0,.44,0],[1.78,.20,5.47],'dark')
    for side in [-1,1]:m.prism(arch_profile(L,axles,.48,1.32),side*w-.045,side*w+.045,'van_paint')
    # Full-height cargo shell with curved shoulders and short separate hood.
    m.loft([[-2.84,.80,1.99,2.17,.97,.79],[-2.57,.80,2.04,2.23,1.035,.85],[.68,.80,2.04,2.23,1.035,.85],[1.49,.80,1.45,1.53,1.015,.88]],'van_paint')
    m.loft([[1.40,.77,1.37,1.42,1.00,.87],[2.40,.74,1.29,1.36,.995,.83],[2.84,.70,1.21,1.29,.96,.78]],'van_paint')
    m.panel([[-.80,1.558,1.475],[.80,1.558,1.475],[.80,2.195,.74],[-.80,2.195,.74]],'glass')
    for side in [-1,1]:
        m.panel([[side*1.04,1.42,.0],[side*1.035,1.42,1.35],[side*.87,2.10,.73],[side*.88,2.11,.0]],'glass',side>0)
        m.beam([side*1.065,.64,-.08],[side*1.065,2.10,-.08],.008,'dark',4)
        # Cargo sliding/swing door seams; photo shows solid panels, not passenger glass.
        for zz in [-2.51,-1.20]:m.beam([side*1.073,.73,zz],[side*1.059,2.05,zz],.007,'dark',4)
        m.box([side*1.068,1.17,.10],[.03,.15,.065],'alloy');m.box([side*1.06,.88,-1.22],[.030,.045,2.22],'dark')
        m.beam([side*1.02,1.45,1.18],[side*1.20,1.48,1.22],.029,'dark',6);m.box([side*1.24,1.50,1.21],[.15,.24,.22],'steel');m.box([side*1.247,1.5,1.092],[.13,.19,.014],'glass')
        for axle in axles:fender(m,side*1.07,axle,.48,'van_paint')
    # Rear barn-door seam, inset door panel edges, tall red tail lamps and chrome step.
    m.beam([0,.69,-2.851],[0,2.11,-2.851],.011,'dark',5)
    for side in [-1,1]:
        m.panel([[side*.06,.94,-2.855],[side*.85,.94,-2.855],[side*.80,1.99,-2.855],[side*.06,2.04,-2.855]],'van_paint',side>0)
        m.box([side*.921,1.70,-2.861],[.13,.52,.06],'red_light');m.box([side*.921,1.66,-2.896],[.12,.07,.02],'headlight')
    m.box([0,.64,-2.94],[2.08,.20,.24],'alloy');m.box([0,.70,-3.005],[1.28,.07,.24],'dark');m.box([0,2.18,-2.64],[.25,.05,.065],'red_light')
    m.box([0,.65,2.91],[2.04,.23,.20],'alloy');m.box([0,1.09,2.89],[1.08,.30,.09],'dark')
    for x in np.linspace(-.47,.47,14):m.box([x,1.10,2.944],[.015,.24,.018],'steel')
    m.panel([[-.20,1.025,2.96],[.20,1.025,2.96],[.20,1.17,2.96],[-.20,1.17,2.96]],'chevy_badge')
    for side in [-1,1]:m.box([side*.77,1.09,2.918],[.42,.19,.08],'headlight');m.box([side*.77,.89,2.934],[.42,.12,.08],'amber')
    vehicle_wheels(m,axles,1.02,.407,'steel','steel');return m

def bike(owner):
    m=MeshBuilder('bike_'+owner);husky=owner=='jordan';plastic='husky_white' if husky else 'yamaha_blue';rim='alloy' if husky else 'rim_blue';seat='black_seat' if husky or owner=='sam' else 'blue_seat'
    # Upright on a compact maintenance stand; geometry includes real open spokes.
    rear=[0,.42,-.735];front=[0,.44,.745]
    m.wheel(*rear,.335,.126,rim,spokes=32,knobs=True);m.wheel(*front,.357,.095,rim,spokes=32,knobs=True)
    for side in [-1,1]:
        # Swingarm, twin frame spars, lower cradle, rear subframe.
        m.beam([side*.15,.50,-.20],[side*.08,.42,-.735],.038,'alloy',6)
        m.beam([side*.17,.56,-.20],[side*.14,1.06,.27],.042 if not husky else .026,'alloy' if not husky else 'dark',6)
        m.tube([[side*.14,.81,.29],[side*.16,.47,.18],[side*.15,.39,-.18],[side*.16,.56,-.25]],.025,'alloy' if not husky else 'dark',6)
        m.tube([[side*.14,.56,-.20],[side*.16,.88,-.72],[side*.13,1.00,-.34],[side*.14,1.06,.27]],.017,'alloy',6)
        m.beam([side*.102,.44,.745],[side*.104,.88,.51],.024,'alloy',12);m.beam([side*.104,.82,.55],[side*.104,1.27,.33],.034,'alloy' if husky else 'fork_gold',12)
        m.beam([side*.104,.46,.73],[side*.104,.75,.60],.030,plastic,10)
    # Brake discs, hubs, chain/sprocket and a visible rear spring.
    m.beam([-.075,.42,-.735],[-.083,.42,-.735],.145,'steel',28);m.beam([.059,.44,.745],[.066,.44,.745],.115,'steel',28)
    m.tube([[-.095,.49,-.735],[-.185,.52,-.15],[-.18,.43,-.15],[-.095,.35,-.735],[-.095,.49,-.735]],.006,'dark',4)
    spring=[[.02*math.cos(t),.52+.36*i/71,-.29+.02*math.sin(t)] for i,t in enumerate(np.linspace(0,14*math.pi,72))];m.tube(spring,.006,'white' if husky else 'fork_gold',5)
    m.loft([[-.30,.40,.63,.67,.115,.095],[.13,.41,.66,.74,.15,.11],[.24,.46,.68,.71,.09,.085]],'engine')
    for side in [-1,1]:m.beam([side*.116,.54,-.105],[side*.185,.54,-.105],.13,'engine',24);m.beam([side*.19,.54,-.105],[side*.195,.54,-.105],.092,'dark',20)
    m.box([0,.77,.06],[.19,.15,.21],'engine')
    for y in np.linspace(.73,.83,6):m.box([0,y,.055],[.23,.013,.22],'alloy')
    # Radiator cores under the graphics, visible fins and hoses.
    for side in [-1,1]:
        m.box([side*.13,.85,.27],[.08,.28,.16],'dark')
        for yy in np.linspace(.73,.97,10):m.box([side*.176,yy,.27],[.013,.012,.17],'steel')
    m.tube([[.12,.75,.20],[.25,.70,.32],[.27,.58,.10],[.23,.72,-.18],[.24,.88,-.52]],.023,'steel',10)
    m.beam([.25,.86,-.42],[.25,.88,-.79],.057,'alloy',12);m.beam([.25,.88,-.79],[.25,.88,-.825],.045,'dark',12)
    # Tank/seat/fenders are separate shaped shells, not a single solid bike slab.
    m.loft([[-.73,.92,.97,1.01,.12,.09],[-.35,.94,1.00,1.05,.14,.12],[.17,.98,1.04,1.07,.11,.10]],seat)
    for z in np.linspace(-.64,.08,10):m.box([0,1.051 if z>-.35 else 1.018,z],[.225,.008,.017],seat)
    m.loft([[-1.06,.965,.972,.978,.085,.075],[-.83,.972,1.001,1.01,.115,.10],[-.56,.944,.986,1.00,.14,.115]],plastic)
    m.loft([[.47,.965,.976,.99,.115,.10],[.70,1.04,1.065,1.076,.115,.09],[.94,1.046,1.07,1.077,.095,.075],[1.16,1.012,1.024,1.03,.07,.05]],plastic)
    for side in [-1,1]:
        x=side*.245
        m.panel([[x,.70,-.73],[x,.73,-.24],[side*.19,.98,-.22],[side*.18,.99,-.73]],owner+'_number',side>0)
        m.panel([[side*.20,.71,-.10],[side*.23,.75,.29],[side*.205,1.017,.36],[side*.18,1.015,-.14]],owner+'_shroud',side>0)
        m.beam([side*.15,.49,-.23],[side*.27,.49,-.23],.014,'steel',6);m.box([side*.265,.49,-.23],[.085,.018,.075],'steel')
    m.panel([[-.145,.993,.518],[.145,.993,.518],[.14,1.266,.385],[-.14,1.266,.385]],owner+'_number')
    m.beam([-.13,1.24,.35],[.13,1.24,.35],.027,'alloy',10)
    m.tube([[-.405,1.30,.38],[-.24,1.30,.36],[-.14,1.24,.32],[.14,1.24,.32],[.24,1.30,.36],[.405,1.30,.38]],.012,'alloy',8)
    for side in [-1,1]:m.beam([side*.27,1.30,.365],[side*.405,1.30,.38],.019,'rubber',10);m.beam([side*.24,1.29,.39],[side*.38,1.27,.46],.006,'alloy',5)
    m.box([0,1.27,.36],[.23,.055,.055],'dark');m.tube([[.30,1.30,.37],[.27,1.39,.46],[.09,1.31,.51],[.10,.63,.66]],.003,'dark',4)
    # Square open workshop stand visible below the engine.
    for x in [-.14,.14]:
        for z in [-.24,.08]:m.beam([x,.40,z],[x*1.30,.04,z*1.2],.012,'alloy' if owner=='premier' else 'dark',6)
    for z in [-.24,.08]:m.beam([-.14,.40,z],[.14,.40,z],.012,'alloy',6)
    m.box([0,.405,-.08],[.32,.024,.35],'dark');return m

BUILDERS={'truck_jordan':cybertruck,'truck_premier':lambda:pickup('premier'),'truck_sam':lambda:pickup('sam'),'van_shane':van,**{'bike_'+o:lambda o=o:bike(o) for o in ['jordan','premier','sam','shane']}}

def main():
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;spec=read(S/'vehicles.json');allmeshes=[];catalog=[]
    for a in spec['assets']:
        m=BUILDERS[a['id']]();parts=m.place(a['xz'],a['heading'],H);allmeshes+=parts;vv=np.concatenate([np.asarray(p['vertices']) for p in m.parts.values()]);dims=np.ptp(vv,axis=0)
        catalog.append(dict(**a,dimensions_xyz_m=dims.tolist(),vertices=sum(len(p['vertices']) for p in parts),triangles=sum(len(p['faces']) for p in parts),material_count=len(parts)))
    save(O/'vehicle_meshes.json',allmeshes);save(O/'vehicle_catalog.json',catalog);print('Authored vehicle/bike geometry:',len(catalog),'assets',sum(a['triangles'] for a in catalog),'triangles')
if __name__=='__main__':main()
