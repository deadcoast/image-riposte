"""Default sorting and visible-folder/input regressions, using temporary media."""
import sys
import io
from collections import deque
from types import SimpleNamespace

import pytest

from riposte.terminal.app import _read_keys, linear_session
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key, TerminalKeys
from riposte.terminal.output import Presentation
from riposte.terminal.render import render


def finish(c):
    assert c.state.operation is not None
    assert c.state.operation.done.wait(10)
    c.pump()
    assert c.state.page.code is None


def paste_path(c, path):
    assert c.state.editor is not None
    assert c.state.editor.value == ""
    c.key(Key("paste", f'"{path}"'))
    c.key(Key("enter"))


def test_locations_survive_unhandled_input(tmp_path, monkeypatch):
    c = Controller(None, Presentation())
    target = tmp_path / "chosen"
    target.mkdir()
    monkeypatch.setattr("riposte.terminal.controller.locations", lambda: [
        {"kind": "directory", "title": "chosen", "path": target}])
    try:
        c.browse("sort", "organize")
        c.key(Key("char", "l"))
        c.key(Key("ignored"))
        assert c.state.page.rows[0]["path"] == target
        c.key(Key("enter"))
        assert c.state.page.result.directory == target
    finally:
        c.shutdown()


def test_windows_zero_timeout_polls_and_preserves_fragmented_escape(monkeypatch):
    chars = deque(["\xe0", "P", "g"])
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(
        kbhit=lambda: bool(chars), getwch=chars.popleft))
    monkeypatch.setattr("riposte.terminal.keyboard.os", SimpleNamespace(name="nt"))
    keyboard = TerminalKeys()
    assert keyboard.read(0) == Key("down")
    assert keyboard.read(0) == Key("char", "g")
    chars.append("\x1b")
    assert keyboard.read(0) is None
    chars.extend("[A")
    assert keyboard.read(0) == Key("up")


def test_bursts_are_drained_without_dropping_events_at_limit():
    received = []
    events = deque(Key("char", str(n)) for n in range(300))
    controller = SimpleNamespace(state=SimpleNamespace(running=True), key=received.append)
    keyboard = SimpleNamespace(read=lambda timeout: events.popleft() if events else None)
    while _read_keys(controller, keyboard, .01):
        pass
    assert [k.text for k in received] == [str(n) for n in range(300)]


def test_folder_listing_does_not_probe_each_media_file(root, monkeypatch):
    from riposte.terminal.paths import Picker
    for n in range(200): (root / f"image-{n}.png").touch()
    child = root / "folder"; child.mkdir()
    probed = []
    monkeypatch.setattr("riposte.terminal.paths.linked", lambda p: probed.append(p) or False)
    rows = Picker(root).rows()
    assert [r["path"] for r in rows[2:]] == [child]
    assert probed == [child]


def test_sort_path_does_not_load_unrelated_catalogs(root, monkeypatch):
    c = Controller(None, Presentation())
    try:
        monkeypatch.setattr(c, "refresh", lambda: pytest.fail("path entry loaded catalog history"))
        c.sorter(); c.sort_path(); paste_path(c, root)
        assert c.state.root == root and c.state.page.name == "sorter"
    finally:
        c.shutdown()


@pytest.mark.parametrize("dimensions", [(72, 24), (79, 24), (100, 34), (132, 46)])
def test_default_three_actions_and_all_home_choices_visible(dimensions):
    c = Controller(None, Presentation(no_animation=True))
    try:
        text = render(c.state, *dimensions).plain()
        for name in ("Riposte Sorter", "Full Sort Workshop", "Undo last sort", "w  Workshop"):
            assert name in text
        c.key(Key("enter"))
        assert c.state.page.name == "sorter" and c.state.editor is None
        assert [r["title"] for r in c.state.page.rows] == ["Sort", "Dry Run", "Enter Path"]
        text = render(c.state, *dimensions).plain()
        for label in ("1. Sort", "2. Dry Run", "3. Enter Path", "[g] Enter Path"):
            assert label in text
    finally:
        c.shutdown()


def test_default_dry_run_uses_category_policy_and_cannot_apply(root, make_image):
    source = make_image(root / "a new painting.png")
    before = source.read_bytes()
    c = Controller(None, Presentation())
    try:
        c.key(Key("enter")); c.key(Key("char", "3")); paste_path(c, root)
        assert c.state.root == root and c.state.page.name == "sorter"
        c.key(Key("char", "2")); finish(c)
        assert c.state.page.values["sorter_mode"] == "dry-run"
        plan = c.state.page.result
        assert plan["ready"] and plan["category_sorting"]
        assert "/img/uncategorized/SML/" in plan["files"][0]["destination"]
        assert c.state.page.request.values["date_mode"] == "download"
        assert not c.state.page.request.values["discard_sidecars"]
        assert "[Enter] Return" in render(c.state, 100, 34).plain()
        c.key(Key("char", "a"))
        assert c.state.page.name == "sorter" and c.state.operation is None
        assert source.read_bytes() == before
        assert list(root.iterdir()) == [source]
    finally:
        c.shutdown()


