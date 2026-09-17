"""Developer capture of the actual ASCII cell renderer; no mock screen or fonts bundled."""
from pathlib import Path
import argparse, datetime as dt, os, sys
from PIL import Image, ImageDraw, ImageFont
from riposte.terminal.controller import Controller
from riposte.terminal.output import Presentation
from riposte.terminal.render import render
from riposte.terminal.keyboard import Key
from riposte.organizer import organize
from riposte.policy import Policy
from make_demo import draw_fixture


def make_art(root):
    root.mkdir(parents=True,exist_ok=False)
    for i in range(6):
        path=root/f'fixture-{i}.png';draw_fixture(i).save(path)
        stamp=dt.datetime(2026 if i<4 else 2025,9 if i<2 else 8 if i<4 else 12,10+i,12).timestamp();os.utime(path,(stamp,stamp))
    organize(root,Policy(date_mode='modified'))


def raster(surface, scale=1, background="#171B22", transparent=False):
    # Background here simulates a HOST TERMINAL for captures only. Runtime cells
    # always use the terminal default background; transparent=True preserves alpha.
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14*scale)
    cw,ch=9*scale,19*scale
    backdrop=(0,0,0,0) if transparent else background
    out=Image.new('RGBA' if transparent else 'RGB',(surface.width*cw,surface.height*ch),backdrop);d=ImageDraw.Draw(out)
    for y,row in enumerate(surface.cells):
        for x,cell in enumerate(row):
            fg=surface.palette.get(cell.fg,cell.fg)
            if fg=='default':fg='#202938' if surface.theme=='light' else '#D8DEE9'
            if cell.char!=' ':d.text((x*cw,y*ch),cell.char,font=font,fill=fg,stroke_width=0)
    return out


def capture(root,out):
    out.mkdir(parents=True,exist_ok=True)
    c=Controller(root,Presentation());s=c.state;s.width=132;s.height=46
    def save(name,w=132,h=46,t=1.2):
        surface=render(s,w,h,t);raster(surface).save(out/(name+'.png'))
        (out/(name+'.txt')).write_text(surface.plain()+'\n')
    save('terminal-home')
    frames=[raster(render(s,112,38,i/12)) for i in range(48)]
    frames[0].save(out/'terminal-motion.gif',save_all=True,append_images=frames[1:],duration=83,loop=0,optimize=False)
    c.library();c.key(Key('char',' '));c.key(Key('down'));c.key(Key('char',' '));save('terminal-library')
    c.key(Key('char','i'));save('terminal-artwork')
    c.action('publish');save('terminal-publish')
    c.key(Key('down'));c.key(Key('enter'));save('terminal-field')
    c.key(Key('escape'));c.state.presentation.theme='light';save('terminal-light');save('terminal-compact',79,24)
    c.preferences();s.page.cursor=6;save('terminal-settings-compact',79,24)
    c.shutdown()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--create-demo',action='store_true');a=p.parse_args()
    if a.create_demo:make_art(a.root)
    capture(a.root,a.output)
