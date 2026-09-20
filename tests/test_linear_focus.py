import pytest
from riposte.terminal.app import _line_command
from riposte.terminal.controller import Controller
from riposte.terminal.interaction import fields_for
from riposte.terminal.output import Presentation
from riposte.terminal.render import view_rows
from riposte.terminal.keyboard import Key
from riposte.terminal.service import Request, execute


@pytest.mark.parametrize('action,advanced', [('doctor', False), ('publish', False), ('publish', True)])
def test_focus_uses_visible_form_fields(root, make_image, action, advanced):
    if action == 'publish':
        make_image(root / 'input.png')
        execute(Request('apply', root, {'plan_id': execute(Request('organize', root))['plan_id']}))
    controller = Controller(root, Presentation(plain=True))
    if action == 'publish':
        controller.library()
        controller.key(Key('enter'))
    controller.action(action)
    if advanced:
        _line_command(controller, 'advanced')
    fields = fields_for(controller.state.page)
    assert len(fields) >= 3
    _line_command(controller, 'focus 3')
    assert controller.state.page.cursor == 2
    _line_command(controller, 'down')
    assert controller.state.page.cursor == 3
    _line_command(controller, 'edit 3 synthetic')
    # Doctor's third model path is an editable string; other forms may reject
    # the value, but retain focus and operation consent.
    if action == 'doctor':
        assert controller.state.page.values[fields[2].key] == 'synthetic'
    assert controller.state.operation is None
    _line_command(controller, 'focus 999')
    assert controller.state.page.cursor == len(fields) - 1
    _line_command(controller, 'focus -2')
    assert controller.state.page.cursor == 0
    _line_command(controller, 'focus invalid')
    assert controller.state.page.cursor == 0
    assert 'row number' in controller.state.notice


def test_non_form_focus_keeps_row_bounds(root):
    controller = Controller(root, Presentation(plain=True))
    rows = view_rows(controller.state)
    _line_command(controller, 'focus 3')
    assert controller.state.page.cursor == min(2, len(rows) - 1)
    _line_command(controller, 'focus 999')
    assert controller.state.page.cursor == len(rows) - 1
