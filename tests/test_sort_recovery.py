import hashlib
import os
import json

import pytest

from riposte import organizer
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.store import catalog

POLICY = Policy(date_mode="modified")


def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def test_undo_restores_original_bytes_names_and_modified_time(root, make_image):
    source = make_image(root / "originals" / "personal-name.png")
    original, stamp = source.read_bytes(), source.stat().st_mtime_ns
    assert organizer.organize(root, POLICY)["checkpoint"] == "COMPLETE"
    before = inventory(root)
    preview = organizer.undo_sort(root)
    assert preview["ready"] and preview["mode"] == "UNDO_SORT_PREVIEW"
    assert before == inventory(root)
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original
    assert source.stat().st_mtime_ns == stamp
    assert not catalog(root)


def test_preview_has_no_state_or_mutations(root, make_image):
    make_image(root / "photo.png")
    before = inventory(root)
    result = organizer.plan(root, POLICY)
    assert result["ready"]
    assert list(result["destinations"]) == ["2025/March/img/SML"]
    assert inventory(root) == before
    assert not (root / ".riposte").exists()


@pytest.mark.parametrize("conflict", ["original", "output", "backup", "catalog"])
def test_undo_conflicts_leave_every_file_unchanged(root, make_image, conflict):
    source = make_image(root / "private.png")
    organizer.organize(root, POLICY)
    if conflict == "original":
        source.write_bytes(b"later addition")
    elif conflict == "output":
        (root / catalog(root)[0]["relative"]).write_bytes(b"later edit")
    elif conflict == "backup":
        next((root / ".riposte/sort-history").rglob("*.bin")).write_bytes(b"damaged")
    else:
        from riposte.store import connect
        with connect(root) as db:
            db.execute("UPDATE images SET width=width+1")
    before = inventory(root)
    assert not organizer.undo_sort(root)["ready"]
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "INCOMPLETE"
    assert inventory(root) == before


def test_multiple_sorts_undo_in_reverse_order_and_noop_does_not_hide_history(root, make_image):
    a = make_image(root / "a.png")
    a_bytes = a.read_bytes()
    organizer.organize(root, POLICY)
    rows = catalog(root)
    b = make_image(root / "added" / "b.png", color=(12, 34, 56))
    b_bytes = b.read_bytes()
    organizer.organize(root, POLICY)
    organizer.organize(root, POLICY)
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == rows and b.read_bytes() == b_bytes
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert a.read_bytes() == a_bytes and b.read_bytes() == b_bytes
    assert organizer.undo_sort(root)["blockers"] == {"NO_SORT_TO_UNDO": 1}


def test_sidecars_and_legacy_catalog_paths_are_recoverable(root, make_image):
    from riposte.sanitize import decode_clean, encode_clean, png_audit
    from riposte.store import atomic_clean_write, record_image
    raw = make_image(root / "input.png")
    clean = decode_clean(raw, POLICY)
    data = encode_clean(clean.pixels, clean.day)
    raw.unlink()
    relative = "2025/March/SML/SML01.png"
    atomic_clean_write(root, relative, data)
    row = record_image(root, relative, png_audit(data), len(data), "embedded")
    side = root / "original.xmp"
    side.write_bytes(b"private sidecar data")
    assert organizer.audit_workspace(root)["blockers"] == {"UNMANAGED_INPUT": 1}
    result = organizer.organize(root, Policy(date_mode="modified", discard_sidecars=True))
    assert result["checkpoint"] == "COMPLETE"
    assert catalog(root)[0]["id"] == row["id"]
    assert catalog(root)[0]["relative"] == "2025/March/img/SML/SML01.png"
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == [row]
    assert (root / relative).read_bytes() == data
    assert side.read_bytes() == b"private sidecar data"


def test_failed_source_removal_can_undo_verified_output_without_losing_later_source_edit(root, make_image, monkeypatch):
    source = make_image(root / "source.png")
    real = organizer.record_image
    def change_source(*args, **kwargs):
        row = real(*args, **kwargs)
        source.write_bytes(b"edited after decode")
        return row
    monkeypatch.setattr(organizer, "record_image", change_source)
    assert organizer.organize(root, POLICY)["checkpoint"] == "INCOMPLETE"
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == b"edited after decode"
    assert not catalog(root)


def test_interrupted_sort_recovery(root, make_image, monkeypatch):
    from riposte.sort_history import SortHistory
    source = make_image(root / "source.png")
    original = source.read_bytes()
    real = SortHistory.remove_source
    def interrupt(self, entry):
        real(self, entry)
        raise KeyboardInterrupt
    monkeypatch.setattr(SortHistory, "remove_source", interrupt)
    with pytest.raises(KeyboardInterrupt):
        organizer.organize(root, POLICY)
    assert organizer.plan(root, POLICY)["blockers"] == {"SORT_RECOVERY_REQUIRED": 1}
    with pytest.raises(RiposteError, match="SORT_RECOVERY_REQUIRED"):
        organizer.organize(root, POLICY)
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original


