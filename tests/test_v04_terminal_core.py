import io, json, threading, time
from pathlib import Path
import pytest
from rich.console import Console
from riposte.errors import RiposteError
from riposte.terminal.keyboard import Key,KeyDecoder,SEQUENCES
from riposte.terminal.jobs import Operation,safe_phase,safe_code
from riposte.terminal.service import Request
from riposte.terminal.surface import Surface
from riposte.terminal.output import Presentation
from riposte.terminal.controller import Controller
from riposte.terminal.render import render,scroll_limit
from riposte.terminal.state import Page
from riposte.terminal.app import _line_command

@pytest.mark.parametrize('sequence,name',list(SEQUENCES.items()))
def test_fragmented_keys(sequence,name):
    d=KeyDecoder()
    for i,ch in enumerate(sequence):
        d.feed(ch);key=d.next()
        if i<len(sequence)-1:assert key is None
        else:assert key==Key(name)


def test_paste_newlines_are_data_not_execution():
    d=KeyDecoder();d.feed('\x1b[200~abc\nREPLACE\r\nq\x1b[201~')
    key=d.next();assert key.name=='paste' and key.text=='abc REPLACE  q'
    assert d.next() is None


def test_large_paste_bounded_and_resynchronizes():
    d=KeyDecoder();d.feed('\x1b[200~');assert d.next() is None
    for _ in range(10):d.feed('x'*8000);assert d.next() is None
    d.feed('\x1b[201~q');assert len(d.next().text)==4096
    assert d.next()==Key('char','q')


def test_unknown_csi_is_consumed_not_menu_digits():
    d=KeyDecoder();d.feed('\x1b[<0;12;13M');assert d.next().name=='ignored';assert d.next() is None
    d.feed('\x1b');assert d.next() is None;assert d.next(flush_escape=True).name=='escape'

@pytest.mark.parametrize('value',['/PRIVATE/file','C:\\PRIVATE','../secret','\x1b[31m','x'*500])
def test_progress_does_not_repeat_paths_or_controls(value):
    assert safe_phase(value)=='Working';assert safe_code(value)=='OPERATION_FAILED'


def test_operation_real_counts_and_phase_reset():
    o=Operation(Request('plan'))
    o.progress({'phase':'Preparing','processed':4,'total':10});a=o.snapshot()
    assert (a.processed,a.total)==(4,10)
    o.progress({'phase':'Loading'});assert o.snapshot().processed is None
    o.progress({'phase':'Loading','processed':True,'total':0});assert o.snapshot().processed is None and o.snapshot().total is None


def test_cancellable_worker_joins():
    entered=threading.Event()
    def work(req,progress):
        entered.set()
        for n in range(1000):progress({'phase':'Optimizing','processed':n,'total':1000});time.sleep(.001)
    op=Operation(Request('publish'),work).start();assert entered.wait(1)
    assert op.cancel();assert op.done.wait(2);op.join()
    assert op.exit_code==130 and not op.thread.is_alive() and not op.thread.daemon


def test_source_commit_does_not_cancel():
    finish=threading.Event()
    def commit(req,progress):
        assert finish.wait(2);progress({'phase':'Committing','processed':1,'total':1});return {'checkpoint':'COMPLETE'}
    op=Operation(Request('apply'),commit).start();assert not op.cancel()
    finish.set();assert op.done.wait(2);op.join();assert op.exit_code==0


def test_backend_exception_does_not_leak():
    def broken(*a):raise RuntimeError('/PRIVATE/LOCATION')
    o=Operation(Request('doctor'),broken).start();assert o.done.wait(2);o.join()
    assert o.snapshot().code=='OPERATION_FAILED' and '/PRIVATE' not in repr(o.snapshot())

@pytest.mark.parametrize('dimensions',[(79,24),(100,34),(132,46)])
@pytest.mark.parametrize('theme',['dark','light','mono'])
@pytest.mark.parametrize('page',['home','library','form','preferences','help','confirm','workshop','result','command'])
def test_every_scene_ascii_and_bounded(root,dimensions,theme,page):
    c=Controller(root,Presentation(theme=theme));s=c.state;s.width,s.height=dimensions
    if page=='form':c.action('doctor')
    elif page=='preferences':c.preferences();s.page.cursor=6
    elif page=='confirm':c.confirm(Request('apply',root),'REPLACE','Apply this cleaning policy.')
    elif page=='result':c.show(Page('result','FULL DATA',result={'mode':'READ_ONLY','counts':{'images':5},'rows':list(range(50))}))
    elif page!='home':c.show(Page(page,page.upper()))
    a=render(s,*dimensions,1.2);text=a.plain();lines=text.splitlines()
    assert len(lines)==dimensions[1] and all(len(line)==dimensions[0] for line in lines)
    assert all(32<=ord(ch)<127 or ch=='\n' for ch in text)
    sink=io.StringIO();Console(file=sink,width=dimensions[0],height=dimensions[1],force_terminal=False).print(a)
    assert '\x1b' not in sink.getvalue()
    if page=='preferences':assert 'Legacy state upgrade' in text
    if page=='confirm':assert 'private undo history' in ' '.join(text.split()) and 'TYPE REPLACE' in text


def test_end_scroll_is_bounded_and_up_recovers(root):
    c=Controller(root,Presentation());c.show(Page('result','Full',result=list(range(100))))
    c.key(Key('end'));limit=scroll_limit(c.state);assert c.state.page.scroll==limit
    c.key(Key('up'));assert c.state.page.scroll==limit-1
    c.show(Page('help','Keys'));c.key(Key('end'));assert c.state.page.scroll<=12


def test_motion_and_freeze_do_not_alter_operation_state(root):
    c=Controller(root,Presentation());s=c.state
    a=render(s,132,46,0);b=render(s,132,46,2)
    assert a.cells!=b.cells and not list(root.iterdir())
    c.key(Key('f2'));assert s.paused
    assert render(s,132,46,s.frozen_time).cells==render(s,132,46,s.frozen_time).cells
    c.key(Key('f3'));assert s.presentation.theme=='light'


def test_small_terminal_cannot_activate_hidden_write(root):
    c=Controller(root,Presentation());c.confirm(Request('apply',root),'REPLACE','Apply')
    c.state.width=50;c.state.height=15
    c.state.page.values['confirmation']='REPLACE';c.key(Key('enter'))
    assert c.state.operation is None and not list(root.iterdir())
    c.key(Key('char','q'));assert not c.state.running


def test_model_path_editor_session_only(root):
    c=Controller(root,Presentation());c.action('doctor');c.key(Key('enter'))
    c.key(Key('paste','/LOCAL MODEL'));c.key(Key('enter'))
    assert c.state.page.values['vae1']=='/LOCAL MODEL' and not list(root.iterdir())
    c.key(Key('f4'));assert c.state.page.name=='command' and not list(root.iterdir())


def test_linear_input_is_selection_not_shell(root):
    c=Controller(root,Presentation());_line_command(c,'rm -rf ANYTHING')
    assert c.state.operation is None and not list(root.iterdir())
    c.action('doctor');_line_command(c,'edit 1 /MODEL WITH SPACES')
    assert c.state.page.values['vae1']=='/MODEL WITH SPACES'
