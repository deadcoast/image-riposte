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
    if c.width >= 76: c.text(c.width - 24, 1, "LOCAL   /   v0.4.0", "muted")
    c.rule(3)
    current = {"library":0,"asset":0,"form":2,"batch":3,"item":3,"batches":3}.get(state.page.name)
    if state.page.action == "organize": current = 1
    labels = ("SELECT", "CLEAN", "PROTECT", "REVIEW", "PUBLISH")
    step = max(8, (c.width - 7) // 5)
    for n, label in enumerate(labels):
        text = f"{n+1:02d} {label}"
        c.text(3 + n*step, 4, text, "accent" if current == n else "muted", bold=current == n, width=step - 1)


def footer(c, state, keys="[Enter] open   [Esc] back   [/] find"):
    c.rule(c.height - 4)
    c.text(3, c.height - 3, keys, "text", width=c.width - 6)
    global_keys = "[F1] keys  [F2] motion " + ("OFF" if state.paused or state.presentation.no_animation else "ON") + "  [F3] palette  [F4] command"
    if c.width < 84: global_keys = "F1 help | F2 motion | F3 palette | F4 command"
    c.text(3, c.height - 2, global_keys, "muted", width=c.width - 6)
    if state.notice:
        c.text(3, c.height - 5, state.notice, "warn", width=c.width - 6)


def home(c, state, time):
    rows = view_rows(state)
    roomy = c.height >= 32 and c.width >= 90
    top = 6
    if roomy:
        for dy, line in enumerate(LOGO): c.text(4, top + dy, line, "text", bold=True)
        c.text(4, top + 6, "YOUR ART. YOUR COUNTERMOVE.", "muted")
        counterstroke(c, c.width//2, top-1, c.width//2-4, 11, time)
        top += 10
    else:
        c.text(3, top, "YOUR ART. YOUR COUNTERMOVE.", "text", bold=True)
        top += 2
    counts = f"{len(state.catalog):02d} CLEAN IMAGES   /   {len(state.selected):02d} SELECTED   /   {len(state.batches):02d} BATCHES"
    c.text(3, top, counts, "accent", width=c.width - 6)
    c.rule(top + 2, label="ACTION DECK" if not state.page.query_edit else "FIND AN ACTION")
    top += 4
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
        effect = action.effect if action else "INSPECT / SELECT"
        c.text(x, top+7, effect.replace("_", " "), "accent", bold=True, width=width)
        note = "Master images stay unchanged." if row['key'] == 'publish' else "Writes require an explicit action."
        c.wrap(x, top+9, note, width, 2)
        c.text(x, top+12, "[Enter] continue", "text", width=width)
    footer(c, state, "[1-7] choose   [Up/Down] focus   [Enter] open   [/] find   [q] quit")


def collection(c, state):
    rows = view_rows(state)
    c.text(3, 6, f"CLEAN LIBRARY / {len(rows)} visible / {len(state.selected)} selected", "accent", bold=True, width=c.width-6)
    c.text(3, 8, "   DATE         SIZE       PIXELS       CANONICAL FILE", "muted", width=c.width-6)
    c.rule(9)
    capacity = c.height - 16
    start, end = page_window(state.page.cursor, len(rows), capacity)
    for n in range(start, end):
        row = rows[n]; y = 10 + n-start; chosen = row["id"] in state.selected
        if n == state.page.cursor: c.fill(3, y, c.width-6, 1, "raised")
        parts = row["relative"].split("/")
        head = f"{'[x]' if chosen else '[ ]'} {row['day']}   {parts[2]:3}  {row['width']:5}x{row['height']:<5}  "
        name = row["relative"] if c.width >= 120 else parts[-1] + "  " + row["id"][:12]
        c.text(3, y, head + name, "accent" if chosen else "text", bold=n==state.page.cursor, width=c.width-6)
    if not rows:
        c.wrap(4, 12, "No matching clean images. Clean & organize imports your existing artwork into the calendar hierarchy.", c.width-8, 3)
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
    footer(c, state, "[Space] select   [v] actual image   [p] protect selection   [Esc] library")


def form(c, state):
    p = state.page; action = BY_KEY[p.action]
    fields = action.fields
    c.text(3, 6, action.title.upper(), "accent", bold=True)
    sub = f"{len(state.selected)} selected images / clean masters unchanged" if p.action == "publish" else action.effect.replace("_", " ")
    c.text(3, 7, sub, "muted", width=c.width-6)
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
            label = "PREVIEW BATCH" if p.action=='publish' else "PREVIEW MIGRATION" if p.action=='organize' else "RUN ACTION"
            c.text(4,y,">> " + label,"accent",bold=True,width=left-2)
            continue
        f = fields[n]; value=shown(p.values.get(f.key,f.default))
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
            c.wrap(x,22,"Path values stay in this process; no saved model-path history.",width,3)
        else:
            c.wrap(x,12,action.summary,width,5,"text")
            c.wrap(x,19,"The next action uses these settings. F4 shows its direct Typer command.",width,4)
    c.text(3,c.height-6,f"FIELD {min(p.cursor+1,count)}/{count}   |   Enter edits; Space toggles; Left/Right cycles choices", "muted",width=c.width-6)
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
    if not rows:c.wrap(4,12,"No publishing records yet. Protect & publish creates independently sized candidates from selected cleaned artwork.",c.width-8,3)
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
              ("Pixel budget",quality.get('budget_violating_pixels','-')),("Worst tile RMS",quality.get('worst_tile_rmse_255','-')),
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


def scroll_limit(state):
    p=state.page
    if p.name=="help": return max(0,12-max(1,state.height-15))
    if p.name=="command":
        return max(0,len(textwrap.wrap(command_line(p.request),max(12,state.width-6)))-max(1,state.height-19)) if p.request else 0
    if p.name!="result" or p.code: return 0
    raw=json.dumps(p.result,indent=2,ensure_ascii=True,allow_nan=False).splitlines()
    lines=sum(max(1,len(textwrap.wrap(line,max(12,state.width-10),replace_whitespace=False,drop_whitespace=False))) for line in raw)
    y=14 if isinstance(p.result,dict) and p.result.get("mode") in ("READ_ONLY","APPLY","PUBLICATION_PLAN") else 8
    return max(0,lines-max(1,state.height-y-6))


def result(c,state):
    p=state.page
    if p.code:
        c.text(3,6,"OPERATION STOPPED", "danger",bold=True)
        c.text(3,8,p.code,"warn",bold=True,width=c.width-6)
        c.wrap(3,10,RECOVERY.get(p.code,"No raw backend error, local path or metadata dump was printed."),c.width-6,4)
        if state.operation_request and state.operation_request.name in ('publish','resume'):
            c.wrap(3,15,"Committed output files remain available in Publishing batches.",c.width-6,3)
        footer(c,state,"[Esc] back   [b] publishing batches   [F4] direct command")
        return
    c.text(3,6,p.title, "accent",bold=True,width=c.width-6)
    values=p.result
    if isinstance(values,dict) and values.get('mode') in ('READ_ONLY','APPLY','PUBLICATION_PLAN'):
        if 'counts' in values:
            counts=' / '.join(f"{k}: {v}" for k,v in values['counts'].items()) or "No changes"
            c.wrap(3,8,counts,c.width-6,2,"text")
        elif values.get('mode')=='PUBLICATION_PLAN':
            c.text(3,8,f"{values['images']} images  /  {values['outputs']} outputs  /  {values['duplicate_renders_avoided']} duplicate sizes avoided",width=c.width-6)
        c.text(3,11,"READ ONLY / NOTHING WRITTEN" if values.get('mode')!='APPLY' else f"CHECKPOINT {values.get('checkpoint')}","accent" if not values.get('blockers') else "warn")
    lines=json.dumps(values,indent=2,ensure_ascii=True,allow_nan=False).splitlines()
    # The complete data remains scrollable; no hidden/truncated record is credited
    # as a full inspection. Long source-free technical lines wrap at cell width.
    wrapped=[]
    for line in lines:wrapped.extend(textwrap.wrap(line,max(12,c.width-10),replace_whitespace=False,drop_whitespace=False) or [''])
    y=14 if isinstance(values,dict) and values.get('mode') in ('READ_ONLY','APPLY','PUBLICATION_PLAN') else 8
    capacity=c.height-y-6
    scroll=min(p.scroll,max(0,len(wrapped)-max(1,capacity)))
    for n,line in enumerate(wrapped[scroll:scroll+max(1,capacity)]):c.text(4,y+n,line,"muted",width=c.width-8)
    c.text(3,c.height-6,f"Lines {scroll+1}-{min(len(wrapped),scroll+max(1,capacity))}/{len(wrapped)}", "muted")
    request=p.request
    keys="[Up/Down/PgUp/PgDn] read   [Esc] back   [b] batches"
    if request and request.name=='organize':keys="[a] apply this policy   [Up/Down] read   [Esc] back"
    if request and request.name=='plan':keys="[r] protect this selection   [Up/Down] read   [Esc] back"
    footer(c,state,keys)


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
    c.text(3,6,"KEY MAP / NOTHING HERE EXECUTES SHELL TEXT", "accent",bold=True,width=c.width-6)
    lines=["Up/Down or j/k   Focus an action or row", "Enter           Open, edit, or run the focused action", "Esc / 0         Go back; discard an unfinished edit", "Space           Toggle an image selection or checkbox", "/               Search the current action list or clean catalog", "F1              This key map", "F2              Freeze/resume aesthetic motion", "F3              Cycle dark / light / monochrome palette", "F4              Exact direct-command lens (not executed)", "q               Quit from menus; waits for an active job", "Ctrl+C          Cooperative stop; destructive commits finish", "v               Open verified image pixels in a local viewer"]
    for n,line in enumerate(lines[state.page.scroll:state.page.scroll+max(1,c.height-15)]):c.text(3,9+n,line,"text",width=c.width-6)
    footer(c,state,"[Up/Down] scroll   [Esc] return")


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
        c.put(x+4+cursor,y+6,char,"ink","accent",True)
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
               'command':lambda:command_page(c,state),'confirm':lambda:confirm(c,state)}
    renderers.get(page,lambda:home(c,state,time))()
    if state.page.query_edit:
        c.fill(3,c.height-5,c.width-6,1,"raised")
        c.text(3,c.height-5,"FIND / "+state.page.query+"_","accent",width=c.width-6)
    if state.editor:editor_overlay(c,state)
    return c
