# Executed inside create_scene.py before FBX export; coordinates are game metres.
def custommesh(name,V,F,material):
    me=bpy.data.meshes.new(name);me.from_pydata(V,[],F);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);finish(ob,name,material)
    uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for j,li in enumerate(p.loop_indices):uv.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][j%4]
    return ob
for key,color in {'white':(.81,.80,.75),'blue':(.13,.27,.35),'red':(.56,.17,.10),'glass':(.12,.20,.23),'rubber':(.055,.06,.065),'water':(.24,.29,.25)}.items():mats[key]=mat(key,color)
# Source-transformed water polygons sit in the terrain basins.
for i,poly in enumerate(spec['pond_polygons']):
    c=np.mean(poly,axis=0);V=[vec(c[0],spec['water_level'],c[1])]+[vec(x,spec['water_level'],z) for x,z in poly];F=[(0,j+1,(j+1)%len(poly)+1) for j in range(len(poly))];custommesh('drainage_water_'+str(i),V,F,'water')
def wheel(x,y,z,name):tube(name,vec(x,y,z-.13),vec(x,y,z+.13),.38,'rubber',10)
def truck(x,z,i,color):
    y=height(x,z);cube('pickup_body_'+str(i),vec(x,y+.74,z),(5.4,1.94,.48),color);cube('pickup_hood_'+str(i),vec(x+1.6,y+1.09,z),(1.5,1.91,.32),color);cube('pickup_cab_'+str(i),vec(x+.15,y+1.42,z),(2.05,1.87,1.02),color);cube('windshield_'+str(i),vec(x+1.185,y+1.58,z),(.025,1.62,.55),'glass')
    for dz in [-.947,.947]:cube('sideglass_'+str(i)+str(dz),vec(x+.2,y+1.64,z+dz),(1.65,.025,.45),'glass')
    cube('bed_'+str(i),vec(x-1.78,y+1.05,z),(1.6,1.55,.05),'rubber')
    for dz in [-.85,.85]:cube('bedrail_'+str(i)+str(dz),vec(x-1.78,y+1.22,z+dz),(1.7,.17,.35),color)
    for dx in [-1.6,1.55]:
        for dz in [-1,1]:wheel(x+dx,y+.46,z+dz,f'wheel_{i}_{dx}_{dz}')
    for dz in [-.64,.64]:cube('headlight_'+str(i)+str(dz),vec(x+2.71,y+.9,z+dz),(.035,.43,.20),'white')
def trailer(x,z,i):
    y=height(x,z);cube('trailer_'+str(i),vec(x,y+1.65,z),(5.3,2.45,2.55),'white');cube('trailer_roof_'+str(i),vec(x,y+2.96,z),(5.5,2.55,.12),'roof');cube('trailer_door_'+str(i),vec(x-2.66,y+1.7,z),(.02,2.15,2.1),'metal');cube('stripe_'+str(i),vec(x,y+1.15,z-1.235),(5.15,.018,.25),'blue')
    for dx in [-.6,.4]:
        for dz in [-1.24,1.24]:wheel(x+dx,y+.5,z+dz,f'trailerwheel_{i}_{dx}_{dz}')
    tube('hitch_'+str(i),vec(x+2.6,y+.6,z),vec(x+4,y+.6,z),.06,'metal')
for i,x in enumerate([257,276,295,314,333]):trailer(x,92,i);truck(x+8,92,i,['white','blue','red','white','white'][i])
for i,x in enumerate([358,371,384]):truck(x,129,i+10,['white','blue','white'][i])
for i in range(3):cube('portable_toilet_'+str(i),vec(351+i*1.4,4.1,101),(1.15,1.15,2.2),'blue');cube('toilet_roof_'+str(i),vec(351+i*1.4,5.25,101),(1.25,1.25,.15),'white')
# Original track identifier on the timing shelter.
from PIL import Image,ImageDraw,ImageFont
im=Image.new('RGB',(1024,256),(30,43,39));ImageDraw.Draw(im).text((46,59),'ORLANDO MX',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',110),fill=(239,233,210));im.save(ROOT/'04_TEXTURES/sign.tga');m=bpy.data.materials.new('sign');m.use_nodes=True;tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'04_TEXTURES/sign.tga'));m.node_tree.links.new(tex.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);mats['sign']=m
x,z=354,169;y=height(x,z);cube('timing_shelter',vec(x,y+1.5,z),(6,3.8,3),'white');cube('timing_roof',vec(x,y+3.08,z),(6.6,4.3,.18),'roof');cube('timing_window',vec(x,y+2,z+1.915),(4.9,.025,.9),'glass');custommesh('timing_sign',[vec(x-2.8,y+3.35,z+1.95),vec(x+2.8,y+3.35,z+1.95),vec(x+2.8,y+4.75,z+1.95),vec(x-2.8,y+4.75,z+1.95)],[(0,1,2,3)],'sign')
# Low vegetation beyond racing shoulders; no collision.
for i in range(300):
    x=rng.uniform(lo[0]-18,hi[0]+18);z=rng.uniform(lo[1]-15,hi[1]+18);d=float(np.linalg.norm(q[::4,:2]-[x,z],axis=1).min())
    if d<8 or d>16 or (228<x<352 and 96<z<177):continue
    V=[];F=[];y=height(x,z)
    for k in range(15):
        a=rng.random()*math.tau;r=rng.uniform(.2,1.3);cx=x+r*math.cos(a);cz=z+r*math.sin(a);h=rng.uniform(.5,1.3);j=len(V);V.extend([vec(cx-.22,y,cz),vec(cx+.22,y,cz),vec(cx+.1,y+h,cz+.12),vec(cx-.1,y+h,cz+.12)]);F.append((j,j+1,j+2,j+3))
    custommesh('scrub_'+str(i),V,F,'foliage_light')

