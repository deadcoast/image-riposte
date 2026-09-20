"""The reconstructed post-0.4 design contract, using the production renderer."""
import io
import json
import re
from dataclasses import asdict
from pathlib import Path
import pytest
from rich.console import Console
from riposte import cli
from riposte.terminal.surface import Surface, PALETTES
from riposte.terminal.palette import GOKS
from riposte.terminal.output import Presentation, emit
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.state import Page
from riposte.terminal.service import Request, execute
from riposte.terminal.render import render, scroll_limit
from riposte.terminal.reports import overview, report_lines, raw_lines, Writer, tree
from riposte.terminal.interaction import fields_for, hints

TOKENS={"gokn0":"#2E3440","gokn1":"#3B4252","gokn2":"#434C5E","gokn4":"#D8DEE9","gokn5":"#E5E9F0","gokn6":"#ECEFF4","gokn7":"#8FBCBB","gokn8":"#88C0D0","gokn9":"#81A1C1","gokn11":"#BF616A","gokn12":"#D08770","gokn13":"#EBCB8B"}
PLAN={"mode":"READ_ONLY","plan_id":"a"*64,"counts":{"images_to_migrate":7,"already_clean":3,"input_bytes":2048},"destinations":{"2026/September/MED":7},"blockers":{},"ready":True,"source_policy":"Verified sources removed only on apply."}


def test_palette_exact_and_terminal_owned():
    assert GOKS==TOKENS and Presentation().theme=="goks"
    for palette in PALETTES.values():
        assert all(palette[k]=="default" for k in ("bg","panel","raised"))

@pytest.mark.parametrize("theme",list(PALETTES))
@pytest.mark.parametrize("page",["home","library","form","result","preferences","help","confirm"])
def test_all_terminal_surfaces_reject_background_fill(root,theme,page):
    c=Controller(root,Presentation(theme=theme))
    if page=="form":c.action("doctor")
    elif page=="result":c.show(Page("result","Plan",result=PLAN,request=Request("organize",root)))
    elif page=="preferences":c.preferences()
    elif page=="confirm":c.confirm(Request("apply",root,{"plan_id":execute(Request("organize",root))["plan_id"]}),"REPLACE","Replace sources")
    elif page!="home":c.show(Page(page,page))
    surface=render(c.state,100,34,1)
    assert all(cell.bg=="bg" for row in surface.cells for cell in row)
    stream=io.StringIO();console=Console(file=stream,width=100,force_terminal=True,color_system="truecolor")
    segments=list(surface.__rich_console__(console,console.options))
    assert all(segment.style is None or segment.style.bgcolor.is_default for segment in segments)
    assert all(not segment.style or not segment.style.reverse for segment in segments)
    console.print(surface)
    assert "\x1b[48;" not in stream.getvalue()


def test_explicit_cell_colour_cannot_overwrite_host_background():
    surface=Surface(20,5);surface.fill(0,0,20,5,"#00ffff");surface.put(0,0,"A",bg="#ff0000")
    assert all(cell.bg=="bg" for row in surface.cells for cell in row)


def test_enter_select_i_inspect_and_space_compatibility(root,make_image):
    make_image(root/"input.png");execute(Request("apply",root,{"plan_id":execute(Request("organize",root))["plan_id"]}))
    c=Controller(root,Presentation());c.library();row=c.state.catalog[0]
    c.key(Key("enter"));assert c.state.page.name=="library" and row["id"] in c.state.selected
    c.key(Key("char","i"));assert c.state.page.name=="asset"
    c.key(Key("enter"));assert row["id"] not in c.state.selected
    c.key(Key("escape"));c.key(Key("char"," "));assert row["id"] in c.state.selected
    assert hints(c.state)[0].key=="Enter" and hints(c.state)[0].label=="Select"


def test_report_overview_is_not_json_and_details_are_complete(root):
    c=Controller(root,Presentation());c.show(Page("result","Plan",result=PLAN,request=Request("organize",root)))
    initial=render(c.state,100,34).plain()
    assert "MIGRATION PLAN" in initial and '"images_to_migrate"' not in initial
    c.key(Key("char","t"));assert c.state.page.report_view=="details"
    c.key(Key("char","t"));assert c.state.page.report_view=="json"
    surface=render(c.state,100,34)
    assert '"mode"' in surface.plain()
    c.key(Key("end"));assert c.state.page.scroll==scroll_limit(c.state)
    c.key(Key("char","t"));assert c.state.page.report_view=="overview" and c.state.page.scroll==0


