"""Render serialized sign UVs and source placement; previews are not game screenshots."""
from PIL import ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from v032_common import *
from v032_sign import render_side
from v027_scenery import parse, child, geometry_records, vertices
from rebind_scenery import array

def font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(p).is_file():return ImageFont.truetype(p,size)
    return ImageFont.load_default(size=size)

def main():
    cfg=read(S/'memorial_spec.json');nodes,_=parse((O/'scenery.fbx').read_bytes());records=geometry_records(nodes)
    g=records[cfg['asset_id']+'_memorial'][0];v=vertices(g);faces=[];f=[]
    for i in array(child(g,b'PolygonVertexIndex')):
        f.append(int(i) if i>=0 else -int(i)-1)
        if i<0:faces.append(f);f=[]
    uv=array(child(child(g,b'LayerElementUV'),b'UV')).reshape(4,3,2);texture=np.asarray(Image.open(O/'facility_textures/v032_pup_whatley_memorial.tga').convert('RGB'))
    w=775;h=round(w*cfg['image_height_m']/cfg['image_width_m']);canvas=Image.new('RGB',(1800,1020),(240,239,235));d=ImageDraw.Draw(canvas)
    d.text((40,20),'Orlando MX v032 | Pup Whatley Memorial',font=font(35),fill=(25,28,28))
    d.text((40,71),'8.0 m wide x 6.4 m high artwork | 4096 px native texture | approved RIP PUP design',font=font(22),fill=(64,67,67))
    for col,offset in enumerate([0,2]):
        x=70+col*890;y=164;d.text((x,117),'Face '+str(col+1)+' - serialized native UV projection',font=font(23),fill=(37,40,40))
        for post in [-.4125,0,.4125]:
            px=x+w/2+post*w;d.rectangle([px-12,y+h,px+12,y+h+116],fill=(43,45,47));d.rectangle([px-30,y+h+116,px+30,y+h+130],fill=(145,143,137))
        d.rectangle([x-13,y-13,x+w+13,y+h+13],fill=(43,45,47));canvas.paste(render_side(v,faces,uv,texture,offset,w,h),(x,y))
    d.text((40,960),'Source rendering of native mesh/UV data. In-game lighting, appearance and performance still require a ride.',font=font(20),fill=(70,72,72))
    image_file(canvas,O/'memorial_preview.png')
    fig,ax=plt.subplots(figsize=(12,9),dpi=170);ax.set_facecolor('#c2c5a6')
    pits=read(R/'V016_SOURCE/pit_facilities.json')
    for road in pits['roads']:
        p=np.array(road['points']);ax.plot(p[:,0],p[:,1],color='#b7ac98',linewidth=road['width']*5,zorder=1)
    for name,(geom,_) in records.items():
        if name.startswith('v032_pup'):continue
        pts=vertices(geom)[:,[0,2]];lo=pts.min(0);hi=pts.max(0)
        if hi[0]<260 or lo[0]>355 or hi[1]<90 or lo[1]>178:continue
        leaf='leaf' in name;color='#617245' if leaf else '#6a6b64'
        ax.add_patch(Rectangle(lo,*(hi-lo),facecolor=color,alpha=.22 if leaf else .38,linewidth=.35,edgecolor=color))
    for a in pits['assets']:
        if 265<a['xz'][0]<351 and a['type'] in ['office','restroom','covered_stand','bleachers']:
            ax.annotate(a['id'].replace('_',' '),a['xz'],xytext=(0,6),textcoords='offset points',fontsize=8,ha='center')
    for row in range(3):
        for col in range(8):ax.scatter(260+col*10,110+row*7,s=15,c='#e8eee8',edgecolors='#5d6958',linewidths=.5)
    x,z=cfg['xz_m'];ax.plot([x-4,x+4],[z,z],color='#af3334',linewidth=7,zorder=5);ax.annotate('PUP WHATLEY MEMORIAL\n8 m wide, artwork on both faces',(x,z),xytext=(305,128),arrowprops=dict(arrowstyle='->',color='#7e2022'),bbox=dict(facecolor='white',edgecolor='#7e2022',pad=7),fontsize=10,color='#7e2022')
    ax.set(xlim=(258,355),ylim=(89,179),xlabel='Game X (metres)',ylabel='Game Z (metres)',title='v032 main-pit memorial placement | source plan, not a game screenshot');ax.set_aspect('equal');ax.grid(alpha=.13)
    fig.tight_layout();b=io.BytesIO();fig.savefig(b,format='png');plt.close(fig);atomic(O/'memorial_placement.png',b.getvalue())
    print('Memorial faces, pit placement and entry-sign source previews written.',flush=True)
if __name__=='__main__':main()
