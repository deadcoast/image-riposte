"""Native Rich ASCII interface with a fully functional line-input alternative."""
from __future__ import annotations
import os
from pathlib import Path
import signal
import sys
import time
from rich.live import Live
from rich.text import Text
from .controller import Controller
from .keyboard import Key, TerminalKeys
from .render import render, view_rows
from .interaction import fields_for
from .output import Presentation, error
from ..errors import RiposteError
from .signals import termination_guard, TerminationRequested


def _line_command(controller: Controller, line: str):
    state = controller.state
    if state.editor:
        if line == "/cancel": controller.key(Key("escape")); return
        state.editor.value = line[:4096]; state.editor.position = len(state.editor.value)
        controller.key(Key("enter")); return
    if state.page.name == "confirm":
        if line == "/cancel": controller.key(Key("escape")); return
        state.page.values["confirmation"] = line
        controller.key(Key("enter")); return
    head, _, rest = line.partition(" ")
    if head == "search": state.page.query=rest;state.page.cursor=0;return
    if head == "focus":
        try:
            rows = fields_for(state.page) if state.page.name == "form" else view_rows(state)
            state.page.cursor=max(0,min(len(rows)-1,int(rest)-1))
        except ValueError: state.notice="Use focus followed by a row number."
        return
    if head == "edit" and state.page.name == "form":
        number, _, value = rest.partition(" ")
        from .actions import BY_KEY, parse_value
        try:
            fields=fields_for(state.page);index=int(number)-1
            if not 0<=index<len(fields): raise ValueError
            f=fields[index]
            state.page.values[f.key]=parse_value(f,value);state.page.cursor=index
            if f.key.startswith("input"): state.page.values.pop("input_paths", None)
        except (ValueError,RiposteError): state.notice="Invalid field number or value. No operation started."
        return
    if head == "select" and state.page.name == "library":
        rows=view_rows(state)
        try:
            indices=[int(x.strip())-1 for x in rest.split(',')]
            if any(i<0 or i>=len(rows) for i in indices): raise ValueError
            for i in indices:controller.toggle_selection(rows[i])
        except ValueError:state.notice="Use select 1,3,5 with visible row numbers."
        return
    if head.isdigit() and state.page.name=="picker":
        index=int(head)-1
        if 0<=index<len(view_rows(state)):
            state.page.cursor=index;controller.key(Key("enter"))
        return
    mapping={"":"enter","enter":"enter","open":"enter","back":"escape","parent":"backspace","up":"up","down":"down","pgup":"pageup","pgdn":"pagedown","home":"home","end":"end","help":"f1","motion":"f2","theme":"f3","command":"f4","toggle":"char"}
    if head in mapping:controller.key(Key(mapping[head]," " if head=="toggle" else ""))
    elif head == "inspect" and state.page.name == "library":controller.key(Key("char","i"))
    elif head == "details" and state.page.name == "result":controller.key(Key("char","t"))
    elif head == "advanced" and state.page.name == "form":controller.key(Key("char","f"))
    elif head in {"plan","run","apply","accept","reject","audit"}:controller.key(Key("char",{"plan":"p","run":"r","apply":"a","accept":"a","reject":"x","audit":"v"}[head]))
    elif len(line)==1:controller.key(Key("char",line))
    else:state.notice="Use a visible key, focus N, select 1,3, edit N VALUE, search TEXT, or help."


def linear_session(controller, input_stream=None, output_stream=None):
    """Same controller/actions. No raw mode, live cursor controls, or fake prompts."""
    input_stream=input_stream or sys.stdin
    output_stream=output_stream or sys.stdout
    state=controller.state
    state.presentation.no_animation=True;state.paused=True
    output_stream.write("RIPOSTE / LINEAR ASCII\nUse visible keys; edit N VALUE; select 1,3; focus N; /cancel discards an edit.\n")
    while state.running:
        controller.pump()
        if state.operation:
            last=None
            while state.operation and not state.operation.done.is_set():
                try:
                    snapshot=state.operation.snapshot()
                    message=snapshot.phase
                    if message!=last:
                        output_stream.write("  "+message+"\n");output_stream.flush();last=message
                    state.operation.done.wait(.1)
                except KeyboardInterrupt:controller.key(Key("interrupt"))
            controller.pump()
            continue
        # A stable transcript, not an animated stream and not ANSI-decorated JSON.
        state.width=max(60,min(100,state.width));state.height=max(26,min(40,state.height))
        output_stream.write(render(state,state.width,state.height,0).plain()+"\n")
        output_stream.write("value (/cancel)> " if state.editor else "confirm (/cancel)> " if state.page.name=="confirm" else "riposte> ")
        output_stream.flush()
        try:line=input_stream.readline()
        except KeyboardInterrupt:controller.key(Key("interrupt"));continue
        if not line:controller.key(Key("eof"));break
        _line_command(controller,line.rstrip("\r\n"))


def launch(root:Path|None,presentation:Presentation,*,linear=False,initial="home") -> int:
    with termination_guard():
        return _launch(root,presentation,linear=linear,initial=initial)


def _launch(root:Path|None,presentation:Presentation,*,linear=False,initial="home") -> int:
    if not linear and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        error("INTERACTIVE_REQUIRES_TTY",presentation);return 2
    try:controller=Controller(root,presentation,initial=initial)
    except RiposteError as exc:error(exc.code,presentation);return 2
    state=controller.state
    if os.environ.get("TERM")=="dumb":linear=True
    code=0
    try:
        if linear:linear_session(controller)
        else:
            console=presentation.console()
            # Keyboard acquisition is foreground-only. Rich's alternate screen
            # and cursor restoration exit before browser or OS shell handoffs.
            with TerminalKeys(output=console.file) as keyboard:
                with Live(console=console,screen=True,auto_refresh=False,redirect_stdout=False,redirect_stderr=False,vertical_overflow="crop") as live:
                    while state.running:
                        try:
                            controller.pump()
                            state.width=console.size.width;state.height=console.size.height
                            elapsed=time.monotonic()-controller.started
                            motion_time=state.frozen_time if state.paused else elapsed
                            live.update(render(state,state.width,state.height,motion_time),refresh=True)
                            key=keyboard.read(1/max(4,presentation.fps))
                            if key:controller.key(key)
                        except KeyboardInterrupt:controller.key(Key("interrupt"))
    except TerminationRequested:
        state.handoff=None;state.switch_linear=False;code=143
    except RiposteError as exc:error(exc.code,presentation);code=2
    except Exception:error("TERMINAL_OPERATION_FAILED",presentation);code=2
    finally:
        controller.shutdown()
    if state.switch_linear:
        state.running=True;state.switch_linear=False
        state.presentation.plain=True
        try:linear_session(controller)
        finally:controller.shutdown()
    if state.handoff:
        from ..cli import main
        return main(state.handoff)
    if not presentation.machine:
        console=presentation.console()
        console.print(Text("  RIPOSTE / terminal released. No unfinished worker was abandoned."))
    return code