def test_json_syntax_roles_and_lossless_unwrap():
    value={"foo":"\\x1b[31m NOT CONTROL", "number":12, "boolean":True, "deep":[None,{"a":"z"*110}]}
    lines=raw_lines(value,40)
    reconstructed="".join(record.plain for record in lines)
    assert json.loads(reconstructed)==value
    assert {run.role for record in lines for run in record.runs}>={"label","value","number","code"}


@pytest.mark.parametrize("width,height",[(79,24),(100,34),(132,46)])
def test_report_draw_uses_actual_viewport_and_can_scroll(root,width,height):
    c=Controller(root,Presentation());c.state.width=width;c.state.height=height
    c.show(Page("result","Plan",result=PLAN,request=Request("organize",root)))
    c.key(Key("end"))
    surface=render(c.state,width,height)
    assert all(len(row)==width for row in surface.plain().splitlines())
    assert "[Enter]" in surface.plain() and "[F1]" in surface.plain()
    assert not list(root.iterdir())


def test_enter_from_migration_plan_still_requires_replace(root):
    c=Controller(root,Presentation());c.show(Page("result","Plan",result=PLAN,request=Request("organize",root)))
    c.key(Key("enter"));assert c.state.page.confirm_word=="REPLACE" and c.state.operation is None
    c.key(Key("enter"));assert c.state.operation is None and not list(root.iterdir())


def test_advanced_disclosure_preserves_all_settings(root):
    c=Controller(root,Presentation());c.state.selected.add("a"*32);c.action("publish")
    p=c.state.page;p.values.update(steps=73,vae4="SESSION_ONLY")
    assert len(fields_for(p))==5
    c.key(Key("char","f"));assert p.advanced and len(fields_for(p))==15
    c.key(Key("char","f"));assert not p.advanced and p.values["steps"]==73 and p.values["vae4"]=="SESSION_ONLY"
    request=c.request_from_form();assert request.values["steps"]==73


def test_contextual_help_describes_the_focused_setting(root):
    c=Controller(root,Presentation());c.action("doctor")
    expected=fields_for(c.state.page)[0].help
    c.key(Key("f1"));assert c.state.page.result["context"]==expected
    assert c.state.page.result["controls"][0]["key"]=="Enter"
    c.key(Key("escape"));assert c.state.page.action=="doctor"


@pytest.mark.parametrize("command,data,title",[
    ("organize",PLAN,"Migration plan"),
    ("audit",{"checkpoint":"INCOMPLETE","verified_images":5,"verified_artifacts":2,"blockers":{"DECODE_FAILED":1}},"Workspace audit"),
    ("plan",{"mode":"PUBLICATION_PLAN","images":3,"outputs":5,"duplicate_renders_avoided":1,"tasks":[],"recipe":{}},"Publishing plan"),
    ("package",{"relative":".riposte/exports/B/RIPOSTE.zip","bytes":30000,"contents":"APPROVED_DATE_ONLY_PNGS","sha256":"a"*64},"Approved image pack"),
    ("doctor",{"runtime":{"cpu":True,"cuda":False,"mps":False,"versions":{},"missing":["diffusers"]}},"Local processing runtime"),
    ("publications",{"mode":"PUBLICATION_BATCH","id":"a"*32,"status":"FINISHED","counts":{"BLOCKED":1},"items":[]},"Publishing batch"),
    ("generation",{"frames":[{"file":"F000.png"}],"status":"UNVERIFIED"},"Generation report"),
])
def test_dedicated_report_types(command,data,title):
    before=json.dumps(data,sort_keys=True)
    report=overview(data,command,76)
    assert report.title==title and report.body
    assert json.dumps(data,sort_keys=True)==before
    assert all(len(record.plain)<=76 for record in report.body)
    if command=="audit":assert report.outcome=="INCOMPLETE" and report.tone=="warn"
    if command=="publications":assert report.tone=="warn"


def test_human_vs_automation_result_contract(capsys):
    emit(PLAN,Presentation(json_output=False,plain=True),"organize")
    value=capsys.readouterr().out
    assert "MIGRATION PLAN" in value and "Calendar" not in value and '"ready":' not in value
    assert "2026/September/MED" in value and "\x1b" not in value
    emit(PLAN,Presentation(json_output=True),"organize")
    assert json.loads(capsys.readouterr().out)==PLAN


def test_complete_tree_retains_unknown_nested_data_without_braces():
    data={"new_field":{"unknown_key":[1,2,{"text":"keep this"}]}}
    w=Writer(60);tree(w,data)
    text="\n".join(l.plain for l in w.lines)
    assert "Unknown key" in text and "keep this" in text and "{" not in text


def test_cli_accepts_goks(root,capsys):
    assert cli.main(["--theme","goks","--plain","list",str(root)])==0
    assert "CLEAN IMAGE LIBRARY" in capsys.readouterr().out
