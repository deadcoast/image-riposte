"""Original geometric test fixtures. Synthetic control, NOT AI protection."""
import argparse
import datetime as dt
import os
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog
from riposte.lab import compare_external
PALETTES=[('#f2e9d4','#243337','#d46145'),('#eee9df','#203b42','#c39a53'),('#dedfd0','#26382f','#b37849'),('#f1e7d8','#402f37','#bb704b'),('#e6e4dc','#273a48','#8d9180'),('#f1e8db','#253336','#9c594b')]
def draw_fixture(index):
    bg,ink,accent=PALETTES[index%6];im=Image.new('RGB',(800,800),bg);d=ImageDraw.Draw(im)
    if index%6==0:
        d.ellipse((130,112,670,650),fill=accent)
        for i in range(12):
            x=115+i*48;d.line((x,705,x+140,90),fill=ink,width=5)
        d.polygon([(200,565),(398,163),(620,565)],fill=ink)
        d.ellipse((300,345,505,550),fill=bg);d.ellipse((355,398,450,494),fill=accent)
        d.line((95,704,705,704),fill=ink,width=5)
    elif index%6==1:
        d.rectangle((138,123,670,677),fill=ink)
        for r in range(5):
            for c in range(5):
                x=168+c*96;y=157+r*96;d.arc((x,y,x+70,y+70),0,300,fill=bg,width=7)
        d.ellipse((278,261,559,543),fill=accent);d.ellipse((330,313,507,491),fill=ink)
    elif index%6==2:
        for i in range(13):
            inset=i*17;d.ellipse((108+inset,97+inset,700-inset,689-inset),outline=ink,width=4)
        d.rectangle((92,334,710,468),fill=bg)
        d.polygon([(155,483),(375,142),(585,483)],fill=accent)
        d.line((102,602,697,602),fill=ink,width=4)
        for i in range(9):d.line((124+i*66,622,124+i*66,692),fill=ink,width=3)
    elif index%6==3:
        for k in range(4):
            x=115+k*146;d.rounded_rectangle((x,132,x+112,674),radius=56,fill=ink)
            d.rounded_rectangle((x+24,165,x+88,645),radius=30,fill=bg)
        d.ellipse((259,244,560,545),fill=accent);d.rectangle((402,105,421,703),fill=ink)
    elif index%6==4:
        for i in range(9):
            s=i*25;d.polygon([(400,96+s),(695-s,400),(400,704-s),(105+s,400)],outline=ink,width=5)
        d.ellipse((260,260,540,540),fill=accent);d.line((110,691,690,110),fill=ink,width=13)
    else:
        d.ellipse((91,91,705,705),fill=ink)
        for i in range(12):
            y=147+i*43;d.line((120,y,680,y),fill=bg,width=5)
        d.polygon([(180,200),(615,400),(180,610)],fill=accent)
        d.polygon([(272,296),(500,401),(272,505)],fill=ink)
    d.rectangle((32,32,767,767),outline=ink,width=2)
    return im

def make_demo(root):
    root=Path(root)
    if root.exists():raise SystemExit('Refusing to replace an existing demonstration folder.')
    root.mkdir(parents=True)
    for i in range(6):
        path=root/'unsorted'/f'fixture-{i}.png';path.parent.mkdir(exist_ok=True)
        draw_fixture(i).save(path)
        stamp=dt.datetime(2026 if i<4 else 2025,9 if i<2 else 8 if i<4 else 12,10+i,12).timestamp();os.utime(path,(stamp,stamp))
    organize(root,Policy(date_mode='modified'))
    row=catalog(root)[0]
    with tempfile.NamedTemporaryFile(dir=root.parent,prefix='riposte-synthetic-control-',suffix='.png',delete=False) as handle:
        external=Path(handle.name)
    with Image.open(root/row['relative']) as im:
        a=np.asarray(im,dtype=np.int16);noise=np.random.default_rng(12).integers(-2,3,a.shape);Image.fromarray(np.clip(a+noise,0,255).astype(np.uint8)).save(external)
    r=compare_external(root,row['id'],external,max_edge=1536,method='external');external.unlink()
    report=root/'.riposte/lab'/r['id']/'report.json'
    import json
    value=json.loads(report.read_text());value['fixture']='Synthetic random-noise control; no AI protection claim.';report.write_text(json.dumps(value,indent=2))
    (root/'.riposte/DEMO').write_text('SYNTHETIC_FIXTURES\n')
    print('Created six geometric test fixtures and one synthetic transport control.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);make_demo(p.parse_args().destination)
