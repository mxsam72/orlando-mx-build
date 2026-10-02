"""Photo-derived owner vehicles and bikes. Dimensions are conservative estimates.
Distinct Cybertruck, King Ranch pickup, wrapped squared-body pickup and Chevy van.
"""
import math
import numpy as np
from vehicle_geometry_v023 import MeshBuilder
from v023_common import *

def arch_profile(length,axles,r,top,front_top=None):
    # Monotonic lower outline with semicircular wheel openings, closed along top.
    pts=[[-length/2,.45]]
    for axle in sorted(axles):
        pts += [[axle-r,.45]]
        for t in np.linspace(math.pi,0,13):pts.append([axle+r*math.cos(t),.45+r*math.sin(t)])
    pts += [[length/2,.45],[length/2,top if front_top is None else front_top],[1.15,top],[-length/2,top]]
    # Suppress repeated lower-arc endpoint vertices.
    clean=[]
    for p in pts:
        if not clean or np.linalg.norm(np.array(p)-clean[-1])>1e-7:clean.append(p)
    return clean

def skin_panel(m,zy,sections,side,mat):
    """Place glazing on the actual tapered body surface, with 12mm offset."""
    sec=np.array(sections);vv=[]
    for z,y in zy:
        shoulder,top,w,r=[np.interp(z,sec[:,0],sec[:,i]) for i in [2,3,4,5]]
        x=w if y<=shoulder else w+(r-w)*(y-shoulder)/(top-shoulder)
        vv.append([side*(x+.012),y,z])
    m.panel(vv,mat,side>0)

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
        m.prism(arch_profile(L,axles,.54,1.38,1.19),side*w-.05,side*w+.05,paint)
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
            if not sam and z0<-.3:continue  # Rear window carries continuous printed wrap.
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
            from vehicle_geometry_v023 import triangulate
            vs=[[side*(w+.064),yy,zz] for zz,yy in poly]
            material='premier_wrap_right' if side>0 else 'premier_wrap'
            def wrap(vs,poly):
                for tri in triangulate(poly):
                    uv=[[(poly[i][0]+2.62)/3.69,(poly[i][1]-.80)/1.15] for i in tri]
                    if side>0:uv=[[1-u,v] for u,v in uv]
                    m.add(vs,[tri],material,[uv]);m.add(vs,[list(reversed(tri))],material,[list(reversed(uv))])
            wrap(vs,poly)
            # Tessellate across the cab shoulder: a single flat quad cuts
            # through this bent body and hides most of the rear-window wrap.
            zs=np.linspace(-1.02,-.25,14);ys=np.unique(np.r_[np.linspace(1.385,1.95,15),1.40,1.42,1.77,1.87])
            for z0,z1 in zip(zs[:-1],zs[1:]):
                for y0,y1 in zip(ys[:-1],ys[1:]):
                    poly=[[z0,y0],[z1,y0],[z1,y1],[z0,y1]];vs=[]
                    for zz,yy in poly:
                        sh,top,wide,roof=[np.interp(zz,[-1.11,-.88,.47],[row[i] for row in [[1.77,1.98,w-.07,w-.21],[1.87,2.04,w-.06,w-.21],[1.87,2.02,w-.08,w-.21]]]) for i in range(4)]
                        xx=wide if yy<=sh else wide+(roof-wide)*(yy-sh)/(top-sh)
                        xx+=.022
                        if yy<1.42:xx=np.interp(yy,[1.385,1.42],[w+.065,xx])
                        vs.append([side*xx,yy,zz])
                    wrap(vs,poly)
    # Real bed cavity: floor, raised rails, front bulkhead and tailgate.
    m.box([0,.93,-2.0],[1.80,.10,1.65],'rubber')
    for side in [-1,1]:m.box([side*.95,1.43,-2.0],[.15,.12,1.73],'dark' if not sam else paint)
    m.box([0,1.20,-2.91],[2.02,.56,.11],paint if sam else 'premier_blue');m.box([0,1.46,-2.93],[2.02,.08,.15],'dark');m.box([0,1.32,-2.985],[.28,.05,.024],'dark')
    m.box([0,.62,-2.99],[2.13,.20,.22],'alloy' if sam else 'steel');m.box([0,.71,-3.015],[1.30,.04,.23],'dark');m.box([0,.48,-3.08],[.22,.10,.28],'dark')
    for side in [-1,1]:m.box([side*.88,1.12,-2.995],[.23,.47,.045],'red_light');m.box([side*.88,1.12,-3.022],[.22,.055,.015],'headlight')
    if not sam:m.panel([[.72,.92,-2.978],[-.72,.92,-2.978],[-.72,1.42,-2.978],[.72,1.42,-2.978]],'premier_tail')
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
    for side in [-1,1]:m.prism(arch_profile(L,axles,.57,1.34,1.07),side*w-.048,side*w+.048,'cyber_steel')
    shell=[[-2.835,.85,1.40,1.45,1.055,.99],[-1.02,.92,1.34,1.89,1.055,.87],[.06,.92,1.34,1.92,1.055,.84],[2.82,.84,1.08,1.18,1.01,.97]]
    m.loft(shell,'cyber_steel')
    # Windshield forms the long planar nose slope; four trapezoidal side windows.
    m.panel([[-.92,1.285,2.48],[.92,1.285,2.48],[.82,1.925,.10],[-.82,1.925,.10]],'glass')
    for side in [-1,1]:
        x=side*1.060
        skin_panel(m,[[-.96,1.43],[-.12,1.40],[-.04,1.86],[-.96,1.83]],shell,side,'glass')
        skin_panel(m,[[-.04,1.40],[1.86,1.23],[.10,1.85],[-.04,1.87]],shell,side,'glass')
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
    for side in [-1,1]:m.prism(arch_profile(L,axles,.48,1.32,1.20),side*w-.045,side*w+.045,'van_paint')
    # Full-height cargo shell with curved shoulders and short separate hood.
    shell=[[-2.84,.80,1.99,2.17,.97,.79],[-2.57,.80,2.04,2.23,1.035,.85],[.68,.80,2.04,2.23,1.035,.85],[1.49,.80,1.45,1.53,1.015,.88]]
    m.loft(shell,'van_paint')
    m.loft([[1.40,.77,1.37,1.42,1.00,.87],[2.40,.74,1.29,1.36,.995,.83],[2.84,.70,1.21,1.29,.96,.78]],'van_paint')
    m.panel([[-.80,1.558,1.475],[.80,1.558,1.475],[.80,2.195,.74],[-.80,2.195,.74]],'glass')
    for side in [-1,1]:
        skin_panel(m,[[0,1.42],[1.35,1.42],[.73,2.10],[0,2.11]],shell,side,'glass')
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
    """v023 custom photo-derived motocross bike mesh.

    Replaces the v019 narrow procedural silhouette with a fuller chassis:
    twin-spar/cradle frame, engine cases/cylinder, radiators, swingarm, shock,
    fork/triple-clamps, discs/calipers, chain/sprocket, shaped plastics,
    exhaust/muffler, cockpit controls and raised textured graphic panels.
    """
    m=MeshBuilder('bike_'+owner)
    def rotor(x,y,z,r,mat,teeth=False):
        # Open annulus and six hub arms; solid cylinders hid the wheel spokes.
        n=60;v=[]
        for rr in [r*.72,r]:
            v += [[x,y+(rr*(1.025 if teeth and i%2==0 else 1))*math.sin(i*math.tau/n),z+(rr*(1.025 if teeth and i%2==0 else 1))*math.cos(i*math.tau/n)] for i in range(n)]
        faces=[]
        for i in range(n):
            f=[i,(i+1)%n,(i+1)%n+n,i+n];faces += [f,f[::-1]]
        m.add(v,faces,mat)
        for t in np.linspace(0,math.tau,6,endpoint=False):
            m.beam([x,y+.027*math.sin(t+.3),z+.027*math.cos(t+.3)],[x,y+r*.76*math.sin(t),z+r*.76*math.cos(t)],.008,mat,5)
    def oval(c,r,mat):
        n=24;v=[[c[0]+r[0]*math.sin(a)*math.cos(b),c[1]+r[1]*math.cos(a),c[2]+r[2]*math.sin(a)*math.sin(b)] for a in np.linspace(0,math.pi,13) for b in np.linspace(0,math.tau,n,endpoint=False)]
        m.add(v,[[j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i] for j in range(12) for i in range(n)],mat)
    def curved_fender(sections,mat):
        from scipy.interpolate import PchipInterpolator
        a=np.asarray(sorted(sections));zz=np.linspace(a[0,0],a[-1,0],22);yy=PchipInterpolator(a[:,0],a[:,1])(zz);ww=PchipInterpolator(a[:,0],a[:,2])(zz)
        v=[[u*w,y+.025*(1-u*u)-th,z] for th in [0,.014] for z,y,w in zip(zz,yy,ww) for u in np.linspace(-1,1,7)];n=len(zz)*7;f=[]
        for j in range(len(zz)-1):
            for i in range(6):
                k=j*7+i;q=[k,k+7,k+8,k+1];f += [q,[x+n for x in q[::-1]]]
            for i in [0,6]:k=j*7+i;f.append([k,k+n,k+n+7,k+7])
        for j in [0,len(zz)-1]:
            for i in range(6):k=j*7+i;f.append([k,k+1,k+n+1,k+n])
        m.add(v,f,mat)
    husky=owner=='jordan'
    plastic='husky_white' if husky else 'yamaha_blue'
    rim='wheel_black' if husky else ('rim_blue' if owner in ['premier','sam'] else 'alloy')
    seat='black_seat' if husky or owner=='sam' else 'blue_seat'
    forkmat='alloy' if husky else 'fork_gold'
    rear=[0,.43,-.74];front=[0,.45,.77]

    # Proper motocross wheels: knobby carcass, rims, hubs and 32 open spokes.
    m.wheel(*rear,.337,.132,rim,spokes=32,knobs=True)
    m.wheel(*front,.360,.100,rim,spokes=32,knobs=True)

    # Hubs / brake rotors / calipers / rear sprocket.
    rotor(-.086,.43,-.74,.140,'steel',True)
    rotor(.072,.45,.77,.125,'steel')
    rotor(.088,.43,-.74,.112,'alloy')
    m.box([-.115,.55,.72],[.050,.11,.055],'dark')
    m.box([-.122,.52,-.68],[.052,.10,.060],'dark')

    # Swingarm is a tapered twin-arm structure instead of two isolated rods.
    for side in [-1,1]:
        m.beam([side*.155,.55,-.17],[side*.085,.43,-.74],.041,'alloy',8)
        m.beam([side*.155,.50,-.18],[side*.085,.39,-.74],.030,'alloy',8)
        m.beam([side*.155,.55,-.17],[side*.155,.50,-.18],.035,'alloy',8)

    # Twin-spar frame + lower cradle around engine.
    frame='dark' if husky else 'alloy'
    for side in [-1,1]:
        m.beam([side*.145,1.055,.28],[side*.185,.61,-.13],.036,frame,8)
        m.beam([side*.185,.61,-.13],[side*.150,.42,-.18],.030,frame,8)
        m.beam([side*.150,.42,-.18],[side*.120,.45,.22],.025,frame,8)
        m.beam([side*.120,.45,.22],[side*.145,1.055,.28],.029,frame,8)
        m.beam([side*.175,.60,-.12],[side*.145,.90,-.58],.021,'alloy',7)
        m.beam([side*.145,.90,-.58],[side*.115,1.00,-.32],.019,'alloy',7)

    # Engine cases, cylinder/head and cooling fins.
    m.beam([-.135,.57,-.08],[.135,.57,-.08],.175,'engine',28)
    m.beam([-.115,.67,.04],[.115,.67,.04],.145,'engine',24)
    oval([0,.77,.10],[.125,.165,.145],'engine')
    oval([0,.90,.145],[.12,.065,.14],'alloy')
    for yy in np.linspace(.76,.90,6):m.beam([0,yy,.11],[0,yy+.008,.11],.119,'steel',20)
    # Small clutch/ignition case caps.
    m.beam([.142,.58,-.08],[.150,.58,-.08],.105,'steel',24)
    m.beam([-.142,.58,-.08],[-.150,.58,-.08],.090,'dark',24)

    # Intake boot, airbox and radiator cores.
    m.tube([[0,.79,.03],[0,.87,-.12],[0,.91,-.31]],.045,'rubber',10)
    for side in [-1,1]:
        m.box([side*.155,.88,.27],[.060,.31,.18],'dark')
        for yy in np.linspace(.75,1.00,11):m.box([side*.190,yy,.27],[.010,.010,.19],'steel')

    # Header follows the front of the motor then sweeps to a real muffler.
    m.tube([[.105,.89,.22],[.205,.82,.34],[.265,.68,.26],[.265,.58,.03],[.255,.70,-.28],[.255,.86,-.53]],.025,'steel',10)
    m.beam([.255,.86,-.50],[.255,.88,-.88],.060,'alloy',14)
    m.beam([.255,.88,-.86],[.255,.885,-.915],.046,'dark',14)

    # Rear shock body and helical spring.
    m.beam([0,.60,-.16],[0,.95,-.37],.026,'steel',10)
    spring=[[.033*math.cos(t),.61+.33*i/79,-.17-.20*i/79+.033*math.sin(t)] for i,t in enumerate(np.linspace(0,15*math.pi,80))]
    m.tube(spring,.006,'white' if husky else 'fork_gold',5)

    # Steering head, triple clamps, fork tubes and plastic fork guards.
    m.beam([-.16,1.08,.30],[.16,1.08,.30],.040,frame,10)
    m.beam([-.17,1.22,.35],[.17,1.22,.35],.035,'alloy',10)
    for side in [-1,1]:
        m.beam([side*.110,1.25,.34],[side*.105,.83,.56],.033,forkmat,12)
        m.beam([side*.105,.83,.56],[side*.100,.47,.76],.025,'steel',12)
        # tapered-looking fork guard with two parallel rails and curved front brace
        m.beam([side*.125,.82,.55],[side*.125,.49,.72],.038,plastic,10)
        m.beam([side*.125,.49,.72],[side*.100,.45,.77],.028,plastic,10)

    # Chain and sprocket: two chain runs from countershaft to rear sprocket.
    m.tube([[-.105,.61,-.14],[-.105,.52,-.73]],.006,'dark',4)
    m.tube([[-.105,.54,-.14],[-.105,.36,-.73]],.006,'dark',4)

    # Shaped tank/airbox and full-width seat; these give the bike a real 3-D volume.
    m.loft([[-.72,.88,.93,1.00,.14,.105],[-.43,.90,1.00,1.07,.17,.14],[-.06,.88,1.07,1.13,.18,.13],[.24,.90,1.08,1.12,.145,.105]],plastic)
    m.loft([[-.84,.96,1.00,1.035,.12,.10],[-.49,1.00,1.055,1.075,.15,.13],[-.10,1.045,1.085,1.095,.15,.13],[.18,1.05,1.075,1.082,.12,.10]],seat)

    # Long rear fender and arched front fender, each with genuine thickness/width.
    curved_fender([[-1.12,.955,.065],[-.88,1.018,.115],[-.58,1.012,.145],[-.35,.978,.13]],plastic)
    curved_fender([[.38,.990,.105],[.64,1.080,.120],[.86,1.092,.105],[1.20,1.038,.060]],plastic)

    # 3-D side number plate backing + flush textured face.
    for side in [-1,1]:
        sx=side*.225
        m.prism([[-.76,.72],[-.27,.75],[-.24,.995],[-.74,1.005]],min(side*.181,side*.188),max(side*.181,side*.188),plastic)
        m.panel([[side*.225,.72,-.76],[side*.225,.75,-.27],[side*.205,.995,-.24],[side*.195,1.005,-.74]],owner+'_number',side>0)
        # Radiator shroud backing and photo-derived graphics.
        m.prism([[-.11,.72],[.30,.75],[.38,1.035],[-.15,1.025]],min(side*.175,side*.183),max(side*.175,side*.183),plastic)
        m.panel([[side*.235,.72,-.11],[side*.245,.75,.30],[side*.218,1.035,.38],[side*.198,1.025,-.15]],owner+'_shroud',side>0)

    # Front plate backing plus textured number panel.
    plate=np.array([[-.150,.995,.537],[.150,.995,.537],[.145,1.265,.480],[-.145,1.265,.480]])
    vv=np.r_[plate-[0,0,.005],plate-[0,0,.012]]
    m.add(vv,[[4,5,6,7],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]],plastic)
    m.panel(plate.tolist(),owner+'_number')

    # Bar, grips, controls, levers and cables.
    m.beam([-.15,1.25,.35],[.15,1.25,.35],.028,'alloy',10)
    m.tube([[-.42,1.31,.38],[-.24,1.31,.36],[-.14,1.26,.33],[.14,1.26,.33],[.24,1.31,.36],[.42,1.31,.38]],.013,'alloy',8)
    for side in [-1,1]:
        m.beam([side*.27,1.31,.365],[side*.42,1.31,.38],.020,'rubber',10)
        m.beam([side*.22,1.30,.39],[side*.39,1.275,.47],.006,'alloy',5)
    m.box([0,1.275,.36],[.23,.055,.055],'dark')
    m.tube([[.31,1.30,.37],[.28,1.39,.46],[.10,1.31,.51],[.10,.63,.66]],.003,'dark',4)

    # Footpegs, rear brake pedal and shifter.
    for side in [-1,1]:
        m.beam([side*.16,.50,-.18],[side*.30,.50,-.18],.014,'steel',6)
        m.box([side*.295,.50,-.18],[.095,.025,.080],'steel')
    m.tube([[-.18,.52,-.10],[-.30,.49,.02]],.009,'steel',5)
    m.tube([[.18,.52,-.10],[.30,.48,.04]],.009,'steel',5)

    # Compact open workshop stand below motor.
    for x in [-.15,.15]:
        for z in [-.25,.09]:m.beam([x,.40,z],[x*1.28,.04,z*1.18],.013,'alloy' if owner=='premier' else 'dark',6)
    for z in [-.25,.09]:m.beam([-.15,.40,z],[.15,.40,z],.013,'alloy',6)
    m.box([0,.405,-.08],[.34,.024,.36],'dark')
    return m

BUILDERS={'truck_jordan':cybertruck,'truck_premier':lambda:pickup('premier'),'truck_sam':lambda:pickup('sam'),'van_shane':van,**{'bike_'+o:lambda o=o:bike(o) for o in ['jordan','premier','sam','shane']}}

def main():
    H=np.fromfile(O/'terrain.raw','<u2').reshape(N,N)/65535*SCALE;spec=read(S/'vehicles.json');allmeshes=[];catalog=[]
    for a in spec['assets']:
        m=BUILDERS[a['id']]();parts=m.place(a['xz'],a['heading'],H);allmeshes+=parts;vv=np.concatenate([np.asarray(p['vertices']) for p in m.parts.values()]);dims=np.ptp(vv,axis=0)
        catalog.append(dict(**a,dimensions_xyz_m=dims.tolist(),vertices=sum(len(p['vertices']) for p in parts),triangles=sum(len(p['faces']) for p in parts),material_count=len(parts)))
    save(O/'vehicle_meshes.json',allmeshes);save(O/'vehicle_catalog.json',catalog);print('Authored vehicle/bike geometry:',len(catalog),'assets',sum(a['triangles'] for a in catalog),'triangles')
if __name__=='__main__':main()
