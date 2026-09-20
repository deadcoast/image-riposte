"""Behavior checks for picker focus, recovery and single-use confirmation."""
import pytest

from riposte.terminal.controller import Controller
from riposte.terminal.interaction import hints
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render


def finish(c):
    assert c.state.operation is not None
    assert c.state.operation.done.wait(10)
    c.pump()


@pytest.fixture
def menu(root):
    c = Controller(root, Presentation(no_animation=True))
    c.sorter()
    try:
        yield c
    finally:
        c.shutdown()


@pytest.mark.parametrize("height", [24, 34, 46])
def test_picker_page_jump_matches_visible_rows_and_parent_restores_focus(menu, root, height):
    for n in range(80): (root / f"folder-{n:02d}").mkdir()
    menu.state.height = height
    menu.key(Key("char", "b"))
    menu.key(Key("pagedown"))
    assert menu.state.page.cursor == height - 18
    selected = menu.selected_row()["path"]
    menu.key(Key("enter"))
    assert menu.state.page.result.directory == selected
    menu.key(Key("backspace"))
    assert menu.selected_row()["path"] == selected
    assert f"> {height-17:2}" in render(menu.state, 100, height).plain()
    menu.key(Key("pageup"))
    assert menu.state.page.cursor == 0


def test_parent_row_also_restores_child_focus(menu, root):
    for name in ("a", "b", "c"): (root / name).mkdir()
    menu.key(Key("char", "b")); menu.key(Key("end")); menu.key(Key("enter"))
    menu.key(Key("down")); menu.key(Key("enter"))
    assert menu.selected_row()["path"] == root / "c"


def test_sort_preview_does_not_refresh_publishing_history(menu, root, make_image, monkeypatch):
    make_image(root / "painting.png")
    monkeypatch.setattr(menu, "refresh", lambda: pytest.fail("unrelated publishing history read"))
    menu.key(Key("char", "2")); finish(menu)
    assert menu.state.page.result["ready"]


@pytest.mark.parametrize("mode", ["1", "2"])
def test_blocked_preview_offers_workshop_without_apply(menu, root, make_image, mode):
    source = make_image(root / "painting.png")
    sidecar = root / "painting.xmp"; sidecar.write_text("retained metadata")
    original = source.read_bytes()
    menu.key(Key("char", mode)); finish(menu)
    assert not menu.state.page.result["ready"]
    assert hints(menu.state)[0].label == "Return"
    assert "[w] Full Sort Workshop" in render(menu.state, 72, 24).plain()
    menu.key(Key("char", "w"))
    assert menu.state.page.name == "form" and menu.state.page.action == "organize"
    assert menu.state.page.values["categories"] is True
    assert menu.state.page.values["discard_sidecars"] is False
    assert menu.state.operation is None and source.read_bytes() == original
    assert sidecar.read_text() == "retained metadata"
    menu.key(Key("escape"))
    assert menu.state.page.name == "sorter"


def test_blocked_preview_enter_returns(menu, root):
    (root / "painting.xmp").touch()
    menu.key(Key("char", "1")); finish(menu)
    menu.key(Key("enter"))
    assert menu.state.page.name == "sorter" and menu.state.operation is None


def test_stale_sort_retains_recovery_and_path_shortcut(menu, root, make_image):
    source = make_image(root / "painting.png")
    menu.key(Key("char", "1")); finish(menu)
    menu.key(Key("enter"))
    source.write_bytes(b"changed after preview")
    menu.key(Key("char", "REPLACE")); menu.key(Key("enter")); finish(menu)
    assert menu.state.page.code == "CATEGORY_PREVIEW_CHANGED"
    screen = render(menu.state, 72, 24).plain()
    assert "Preview again" in screen and "[g] Enter Path" in screen
    menu.key(Key("char", "a"))
    assert menu.state.page.code == "CATEGORY_PREVIEW_CHANGED"
    menu.key(Key("char", "g"))
    assert menu.state.page.name == "sorter" and menu.state.editor.target == "sort-path"
    assert menu.state.operation is None


def test_completed_undo_returns_without_filled_confirmation(menu, root, make_image):
    source = make_image(root / "painting.png"); original = source.read_bytes()
    menu.key(Key("char", "1")); finish(menu)
    menu.key(Key("enter")); menu.key(Key("char", "REPLACE")); menu.key(Key("enter")); finish(menu)
    menu.key(Key("enter")); menu.key(Key("char", "u")); finish(menu)
    menu.key(Key("enter")); menu.key(Key("char", "UNDO")); menu.key(Key("enter")); finish(menu)
    assert source.read_bytes() == original
    menu.key(Key("enter"))
    assert menu.state.page.name == "sorter"
    assert all(p.name != "confirm" for p in menu.state.stack)
    assert menu.state.operation is None


@pytest.mark.parametrize("dimensions", [(72, 24), (100, 34)])
def test_confirmation_displays_bound_folder_and_complete_warning(menu, root, make_image, dimensions):
    make_image(root / "painting.png")
    menu.key(Key("char", "1")); finish(menu); menu.key(Key("enter"))
    text = render(menu.state, *dimensions).plain()
    assert root.name in text
    assert "TYPE REPLACE" in text
    assert "private undo history" in " ".join(text.split())
    assert "Failed inputs remain" in " ".join(text.split())


def test_path_validation_explains_error_without_losing_input(menu, root):
    menu.key(Key("char", "g"))
    path = str(root / "missing-folder")
    menu.key(Key("paste", path)); menu.key(Key("enter"))
    text = render(menu.state, 72, 24).plain()
    assert "Folder not found" in text and "[Esc]" in text
    assert menu.state.editor.value == path and menu.state.root == root
    menu.key(Key("clear"))
    assert not menu.state.editor.error
    menu.key(Key("paste", str(root))); menu.key(Key("enter"))
    assert menu.state.editor is None and menu.state.page.name == "sorter"


def test_no_folder_pending_preview_has_accurate_enter_label(root, make_image):
    make_image(root / "painting.png")
    c = Controller(None, Presentation())
    try:
        c.sorter(); c.key(Key("char", "1"))
        assert hints(c.state)[0].label == "Preview"
        assert "[Enter] preview" in render(c.state, 72, 24).plain()
        c.key(Key("escape")); c.key(Key("char", "g"))
        assert hints(c.state)[0].label == "Save"
        c.key(Key("paste", str(root))); c.key(Key("enter"))
        assert c.state.operation is None
    finally:
        c.shutdown()


@pytest.mark.parametrize("activation", [Key("enter"), Key("char", "a")])
def test_empty_sort_returns_without_meaningless_confirmation(menu, root, activation):
    menu.key(Key("char", "1")); finish(menu)
    screen = render(menu.state, 72, 24).plain()
    assert "NO CHANGES" in screen and "Nothing to sort" in screen
    assert hints(menu.state)[0].label == "Return"
    menu.key(activation)
    assert menu.state.page.name == "sorter" and menu.state.operation is None
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("key,page", [("f1", "help"), ("f4", "command")])
def test_confirmation_help_and_command_return_without_executing(menu, root, make_image, key, page):
    source = make_image(root / "painting.png")
    menu.key(Key("char", "1")); finish(menu); menu.key(Key("enter"))
    menu.key(Key("char", "REP")); confirmation = menu.state.page
    menu.key(Key(key))
    assert menu.state.page.name == page and menu.state.operation is None
    if key == "f4": assert menu.state.page.request == confirmation.confirm_request
    menu.key(Key("escape"))
    assert menu.state.page is confirmation and confirmation.values["confirmation"] == "REP"
    assert source.exists()
