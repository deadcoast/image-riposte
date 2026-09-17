"""Capture live 0.5 report compositions from synthetic, non-personal artwork."""
import json
from pathlib import Path
from capture_terminal import make_art, raster
from riposte.terminal.controller import Controller
from riposte.terminal.output import Presentation
from riposte.terminal.state import Page
from riposte.terminal.service import Request, execute
from riposte.terminal.render import render
from riposte.terminal.keyboard import Key


def capture(root, output):
    output.mkdir(parents=True,exist_ok=True)
    controller=Controller(root,Presentation());state=controller.state
    state.width=112;state.height=38
    def save(name, width=112,height=38,transparent=False):
        state.width=width;state.height=height
        surface=render(state,width,height,1.5)
        raster(surface,background="#f5f3ee" if state.presentation.theme=="light" else "#171B22",transparent=transparent).save(output/(name+".png"))
        (output/(name+".txt")).write_text(surface.plain()+"\n")
    save("terminal-home-goks")
    frames=[raster(render(state,112,38,i/12)) for i in range(36)]
    frames[0].save(output/"terminal-motion-goks.gif",save_all=True,append_images=frames[1:],duration=83,loop=0,optimize=False)
    controller.library();controller.key(Key("enter"));save("terminal-library-goks")
    controller.key(Key("char","i"));save("terminal-artwork-goks")
    controller.action("publish");save("terminal-publish-goks")
    request=controller.request_from_form();request=Request("plan",request.root,request.values)
    data=execute(request)
    controller.show(Page("result","PUBLISHING PLAN",result=data,request=request))
    save("terminal-report-overview")
    save("terminal-report-transparent",transparent=True)
    save("terminal-report-compact",79,24)
    controller.key(Key("char","t"));save("terminal-report-details")
    controller.key(Key("char","t"));save("terminal-report-json")
    controller.key(Key("char","t"));state.presentation.theme="light";save("terminal-report-light")
    state.presentation.theme="goks"
    request=Request("audit",root);controller.show(Page("result","WORKSPACE AUDIT",result=execute(request),request=request));save("terminal-audit-goks")
    request=Request("doctor");controller.show(Page("result","LOCAL RUNTIME",result=execute(request),request=request));save("terminal-runtime-goks")
    controller.shutdown()
    (output/"captures.json").write_text(json.dumps({"source":"actual production ASCII renderer", "artwork":"synthetic developer fixtures", "transparent_png":"terminal-report-transparent.png", "host_backgrounds":"capture-only; not runtime palette fills", "pretrained_efficacy":False},indent=2)+"\n")

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args();capture(args.root,args.output)
