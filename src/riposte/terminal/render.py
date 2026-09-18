"""Task-composed deterministic Rich ASCII scenes, not seven identical cards."""
from __future__ import annotations
import json
import textwrap
from .surface import Surface, ascii_text
from .material import LOGO, counterstroke, activity_trace
from .state import Session, HOME
from .actions import BY_KEY, ACTIONS, command_line
from .preview import paint_preview
from .output import RECOVERY
from .interaction import hints, context, fields_for, GLOBAL
from .reports import overview, report_lines, paint_lines, Writer, label
from .. import __version__


def view_rows(state):
    page = state.page
    if page.name == "home":
        rows = [{"key": k, "title": title, "summary": summary} for k, title, summary in HOME]
    elif page.name == "workshop":
        rows = [{"key": a.key, "title": a.title, "summary": a.summary} for a in ACTIONS if a.section == "WORKSHOP"]
    else: rows = page.rows
    if page.query:
        word = page.query.lower()
        rows = [r for r in rows if word in " ".join(str(r.get(k, "")) for k in ("key", "title", "summary", "relative", "day", "id", "status", "review")).lower()]
    return rows


def shown(value):
    if isinstance(value, bool): return "ON" if value else "OFF"
    if value in (None, ""): return "not selected"
    if isinstance(value, (list, tuple)): return ", ".join(str(x) for x in value)
    return str(value)