def test_sort_uses_saved_rules_exact_receipt_then_returns_to_sorter_and_undo(root, make_image):
    from riposte.category_rules import category_rules
    source = make_image(root / "hockey painting.png")
    original = source.read_bytes()
    category_rules(root, categories=("Hockey=hockey",), save=True, expected_revision="missing")
    c = Controller(root, Presentation())
    try:
        c.key(Key("enter")); c.key(Key("char", "1")); finish(c)
        plan = c.state.page.result
        assert "/img/hockey/SML/" in plan["files"][0]["destination"]
        c.key(Key("enter"))
        assert c.state.page.confirm_request.values["plan_id"] == plan["plan_id"]
        c.key(Key("enter"))
        assert source.exists() and c.state.operation is None
        c.key(Key("char", "REPLACE")); c.key(Key("enter")); finish(c)
        assert not source.exists()
        assert (root / plan["files"][0]["destination"]).exists()
        c.key(Key("enter"))
        assert c.state.page.name == "sorter"
        c.key(Key("char", "u")); finish(c)
        c.key(Key("enter")); c.key(Key("char", "UNDO")); c.key(Key("enter")); finish(c)
        assert source.read_bytes() == original
    finally:
        c.shutdown()


def test_sorter_rejects_stale_preview_and_returns_without_reusable_consent(root, make_image):
    source = make_image(root / "painting.png")
    c = Controller(root, Presentation())
    try:
        c.key(Key("enter")); c.key(Key("char", "1")); finish(c)
        c.key(Key("enter"))
        source.write_bytes(b"changed after preview")
        c.key(Key("char", "REPLACE")); c.key(Key("enter"))
        assert c.state.operation.done.wait(10)
        c.pump()
        assert c.state.page.code == "CATEGORY_PREVIEW_CHANGED"
        assert source.read_bytes() == b"changed after preview"
        c.key(Key("enter"))
        assert c.state.page.name == "sorter" and c.state.operation is None
    finally:
        c.shutdown()


def test_sort_without_path_only_asks_path_then_previews(root, make_image):
    make_image(root / "painting.png")
    c = Controller(None, Presentation())
    try:
        c.key(Key("enter")); c.key(Key("char", "1")); paste_path(c, root)
        finish(c)
        assert c.state.page.result["ready"]
        assert not (root / ".riposte").exists()
    finally:
        c.shutdown()


def test_path_errors_preserve_selection_and_workshop_settings(root):
    other = root / "other"; other.mkdir()
    c = Controller(root, Presentation())
    try:
        c.key(Key("char", "8"))
        assert c.state.page.title == "FULL SORT WORKSHOP"
        c.state.page.values["date_mode"] = "embedded"
        c.key(Key("char", "g")); paste_path(c, root / "missing")
        assert c.state.editor.error and c.state.root == root
        c.key(Key("escape")); c.key(Key("char", "g")); paste_path(c, other)
        assert c.state.root == other
        assert c.state.page.values["date_mode"] == "embedded"
        assert c.state.page.name == "form" and c.state.operation is None
    finally:
        c.shutdown()


def test_picker_selects_visible_folder_after_paging_without_rescanning(root, monkeypatch):
    for n in range(60): (root / f"folder-{n:02d}").mkdir()
    c = Controller(root, Presentation())
    try:
        c.sorter(); c.key(Key("char", "b"))
        c.key(Key("pagedown")); c.key(Key("down"))
        row = c.selected_row()
        assert row["title"] in render(c.state, 100, 34).plain()
        # A directory change cannot silently reorder the visible snapshot.
        (root / "a-new-folder").mkdir()
        c.key(Key("ignored"))
        c.key(Key("char", "s"))
        assert c.state.root == row["path"] and c.state.page.name == "sorter"
        c.key(Key("char", "g")); paste_path(c, root)
        assert c.state.root == root
    finally:
        c.shutdown()


def test_picker_parent_shortcut_uses_the_highlighted_parent(root):
    c = Controller(root, Presentation())
    try:
        c.sorter(); c.key(Key("char", "b"))
        c.key(Key("down")); c.key(Key("char", "s"))
        assert c.state.root == root.parent and c.state.page.name == "sorter"
    finally:
        c.shutdown()


def test_disappeared_folder_keeps_focus_and_reports_navigation_error(root):
    child = root / "vanished"; child.mkdir()
    c = Controller(root, Presentation())
    try:
        c.sorter(); c.key(Key("char", "b"))
        c.key(Key("down")); c.key(Key("down"))
        child.rmdir()
        c.key(Key("enter"))
        assert c.state.page.cursor == 2
        assert "existing folder" in c.state.notice
        assert c.state.page.result.directory == root
        assert c.state.page.name == "picker" and c.state.operation is None
    finally:
        c.shutdown()


def test_linear_sorter_enters_path_then_dry_runs_without_workshop(root, make_image):
    source = make_image(root / "painting.png")
    c = Controller(None, Presentation(plain=True))
    output = io.StringIO()
    try:
        linear_session(c, io.StringIO(f"1\n3\n{root}\n2\nenter\nq\n"), output)
        assert source.exists() and not (root / ".riposte").exists()
        assert "Riposte Sorter / Dry Run" in output.getvalue()
        assert c.state.root == root
    finally:
        c.shutdown()
