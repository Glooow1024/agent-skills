"""Generate the authored Orbit vector mark and Windows icon at multiple sizes."""
from pathlib import Path
import math
from PIL import Image,ImageDraw
root=Path(__file__).parent/'assets';root.mkdir(exist_ok=True)
S=1024;im=Image.new('RGBA',(S,S));d=ImageDraw.Draw(im)
d.rounded_rectangle((24,24,1000,1000),radius=250,fill='#14263B')
points=[]
for i in range(151):
    a=math.radians(-40+i*2.1)
    x,y=340*math.cos(a),235*math.sin(a)
    t=math.radians(-32)
    points.append((512+x*math.cos(t)-y*math.sin(t),512+x*math.sin(t)+y*math.cos(t)))
for i in range(len(points)-1):
    v=i/(len(points)-1);color=(int(32+48*v),int(152+75*v),int(176+30*v),255)
    d.line([points[i],points[i+1]],fill=color,width=76)
    x,y=points[i];d.ellipse((x-38,y-38,x+38,y+38),fill=color)
spark=[(512,305),(562,462),(719,512),(562,562),(512,719),(462,562),(305,512),(462,462)]
d.polygon(spark,fill='#F4FFFD')
x,y=points[-1];d.ellipse((x-64,y-64,x+64,y+64),fill='#FFCE78')
im.save(root/'orbit.ico',sizes=[(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(96,96),(128,128),(256,256)])
im.save(root/'orbit-1024.png')
im.resize((96,96),Image.Resampling.LANCZOS).save(root/'orbit.png')
path=' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
star=' '.join(f'{x},{y}' for x,y in spark)
(root/'orbit.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><rect x="24" y="24" width="976" height="976" rx="250" fill="#14263b"/><polyline points="{path}" fill="none" stroke="#40cfcb" stroke-width="76" stroke-linecap="round"/><polygon points="{star}" fill="#f4fffd"/><circle cx="{x}" cy="{y}" r="64" fill="#ffce78"/></svg>',encoding='utf-8')
