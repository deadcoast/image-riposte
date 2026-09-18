"""Menu entry, navigation and action-specific path intent regressions."""
import io
from pathlib import Path
import pytest
from riposte.errors import RiposteError
from riposte.terminal.keyboard import Key
from riposte.terminal.paths import Picker, validate_workspace
from riposte.terminal.app import linear_session
from riposte.terminal.controller import Controller
from riposte.terminal.output import Presentation
from riposte.terminal.render import render


def test_no_root_opens_actions_without_path_editor():
    controller = Controller(None, Presentation())
    try:
        assert controller.state.page.name == 'home'
        assert controller.state.editor is None
        screen = render(controller.state, 100, 34, 0).plain()
        assert 'MAIN MENU' in screen and 'Sort + RIPOSTE' in screen
        assert '01 CHOOSE' not in screen and 'Artwork' not in screen
    finally:
        controller.shutdown()


def test_no_root_linear_entry_can_quit_from_menu_without_a_path():
    controller = Controller(None, Presentation(plain=True))
    output = io.StringIO()
    try:
        linear_session(controller, io.StringIO('q\n'), output)
        assert controller.state.root is None and controller.state.editor is None
        assert 'MAIN MENU' in output.getvalue()
        assert 'value (/cancel)>' not in output.getvalue()
    finally:
        controller.shutdown()


@pytest.fixture
def menu(tmp_path, monkeypatch):
    inputs = tmp_path / 'inputs'; inputs.mkdir()
    results = tmp_path / 'results'; results.mkdir()
    monkeypatch.setattr('riposte.terminal.controller.starting_directory', lambda root=None: root or inputs)
    monkeypatch.setattr('riposte.terminal.paths.application_directory', lambda: tmp_path / 'application')
    controller = Controller(None, Presentation())
    yield controller, inputs, results
    controller.shutdown()


@pytest.mark.parametrize('number,action', [('1','riposte'), ('2','organize'), ('3','sort-riposte')])
def test_visible_actions_open_explained_browser_before_root(menu, number, action):
    c, inputs, _ = menu
    c.key(Key('char',number))
    p=c.state.page
    assert p.name=='picker' and p.action==action and c.state.root is None
    assert c.state.editor is None and c.state.operation is None
    screen=render(c.state,72,24).plain()
    assert '[Esc] Cancel' in screen
    assert ('Originals stay' in screen) if action=='riposte' else ('REPLACE' in screen)
    assert not list(inputs.iterdir())
    c.key(Key('escape'))
    assert c.state.page.name=='home' and c.state.root is None
    assert c.state.page.cursor==int(number)-1


@pytest.mark.parametrize('width,height', [(72,24),(100,34),(160,50)])
def test_menu_all_actions_visible_and_navigation_is_discoverable(width,height):
    c=Controller(None,Presentation())
    text=render(c.state,width,height).plain()
    for label in ('MAIN MENU','RIPOSTE','Sort + RIPOSTE','Image library','Workshop','Arrows','Enter'):
        assert label in text


def test_arrows_enter_and_escape_preserve_menu_focus(menu):
    c,_,_=menu
    c.key(Key('down'));c.key(Key('enter'))
    assert c.state.page.action=='organize'
    c.key(Key('escape'))
    assert c.state.page.cursor==1 and c.state.page.name=='home'


def test_multiple_inputs_and_separate_results_preserve_originals(menu):
    c,inputs,results=menu
    files=[inputs/f'image {n}.png' for n in range(6)]
    for path in files:path.write_bytes(b'unchanged')
    c.key(Key('enter'))
    for n in range(2,8):
        c.state.page.cursor=n;c.key(Key('char',' '))
    assert len(c.state.page.result.selected)==6
    c.key(Key('home'));c.key(Key('enter'))
    assert c.state.page.values['mode']=='workspace' and c.state.root is None
    assert 'results' in render(c.state,72,24).plain()
    c.state.page.result.enter(results);c.state.page.rows=c.state.page.result.rows();c.key(Key('enter'))
    request=c.request_from_form()
    assert request.name=='riposte' and request.root==results
    assert request.values['input_paths']==files
    assert c.state.operation is None and not list(results.iterdir())
    assert all(p.read_bytes()==b'unchanged' for p in files)
    c.state.page.values['epsilon']=3
    c.key(Key('enter'))
    assert c.state.page.name=='picker'
    c.key(Key('enter'))
    c.key(Key('enter'))
    assert c.state.page.name=='form' and c.state.page.values['epsilon']==3


def test_cancel_results_selection_returns_to_inputs_without_setting_root(menu):
    c,inputs,_=menu
    c.key(Key('enter'));c.key(Key('char','s'));c.key(Key('enter'))
    c.key(Key('escape'))
    assert c.state.root is None
    assert c.state.page.result.selected==[inputs]
    c.key(Key('escape'));assert c.state.page.name=='home'


def test_browse_parent_locations_and_optional_pasted_location(menu):
    c,inputs,results=menu
    child=inputs/'child';child.mkdir()
    c.key(Key('char','2'));c.state.page.cursor=2;c.key(Key('enter'))
    assert c.state.page.result.directory==child
    c.key(Key('backspace'));assert c.state.page.result.directory==inputs
    c.key(Key('char','l'));assert c.state.page.values['locations']
    c.key(Key('char','g'));c.key(Key('clear'));c.key(Key('paste',str(results/'missing')));c.key(Key('enter'))
    assert c.state.editor.error and c.state.root is None
    c.key(Key('clear'));c.key(Key('paste',str(results)));c.key(Key('enter'))
    assert c.state.editor is None and c.state.page.result.directory==results
    c.key(Key('enter'))
    assert c.state.root==results and c.state.page.action=='organize'
    assert not list(results.iterdir())


def test_application_overlap_is_blocked_without_dismissing_picker(menu, monkeypatch):
    c,inputs,_=menu
    monkeypatch.setattr('riposte.terminal.paths.application_directory',lambda:inputs)
    c.key(Key('char','2'));c.key(Key('enter'))
    assert c.state.root is None and c.state.page.name=='picker'
    assert 'separate' in c.state.notice
    for p in (inputs,inputs/'inside',inputs.parent):
        with pytest.raises(RiposteError,match='IMAGE_FOLDER_OVERLAPS_APPLICATION'):validate_workspace(p)


def test_permission_error_leaves_parent_navigation_available(tmp_path,monkeypatch):
    picker=Picker(tmp_path)
    def denied(self):raise PermissionError
    monkeypatch.setattr(Path,'iterdir',denied)
    rows=picker.rows()
    assert rows[1]['kind']=='parent' and 'Cannot read' in picker.error


def test_browser_skips_links_and_internal_state(tmp_path,monkeypatch):
    for name in ('visible','.riposte','.shroud','linked'):(tmp_path/name).mkdir()
    monkeypatch.setattr('riposte.terminal.paths.linked',lambda p:p.name=='linked')
    assert [r['title'] for r in Picker(tmp_path).rows()][2:]==['visible']


def test_model_browser_does_not_need_image_root(menu):
    c,inputs,_=menu
    c.key(Key('char','6'));assert c.state.page.name=='form'
    c.key(Key('char','b'));assert c.state.page.name=='picker'
    c.key(Key('enter'))
    assert c.state.page.values['vae1']==str(inputs) and c.state.root is None
