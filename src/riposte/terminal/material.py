"""COUNTERSTROKE: an authored ASCII lamellar surface and deflection trail.

Decorative motion is independent of engine progress. Layout labels never move.
The caller supplies time; a paused frame requires no timers, worker or randomness.
"""
from __future__ import annotations
import math
from .surface import Surface

LOGO = (
    "RRRR   III  PPPP    OOO   SSSS  TTTTT  EEEEE",
    "R   R   I   P   P  O   O  S       T    E    ",
    "RRRR    I   PPPP   O   O   SSS    T    EEEE ",
    "R  R    I   P      O   O      S   T    E    ",
    "R   R  III  P       OOO   SSSS    T    EEEEE",
)


def counterstroke(surface: Surface, x: int, y: int, width: int, height: int, time: float, active=False):
    """Depth-resolved hinged raster plates, with a travelling reflected stroke.

    Inverse affine rasterization gives each ASCII cell an exact plate coordinate;
    a per-cell depth buffer resolves overlapping sheets. The hinge, lattice and
    light move together, while every operational label stays stationary.
    """
    if width < 12 or height < 4: return
    depth = {}
    cycle = time * (1.0 if active else .65)
    for layer in range(3):
        angle = -.16 + .10 * math.sin(cycle*.7 + layer*.6)
        hinge = .24 * math.sin(cycle*.8 + layer*.45)
        # Projected unit axes in character cells; character aspect is deliberate.
        ax, ay = width*.48, height*(angle-.13)
        bx, by = -width*(.23+hinge*.12), height*(.34+hinge*.14)
        ox = x + width*.38 + layer*width*.025
        oy = y + height*.20 + layer*height*.18
        det = ax*by-ay*bx
        if abs(det) < .01: continue
        for row in range(max(0,y), min(surface.height,y+height)):
            for col in range(max(0,x), min(surface.width,x+width)):
                dx,dy=col+.5-ox,row+.5-oy
                u=(dx*by-dy*bx)/det;v=(dy*ax-dx*ay)/det
                if not (0<=u<=1 and 0<=v<=1):continue
                # A cut corner gives the lamella a deliberate silhouette.
                if u+v<.10 or u+v>1.90:continue
                z=layer*.5+v*.12
                if depth.get((col,row),-99)>z:continue
                depth[(col,row)]=z
                edge=min(u,1-u,v,1-v)
                light=.5+.5*math.cos(u*4+v*2-cycle*1.4+layer*.55)
                if edge<.055:glyph='/' if min(u,1-u)<.06 else '='
                elif (int(u*28)+int(v*14))%7==0:glyph='+'
                elif int(v*14)%3==0:glyph=':'
                else:glyph='.'
                fg='accent' if light>.86 else 'text' if edge<.055 and light>.5 else 'muted' if light>.5 else 'line'
                surface.put(col,row,glyph,fg,bold=edge<.055 and light>.86)
        corners=[(.10,0),(1,0),(1,.90),(.90,1),(0,1),(0,.10)]
        for i,(u,v) in enumerate(corners):
            u2,v2=corners[(i+1)%len(corners)]
            x1,y1=ox+ax*u+bx*v,oy+ay*u+by*v
            x2,y2=ox+ax*u2+bx*v2,oy+ay*u2+by*v2
            dx,dy=x2-x1,y2-y1
            steps=max(1,int(max(abs(dx),abs(dy))))
            glyph='-' if abs(dy)<abs(dx)*.3 else '/' if dx*dy<0 else '\\'
            for j in range(steps+1):
                col,row=round(x1+dx*j/steps),round(y1+dy*j/steps)
                if x<=col<x+width and y<=row<y+height:
                    surface.put(col,row,glyph,'muted' if layer<2 else 'accent')
    phase=(cycle*.65)%1
    px=x+int(width*phase)
    intercept=x+width*.34
    for tail in range(9):
        tx=px-tail
        ty=y+int(height*.65) if tx<intercept else y+int(height*.65-(tx-intercept)*height/width*.85)
        if x<=tx<x+width and y<=ty<y+height:
            surface.put(tx,ty,'>' if tail==0 else '-' if tx<intercept else '/', 'accent' if tail<4 else 'line',bold=tail==0)


def activity_trace(surface, x, y, width, time, state="RUNNING"):
    """A liveness ornament, deliberately not a percent-filled progress bar."""
    if width < 4: return
    surface.text(x, y, "." * width, "line")
    if state not in ("RUNNING", "CANCELLING"):
        surface.text(x, y, "+" + "-" * (width - 2) + "+", "accent" if state == "DONE" else "warn")
        return
    head = int(time * 15) % (width + 9)
    for t, glyph in enumerate(">=---...."):
        col = head - t
        if 0 <= col < width: surface.put(x + col, y, glyph, "accent" if t < 3 else "line")