def test_undo_resumes_after_restoration_before_output_removal(root, make_image, monkeypatch):
    import riposte.sort_history as history
    source = make_image(root / "source.png")
    original = source.read_bytes()
    stamp = source.stat().st_mtime_ns
    organizer.organize(root, POLICY)
    real = history.copy_exclusive
    def interrupt(*args, **kwargs):
        value = real(*args, **kwargs)
        raise KeyboardInterrupt
    monkeypatch.setattr(history, "copy_exclusive", interrupt)
    with pytest.raises(KeyboardInterrupt):
        organizer.undo_sort(root, apply=True)
    monkeypatch.setattr(history, "copy_exclusive", real)
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original
    assert source.stat().st_mtime_ns == stamp
    assert not catalog(root)


@pytest.mark.parametrize("entries", [None, "invalid", [None], [{}]])
def test_malformed_journal_fails_closed(root, make_image, entries):
    make_image(root / "source.png")
    organizer.organize(root, POLICY)
    path = next((root / ".riposte/sort-history").rglob("journal.json"))
    journal = json.loads(path.read_text())
    journal["entries"] = entries
    path.write_text(json.dumps(journal))
    before = inventory(root)
    with pytest.raises(RiposteError, match="SORT_HISTORY_INVALID"):
        organizer.undo_sort(root, apply=True)
    assert inventory(root) == before


def test_backup_write_failure_never_removes_source(root, make_image, monkeypatch):
    source = make_image(root / "source.png")
    original = source.read_bytes()
    def fail(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr("riposte.sort_history.copy_exclusive", fail)
    assert organizer.organize(root, POLICY)["checkpoint"] == "INCOMPLETE"
    assert source.read_bytes() == original and not catalog(root)


def test_undo_survives_legacy_workspace_namespace_upgrade(root, make_image):
    from riposte.store import LEGACY_SIGNATURE, upgrade_workspace
    state = root / ".shroud"
    state.mkdir()
    (state / "WORKSPACE").write_text(LEGACY_SIGNATURE)
    source = make_image(root / "legacy.png")
    original = source.read_bytes()
    assert organizer.organize(root, POLICY)["checkpoint"] == "COMPLETE"
    assert upgrade_workspace(root)["status"] == "UPGRADED"
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original and not catalog(root)


def test_undo_confirmation_is_bound_to_previewed_sort(root, make_image):
    make_image(root / "a.png")
    organizer.organize(root, POLICY)
    previous = organizer.undo_sort(root)["sort_id"]
    make_image(root / "b.png")
    organizer.organize(root, POLICY)
    before = inventory(root)
    with pytest.raises(RiposteError, match="SORT_HISTORY_CHANGED_REPREVIEW"):
        organizer.undo_sort(root, apply=True, sort_id=previous)
    assert inventory(root) == before


def test_undo_history_cannot_escape_workspace(root, make_image, tmp_path):
    make_image(root / "a.png")
    organizer.organize(root, POLICY)
    journal_path = next((root / ".riposte/sort-history").rglob("journal.json"))
    journal = json.loads(journal_path.read_text())
    journal["entries"][0]["source"] = "../outside.png"
    journal_path.write_text(json.dumps(journal))
    before = inventory(root)
    assert not organizer.undo_sort(root)["ready"]
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "INCOMPLETE"
    assert inventory(root) == before


def test_no_history_preview_is_read_only(root):
    assert organizer.undo_sort(root)["blockers"] == {"NO_SORT_TO_UNDO": 1}
    assert list(root.iterdir()) == []


def test_direct_cli_undo_previews_then_applies(root, make_image):
    from typer.testing import CliRunner
    from riposte.cli import app
    source = make_image(root / "source.png")
    original = source.read_bytes()
    runner = CliRunner()
    assert runner.invoke(app, ["--json", "sort", str(root), "--apply"]).exit_code == 0
    before = inventory(root)
    preview = runner.invoke(app, ["--json", "undo-sort", str(root)])
    assert preview.exit_code == 0, preview.output
    result = json.loads(preview.output)
    assert result["ready"] and before == inventory(root)
    applied = runner.invoke(app, ["--json", "undo-sort", str(root), "--apply", "--sort-id", result["sort_id"]])
    assert applied.exit_code == 0, applied.output
    assert source.read_bytes() == original