def page_window(cursor, count, capacity):
    capacity = max(1, capacity)
    cursor = min(max(cursor, 0), max(0, count - 1))
    start = (cursor // capacity) * capacity
    return start, min(count, start + capacity)


def header(c, state):
    c.text(3, 1, "R I P O S T E", "accent", bold=True)
    c.text(20, 1, "/  " + state.page.title, "text", width=max(0, c.width - 47))
    if c.width >= 76: c.text(c.width - 24, 1, "LOCAL   /   v" + __version__, "muted")
    c.rule(3)
    caption = "Choose what you want to do. Each action works independently."
    if state.page.name != "home": caption = "MAIN MENU / " + state.page.title
    c.text(3, 4, caption, "muted", width=c.width-6)


def footer(c, state, keys=None):
    # All scenes use the same action grammar. Per-screen ad-hoc key strings are
    # intentionally ignored; hints() is also the contextual help source.
    c.rule(c.height - 4)
    controls=hints(state)
    if not any(h.key=="F1" for h in controls):controls=controls+[GLOBAL[0]]
    # Keep primary action and Help visible at the smallest supported size.
    compact=[controls[0]] if controls else []
    compact += [h for h in controls[1:] if h.key not in {"Left/Right","a","n","Up/Down"}]
    if not any(h.key=="F1" for h in compact):compact.append(GLOBAL[0])
    x,y=3,c.height-3; maxx=c.width-3
    deferred=[]
    for h in compact:
        token=f"[{h.key}] {h.label}"
        if x+len(token)>maxx:
            if y==c.height-3:x=3;y+=1
            else:deferred.append(h);continue
        # Leave space for Help on the second line.
        if y==c.height-2 and h.key!="F1" and x+len(token)+12>maxx:
            deferred.append(h);continue
        c.text(x,y,f"[{h.key}]","accent",bold=True)
        c.text(x+len(h.key)+3,y,h.label,"text")
        x+=len(token)+3
    if deferred and not any('F1' in ''.join(cell.char for cell in row) for row in c.cells[-3:]):
        c.text(c.width-13,c.height-2,"[F1] All keys","accent",bold=True)
    note=state.notice or context(state)
    if note:
        text=note if len(note)<=c.width-6 else note[:c.width-9].rstrip()+"..."
        c.text(3,c.height-5,text,"warn" if state.notice else "muted",width=c.width-6)

def home(c, state, time):
    rows = view_rows(state)
    roomy = c.height >= 32 and c.width >= 90
    top = 6
    if roomy:
        for dy, line in enumerate(LOGO): c.text(4, top + dy, line, "text", bold=True)
        counterstroke(c, c.width//2, top-1, c.width//2-4, 7, time)
        top += 7
    else:
        c.text(3, top, "IMAGE PROTECTION & ORGANIZATION", "text", bold=True)
        top += 2
    counts = "Choose an action, then browse images or folders."
    c.text(3, top, counts, "accent", width=c.width - 6)
    c.rule(top + 1, label="MAIN MENU" if not state.page.query_edit else "FIND AN ACTION")
    top += 2
    stride = 2 if c.height - top - 5 >= len(rows)*2 else 1
    deck_width = (c.width//2 + 5) if c.width >= 100 else c.width - 6
    capacity = max(1, (c.height - top - 5)//stride)
    start, end = page_window(state.page.cursor, len(rows), capacity)
    for n in range(start, end):
        y = top + (n-start)*stride
        selected = n == state.page.cursor
        if selected: c.fill(3, y, deck_width, stride, "raised")
        row = rows[n]
        marker = ">" if selected else " "
        c.text(4, y, f"{marker} {n+1}  {row['title']}", "accent" if selected else "text", bold=selected, width=deck_width - 2)
        if stride > 1: c.text(10, y+1, row["summary"], "muted", width=deck_width-8)
    if not rows: c.text(4, top, "No matching actions. Clear the search.", "warn")
    if rows and c.width >= 100:
        row = rows[min(state.page.cursor, len(rows)-1)]
        x, width = deck_width + 8, c.width - deck_width - 12
        c.text(x, top, "FOCUS / " + row["title"].upper(), "muted", width=width)
        action = BY_KEY.get(row["key"])
        c.wrap(x, top+2, action.summary if action else row["summary"], width, 4, "text")
        c.wrap(x, top+6, "No files change when you open an action.", width, 2)
    footer(c, state, "[1-7] choose   [Up/Down] focus   [Enter] open   [/] find   [q] quit")


def picker(c, state):
    p = state.page
    browser = p.result
    c.wrap(3, 6, p.values["purpose"], c.width-6, 3, "text")
    location = str(browser.directory)
    if len(location) > c.width-6: location = location[:3] + "..." + location[-(c.width-12):]
    c.text(3, 10, location, "accent", width=c.width-6)
    c.rule(11, label="LOCATIONS" if p.values.get("locations") else "FILES & FOLDERS" if browser.multiple else "FOLDERS")
    rows = view_rows(state)
    start, end = page_window(p.cursor, len(rows), c.height-18)
    for n in range(start, end):
        row = rows[n]; y = 12+n-start
        focused = n == p.cursor
        if focused: c.fill(3, y, c.width-6, 1, "raised")
        mark = "[x] " if row.get("selected") else "[ ] " if browser.multiple and row["kind"] in {"file", "directory"} else "    "
        suffix = "/" if row["kind"] == "directory" else ""
        c.text(3, y, f"{'>' if focused else ' '} {n+1:2} {mark}{row['title']}{suffix}", "accent" if focused else "text", bold=focused, width=c.width-6)
    c.text(3, c.height-6, f"{len(browser.selected)} selected   |   Rows {start+1}-{end}/{len(rows)}", "muted", width=c.width-6)
    footer(c, state)


def collection(c, state):
    rows = view_rows(state)
    c.text(3, 6, f"CLEAN LIBRARY / {len(rows)} visible / {len(state.selected)} selected", "accent", bold=True, width=c.width-6)
    c.text(3, 8, "     DATE         SIZE       PIXELS       CANONICAL FILE", "muted", width=c.width-6)
    c.rule(9)
    capacity = c.height - 16
    start, end = page_window(state.page.cursor, len(rows), capacity)
    for n in range(start, end):
        row = rows[n]; y = 10 + n-start; chosen = row["id"] in state.selected
        if n == state.page.cursor: c.fill(3, y, c.width-6, 1, "raised")
        parts = row["relative"].split("/")
        head = f"{'>' if n==state.page.cursor else ' '} {'[x]' if chosen else '[ ]'} {row['day']}   {parts[2]:3}  {row['width']:5}x{row['height']:<5}  "
        name = row["relative"] if c.width >= 120 else parts[-1] + "  " + row["id"][:12]
        c.text(3, y, head + name, "accent" if chosen or n==state.page.cursor else "text", bold=n==state.page.cursor, width=c.width-6)
    if not rows:
        c.wrap(4, 12, "No matching clean images. Clean & organize imports your existing image into the calendar hierarchy.", c.width-8, 3)
    if rows:
        row = rows[min(state.page.cursor, len(rows)-1)]
        c.text(3, c.height-6, f"ID {row['id']}  |  rows {start+1}-{end}/{len(rows)}", "muted", width=c.width-6)
    footer(c, state, "[Space] select   [a] all visible   [n] clear   [Enter] inspect   [p] protect   [/] find")


def asset(c, state):
    p = state.page
    c.text(3, 6, "CLEAN MASTER / " + (p.report.get("relative", "")), "accent", bold=True, width=c.width-6)
    side = 33 if c.width >= 100 else 0
    x, y, width, height = 3, 8, c.width-6-side, c.height-15
    c.frame(x, y, width, height, "ASCII COMPOSITION PREVIEW")
    if p.preview: paint_preview(c, p.preview, x+1, y+1, width-2, height-2)
    if side:
        dx = c.width-side+1
        for n, (label, value) in enumerate((("DATE", p.report.get("day")), ("DIMENSIONS", f"{p.report.get('width')} x {p.report.get('height')}"),
                                           ("METADATA", "DATE ONLY"), ("SELECTED", "YES" if p.image_id in state.selected else "NO"))):
            c.text(dx, 9+n*3, label, "muted"); c.text(dx,10+n*3, shown(value), "text", width=side-4)
        c.wrap(dx, 23, "[v] opens the audited image in your local image viewer.", side-4, 3)
    footer(c, state, "[Enter] select   [v] actual image   [p] protect selection   [Esc] library")


def form(c, state):
    p = state.page; action = BY_KEY[p.action]
    fields = fields_for(p)
    c.text(3, 6, action.title.upper(), "accent", bold=True)
    sub = (f"{len(state.selected)} selected images / clean masters unchanged" if p.action == "publish"
           else "Files and folders / originals stay in place" if p.action == "riposte"
           else "Entire workspace / preview, REPLACE, then protection" if p.action == "sort-riposte"
           else action.effect.replace("_", " "))
    c.text(3, 7, sub, "muted", width=c.width-6)
    if state.root: c.text(3, 8, ("Results: " if p.action == "riposte" else "Folder: ") + str(state.root), "muted", width=c.width-6)
    c.rule(9)
    side = max(28, c.width//3) if c.width >= 100 else 0
    left = c.width - side - 6
    count = len(fields)+1
    capacity = c.height-16
    start, end = page_window(p.cursor, count, capacity)
    label_width = 25 if left >= 60 else max(16, left//2)
    for n in range(start, end):
        y = 10+n-start; selected = n==p.cursor
        if selected: c.fill(3,y,left,1,"raised")
        if n == len(fields):
            label = "PREVIEW BATCH" if p.action in {'publish','riposte'} else "PREVIEW SORT" if p.action=='organize' else "PREVIEW BOTH STAGES" if p.action=='sort-riposte' else "RUN ACTION"
            c.text(4,y,">> " + label,"accent",bold=True,width=left-2)
            continue
        f = fields[n]; value=shown(p.values.get(f.key,f.default))
        if f.key == "input1" and p.values.get("input_paths"): value = f"{len(p.values['input_paths'])} selected - Enter to browse"
        if f.kind=='bool': value='[x] ON' if p.values.get(f.key,f.default) else '[ ] OFF'
        c.text(4,y,('> ' if selected else '  ')+f.label,"text",bold=selected,width=label_width)
        c.text(5+label_width,y,value,"accent" if selected else "muted",width=max(0,left-label_width-3))
    if side:
        x=c.width-side+1; width=side-5
        c.text(x,10,"FIELD / CONTEXT","muted")
        if p.cursor < len(fields):
            f=fields[p.cursor]
            c.text(x,12,f.label.upper(),"text",bold=True,width=width)
            used=c.wrap(x,14,f.help,width,5)
            if f.choices: c.wrap(x,15+used," / ".join(f.choices),width,3,"accent")
            elif f.minimum is not None: c.text(x,15+used,f"{f.minimum:g} .. {f.maximum:g}","accent",width=width)
            c.wrap(x,22,"Local paths remain in memory only." if f.kind=="path" else "Changing a setting does not start processing. Preview uses the current values.",width,3)
        else:
            c.wrap(x,12,action.summary,width,5,"text")
            c.wrap(x,19,"The next action uses these settings. F4 shows its direct Typer command.",width,4)
    c.text(3,c.height-6,f"SETTING {min(p.cursor+1,count)}/{count}   |   " + ("ALL SETTINGS" if p.advanced else "ESSENTIAL SETTINGS" if p.action in {"publish", "riposte", "sort-riposte"} else "ACTION SETTINGS"), "muted",width=c.width-6)
    footer(c,state,"[Enter] edit / preview   [p] preview   [v] audit workspace   [Esc] back" if p.action=="organize" else "[Enter] edit / continue   [p] preview   [r] run   [Esc] back")


def batches(c,state):
    rows=view_rows(state); batch = state.page.name=='batch'
    c.text(3,6,("OUTPUTS / " + (state.page.batch_id or "")) if batch else f"PUBLISHING BATCHES / {len(rows)}", "accent",bold=True,width=c.width-6)
    c.text(3,8,"   OUTPUT         DIMENSIONS     STATE                  REVIEW" if batch else "   BATCH   STATE                  READY  APPROVED  BLOCKED   ID", "muted",width=c.width-6)
    c.rule(9)
    capacity=c.height-16;start,end=page_window(state.page.cursor,len(rows),capacity)
    for n in range(start,end):
        row=rows[n];y=10+n-start
        if n==state.page.cursor:c.fill(3,y,c.width-6,1,"raised")
        if batch:
            dims=f"{row.get('width','-')}x{row.get('height','-')}"
            text=f"{'>' if n==state.page.cursor else ' '}  {row['id'][:10]}   {dims:14} {row['status']:22} {row['review']}"
        else:
            counts=row.get('counts',{})
            text=f"{'>' if n==state.page.cursor else ' '}  {row['sequence']:05d}   {row['status']:22} {counts.get('READY_FOR_REVIEW',0):5}  {counts.get('ACCEPTED',0):8} {counts.get('BLOCKED',0):8}   {row['id'][:12]}"
        c.text(3,y,text,"warn" if row.get('status')=='BLOCKED' else "text",bold=n==state.page.cursor,width=c.width-6)
    if not rows:c.wrap(4,12,"No publishing records yet. Protect & publish creates independently sized candidates from selected cleaned image.",c.width-8,3)
    footer(c,state,"[Enter] review output   [p] package approved   [r] resume   [Esc] batches" if batch else "[Enter] open batch   [/] find   [Esc] home")


def item(c,state):
    p=state.page
    c.text(3,6,f"OUTPUT / {p.item_id}","accent",bold=True,width=c.width-6)
    c.text(3,7,f"{p.kind.upper()}  /  {p.view}  /  review {p.report.get('review','PENDING')}","text",width=c.width-6)
    side=36 if c.width>=105 else 0
    width=c.width-6-side;height=c.height-16
    c.frame(3,9,width,height,"ASCII PREVIEW / NOT PIXEL REVIEW")
    if p.preview:paint_preview(c,p.preview,4,10,width-2,height-2)
    if side:
        x=c.width-side+1;quality=p.report.get('quality',{})
        c.text(x,10,"EXACT OUTPUT", "muted")
        for n,(label,value) in enumerate((("Dimensions",f"{p.report.get('width')} x {p.report.get('height')}"),
              ("Budget violations",quality.get('budget_violating_pixels','-')),("Worst tile RMS",quality.get('worst_tile_rmse_255','-')),
              ("Delta E76 p95",quality.get('delta_e76_p95','-')),("AI evidence","UNVERIFIED"))):
            c.text(x,12+n*2,label,"muted",width=side-4);c.text(x,13+n*2,shown(value),"warn" if label=='AI evidence' else "text",width=side-4)
        c.wrap(x,24,"[v] actual pixels in a local viewer. Approval is bound to these bytes.",side-4,4)
    footer(c,state,"[c/b/d] view   [t] transport   [v] actual PNG   [a] accept   [x] reject   [w] helper")


def workshop(c,state):
    rows=view_rows(state)
    c.text(3,6,"WORKSHOP / OPTIONAL HELPERS", "accent",bold=True)
    c.text(3,7,"Publishing does not require these tools.","muted")
    c.rule(9)
    capacity=c.height-16;start,end=page_window(state.page.cursor,len(rows),capacity)
    for n in range(start,end):
        y=10+n-start;row=rows[n]
        if n==state.page.cursor:c.fill(3,y,c.width-6,1,"raised")
        c.text(4,y,f"{'>' if n==state.page.cursor else ' '} {n+1:02d}  {row['title']}","accent" if n==state.page.cursor else "text",width=37)
        if c.width>=90:c.text(43,y,row['summary'],"muted",width=c.width-47)
    footer(c,state,"[Up/Down] choose   [Enter] configure   [/] find   [Esc] home")


def _report_data(state, actual_width=None):
    p=state.page
    command=p.request.name if p.request else ""
    width=max(12,(actual_width or state.width)-8)
    key=(id(p.result),command,width,p.report_view)
    if key not in p.display_cache:
        report=overview(p.result,command,width)
        p.display_cache.clear()
        p.display_cache[key]=(report,report_lines(report,p.result,p.report_view,width))
    return p.display_cache[key]


def _help_lines(state, actual_width=None):
    value=state.page.result or {"screen":"RIPOSTE", "context":"Enter activates the focused action; Esc returns.",
                              "controls":[{"key":h.key,"label":h.label,"explanation":h.explanation} for h in GLOBAL]}
    w=Writer(max(12,(actual_width or state.width)-8))
    if value.get("context"):w.text(value["context"]);w.blank()
    for entry in value.get("controls",[]):
        w.pair("["+entry["key"]+"]",entry["label"])
        w.text("  "+entry["explanation"],"muted");w.blank()
    return w.lines


def scroll_limit(state):
    p=state.page
    if p.name=="help":return max(0,len(_help_lines(state))-max(1,state.height-15))
    if p.name=="command":
        return max(0,len(textwrap.wrap(command_line(p.request),max(12,state.width-6)))-max(1,state.height-19)) if p.request else 0
    if p.name!="result" or p.code:return 0
    return max(0,len(_report_data(state)[1])-max(1,state.height-(10 if state.height<30 else 14)-6))

def result(c,state):
    p=state.page
    if p.code:
        c.text(3,6,"[STOPPED]  OPERATION NEEDS ATTENTION","danger",bold=True)
        c.wrap(3,8,label(p.code),c.width-6,3,"text",bold=True)
        c.rule(11,label="NEXT ACTION")
        c.wrap(3,13,RECOVERY.get(p.code,"No raw backend error or personal path was printed. Review the settings and retry the action."),c.width-6,max(2,c.height-21),"text")
        c.text(3,c.height-6,"CODE / "+p.code,"code",width=c.width-6)
        footer(c,state);return
    report,lines=_report_data(state,c.width)
    c.text(3,6,report.title.upper(),"text",bold=True,width=c.width-6)
    compact=c.height<30
    if compact:
        badge="["+report.outcome+"]"
        if len(report.title)+len(badge)<c.width-10:c.text(c.width-len(badge)-3,6,badge,report.tone,bold=True)
        else:c.text(3,7,badge,report.tone,bold=True,width=c.width-6)
    else:
        c.text(3,7,"["+report.outcome+"]",report.tone,bold=True,width=c.width-6)
        c.wrap(3,9,report.explanation,c.width-6,2,"muted")
    tab_y=8 if compact else 12
    body_y=10 if compact else 14
    x=3
    for value,title in (("overview","Overview"),("details","Details"),("json","JSON")):
        selected=value==p.report_view
        text=("> " if selected else "  ")+title
        c.text(x,tab_y,text,"accent" if selected else "muted",bold=selected)
        if selected:c.text(x,tab_y+1,"-"*len(text),"accent")
        x+=len(title)+7
    capacity=max(1,c.height-body_y-6)
    start,end=paint_lines(c,lines,4,body_y,c.width-8,capacity,p.scroll)
    c.text(3,c.height-6,f"{p.report_view.upper()} / lines {start+1 if lines else 0}-{end} of {len(lines)}","muted",width=c.width-6)
    footer(c,state)

def job(c,state,time):
    op=state.operation;s=op.snapshot()
    c.text(3,6,"RUNNING / "+op.request.name.upper(),"accent",bold=True)
    c.text(3,9,s.phase,"text",bold=True,width=c.width-6)
    if s.item:c.text(3,11,f"PUBLISHING OUTPUT {s.item}/{s.items}","muted")
    text=f"ENGINE POSITION   {s.processed} / {s.total}" if s.processed is not None and s.total else f"ITEMS INSPECTED   {s.processed}" if s.processed is not None else "ENGINE COUNT      not reported yet"
    c.text(3,13,text,"accent",width=c.width-6)
    c.text(3,14 if c.height < 30 else 15,f"ELAPSED           {s.elapsed:0.1f}s", "muted")
    if c.width>=104 and c.height>=30:counterstroke(c,c.width//2,8,c.width//2-4,12,time,active=True)
    line_y=min(19,c.height-8)
    activity_trace(c,3,line_y,c.width-6,time,s.state)
    c.text(3,line_y+1,"ACTIVITY TRACE / engine counts are reported separately above", "muted",width=c.width-6)
    event_count=max(0,c.height-line_y-9)
    for n,event in enumerate(s.events[-event_count:] if event_count else ()):c.text(4,line_y+3+n,". "+event,"muted",width=c.width-8)
    if s.cancel_requested:state_label="Stop requested / waiting for an engine checkpoint"
    elif not s.cancellable:state_label="Source/record commit / exit waits for completion"
    else:state_label="[Esc or Ctrl+C] request checkpoint stop"
    footer(c,state,state_label)


def preferences(c,state):
    rows=state.page.rows
    c.text(3,6,"TERMINAL & WORKSPACE", "accent",bold=True)
    c.text(3,7,"Appearance and local paths are session-only.","muted")
    c.rule(9)
    stride=2 if c.height >= 32 else 1
    start,end=page_window(state.page.cursor,len(rows),max(1,(c.height-16)//stride))
    for n in range(start,end):
        row=rows[n];y=10+(n-start)*stride
        if n==state.page.cursor:c.fill(3,y,c.width-6,1,"raised")
        c.text(4,y,('> ' if n==state.page.cursor else '  ')+row['title'],"text",bold=n==state.page.cursor,width=30)
        value=row.get('value','')
        c.text(37,y,value,"accent",width=c.width-41)
    footer(c,state,"[Enter] change   [Esc] home")


def help_page(c,state):
    title=(state.page.result or {}).get("screen","KEY MAP")
    c.text(3,6,"HELP / "+title,"accent",bold=True,width=c.width-6)
    c.text(3,7,"Controls are contextual. Enter activates the focused action.","muted",width=c.width-6)
    paint_lines(c,_help_lines(state,c.width),3,9,c.width-6,max(1,c.height-15),state.page.scroll)
    footer(c,state)

def command_page(c,state):
    c.text(3,6,"DIRECT COMMAND / INSPECT ONLY", "accent",bold=True)
    request=state.page.request
    if request:
        text=command_line(request)
        lines=textwrap.wrap(text,max(12,c.width-6))
        for i,line in enumerate(lines[state.page.scroll:state.page.scroll+max(1,c.height-19)]):c.text(3,9+i,line,"text",width=c.width-6)
    else:c.wrap(3,9,"Choose an operation first. Typer's --help lists all direct commands.",c.width-6,4)
    c.wrap(3,c.height-9,"Local path values are displayed only in this session. No history file, shell evaluation or clipboard write occurs.",c.width-6,3)
    footer(c,state,"[Up/Down] read command   [Esc] return   Nothing is executed")


def confirm(c,state):
    p=state.page
    c.text(3,6,"EXPLICIT WRITE BOUNDARY", "warn",bold=True)
    c.wrap(3,8,p.title,c.width-6,3,"text",bold=True)
    if p.confirm_word=='REPLACE':
        c.wrap(3,11,"Verified sources and authorized metadata sidecars are REMOVED. No raw backup or Trash copy. Failed inputs remain as blockers.",c.width-6,max(2,c.height-21),"warn")
    c.text(3,c.height-8,"TYPE "+p.confirm_word+" TO CONTINUE", "accent",bold=True)
    c.text(3,c.height-6,"> "+p.values.get('confirmation',''),"text",width=c.width-6)
    footer(c,state,"[Enter] confirm exact word   [Esc] cancel")


def editor_overlay(c,state):
    e=state.editor
    w=min(c.width-4,104);h=min(13,c.height-4);x=(c.width-w)//2;y=(c.height-h)//2
    c.frame(x,y,w,h,"EDIT / "+e.field.label.upper(),"panel","accent")
    c.wrap(x+3,y+2,e.field.help,w-6,3,"muted")
    available=w-8;start=max(0,e.position-available+1)
    visible=e.value[start:start+available]
    c.fill(x+3,y+6,w-6,1,"raised")
    c.text(x+4,y+6,visible,"text",width=available)
    cursor=e.position-start
    if 0<=cursor<available:
        char=e.value[e.position] if e.position<len(e.value) else ' '
        c.put(x+4+cursor,y+6,char,"accent",bold=True)
        c.put(x+4+cursor,y+7,"^","accent",bold=True)
    c.text(x+3,y+8,"Invalid value. Correct this field." if e.error else "[Enter] save   [Esc] discard   [Ctrl+U] clear", "danger" if e.error else "muted",width=w-6)


def render(state:Session,width:int,height:int,time:float=0)->Surface:
    c=Surface(width,height,state.presentation.theme)
    if c.width<72 or c.height<24:
        c.text(1,1,"RIPOSTE / compact terminal", "accent",bold=True)
        c.wrap(1,3,"Increase to at least 72 columns x 24 rows, or use ui --linear. q still exits.",c.width-2,c.height-6)
        return c
    header(c,state)
    page=state.page.name
    renderers={'home':lambda:home(c,state,time),'library':lambda:collection(c,state),'asset':lambda:asset(c,state),
               'form':lambda:form(c,state),'batches':lambda:batches(c,state),'batch':lambda:batches(c,state),
               'item':lambda:item(c,state),'workshop':lambda:workshop(c,state),'result':lambda:result(c,state),
               'job':lambda:job(c,state,time),'preferences':lambda:preferences(c,state),'help':lambda:help_page(c,state),
               'command':lambda:command_page(c,state),'confirm':lambda:confirm(c,state),'picker':lambda:picker(c,state)}
    renderers.get(page,lambda:home(c,state,time))()
    if state.page.query_edit:
        c.fill(3,c.height-5,c.width-6,1,"raised")
        c.text(3,c.height-5,"FIND / "+state.page.query+"_","accent",width=c.width-6)
    if state.editor:editor_overlay(c,state)
    return c
