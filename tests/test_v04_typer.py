"""Native command contract and same-action CLI/menu parity; no pretrained claims."""
import json
from pathlib import Path
import pytest
import typer
from riposte import cli
from riposte.errors import RiposteError
from riposte.terminal.actions import ACTIONS, defaults, make_request, request_argv, Field, parse_value
from riposte.terminal.service import Request, execute, parse_month
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog

COMMANDS=[command.name for command in cli.app.registered_commands]

@pytest.mark.parametrize('name',COMMANDS)
def test_every_command_has_real_typer_help(name,capsys):
    assert isinstance(cli.app,typer.Typer)
    assert cli.main([name,'--help'])==0
    out=capsys.readouterr().out
    assert 'Usage:' in out and '\x1b' not in out
    assert all(ord(c)<128 for c in out)

@pytest.mark.parametrize('action',ACTIONS,ids=lambda a:a.key)
def test_every_menu_action_roundtrips_to_direct_typer(action,root,monkeypatch):
    values=defaults(action)
    for f in action.fields:
        if f.kind=='id':values[f.key]='a'*32
        elif f.kind=='ids':values[f.key]=('b'*32,)
        elif f.kind=='path':values[f.key]='LOCAL MODEL'
        elif f.key=='relative':values[f.key]='identity/7/clean/frame-000.png'
    request=make_request(action.key,root,values,['c'*32])
    captured=[]
    monkeypatch.setattr(cli,'run_direct',lambda req,pres:captured.append(req) or 0)
    assert cli.main(request_argv(request)[1:])==0,request_argv(request)
    assert len(captured)==1
    actual=captured[0]
    assert actual.name==request.name
    assert actual.root==(None if action.key=='doctor' else root)
    for key,value in request.values.items():
        other=actual.values.get(key)
        if isinstance(value,(tuple,list)):assert list(other)==list(value),(key,other,value)
        elif isinstance(value,Path):assert Path(other)==value
        elif value not in ('',None):assert other==value,(key,other,value)

@pytest.mark.parametrize('args',[
    ['publish','ROOT','--epsilon','17'],['publish','ROOT','--steps','0'],
    ['publish','ROOT','--restarts','5'],['publish','ROOT','--edge','63'],
    ['publish','ROOT','--delta-e76-p95','nan'],['guard','ROOT','a'*32,'--device','SECRET_PATH'],
    ['--fps','31'],['--theme','SECRET_PATH'],['review','ROOT','x','--decision','SECRET_PATH'],
    ['frame','ROOT','x'],['compare','ROOT','x','candidate','--max-edge','1']])
def test_invalid_arguments_never_echo_rejected_values(args,capsys):
    assert cli.main(['--json',*args])==2
    captured=capsys.readouterr()
    assert not captured.out and '\x1b' not in captured.err and 'SECRET_PATH' not in captured.err
    assert json.loads(captured.err)['error']

@pytest.mark.parametrize('text,result',[('Sep','September'),('9','September'),('september','September'),('ALL',None),(None,None)])
def test_month_normalization(text,result):assert parse_month(text)==result

@pytest.mark.parametrize('value',['0','13','../September','\x1b[31mSeptember'])
def test_bad_month_filter(value):
    with pytest.raises(RiposteError):parse_month(value)

@pytest.mark.parametrize('kind,raw',[('int',True),('int',1.5),('float','nan'),('float','inf'),('id','../source'),('path','x\x1by'),('ids','a'*32+','+'a'*32)])
def test_invalid_form_values(kind,raw):
    with pytest.raises(RiposteError):parse_value(Field('x','X',kind),raw)


def test_readonly_targeting_and_plan_no_files(root,make_image,capsys):
    make_image(root/'raw.png',day='2026-09-10');organize(root,Policy(date_mode='modified'))
    before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert cli.main(['--json','list',str(root),'--year','2026','--month','sep','--size','SML'])==0
    rows=json.loads(capsys.readouterr().out);assert len(rows)==1
    assert cli.main(['--json','publish',str(root),'--all','--year','2026','--month','9','--size','SML','--plan'])==0
    assert json.loads(capsys.readouterr().out)['outputs']==1
    after={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert before==after


def test_ui_resolves_global_workspace(root,monkeypatch):
    import riposte.terminal.app as app
    calls=[]
    monkeypatch.setattr(app,'launch',lambda path,pres,**kw:calls.append((path,kw)) or 0)
    assert cli.main(['--root',str(root),'ui'])==0
    assert calls[0][0]==root


def test_human_and_machine_output_are_distinct(root,capsys):
    assert cli.main(['--json','list',str(root)])==0
    assert json.loads(capsys.readouterr().out)==[]
    assert cli.main(['--plain','list',str(root)])==0
    out=capsys.readouterr().out;assert 'No records' in out and '\x1b' not in out


def test_master_transform_is_not_silently_ignored(root,make_image):
    make_image(root/'raw.png');organize(root,Policy(date_mode='modified'))
    row=catalog(root)[0]
    with pytest.raises(RiposteError,match='CLEAN_MASTER_VIEW_INVALID'):
        execute(Request('image',root,{'image_id':row['id'],'view':'jpeg70'}))


def test_legacy_benchmark_has_no_invented_progress_parameter(root,monkeypatch):
    import riposte.benchmark as b
    calls=[]
    def run(r,trial,model,*,task,steps):calls.append((r,trial,task,steps));return {'ok':True}
    monkeypatch.setattr(b,'run_benchmark',run)
    assert execute(Request('benchmark',root,{'trial_id':'a'*32,'model':Path('MODEL')}))=={'ok':True}
    assert calls[0][3]==25


def test_missing_command_never_launches_menu_for_piped_direct_use(capsys):
    assert cli.main([])==2
    assert json.loads(capsys.readouterr().err)['error']=='INTERACTIVE_REQUIRES_TTY'
