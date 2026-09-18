"""Changes while the recovery journal is flushed must not be unlinked."""
import hashlib
import os

import pytest

from riposte import organizer
from riposte.policy import Policy
from riposte.store import catalog
import riposte.sort_history as history


@pytest.mark.parametrize("media", ["image", "sidecar"])
@pytest.mark.parametrize("change", ["edit", "replace", "timestamp", "remove", "hardlink"])
def test_source_changed_during_removal_journal_is_retained(root, make_image, monkeypatch, media, change):
    source = root / ("original.png" if media == "image" else "original.xmp")
    if media == "image":
        make_image(source)
    else:
        source.write_bytes(b"private sidecar metadata")
    original = source.read_bytes()
    stamp = source.stat()
    edited = bytes([original[0] ^ 1]) + original[1:]
    expected = edited if change == "edit" else original
    fired = False
    save = history._save

    def change_during_save(workspace, journal):
        nonlocal fired
        save(workspace, journal)
        if fired or not any(e["removing"] and not e["removed"] for e in journal["entries"]):
            return
        fired = True
        if change == "edit":
            source.write_bytes(edited)
            os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        elif change == "replace":
            replacement = root / "replacement.tmp"
            replacement.write_bytes(original)
            os.utime(replacement, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            os.replace(replacement, source)
        elif change == "timestamp":
            os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 10_000_000_000))
        elif change == "remove":
            source.unlink()
        else:
            os.link(source, root / "external-link.tmp")

    monkeypatch.setattr(history, "_save", change_during_save)
    result = organizer.organize(root, Policy(date_mode="modified", discard_sidecars=True))
    assert fired
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["blockers"].get("SOURCE_CHANGED_OUTPUT_RETAINED") == 1
    if change != "remove":
        assert source.read_bytes() == expected
    journal = history.latest_sort(root)
    assert journal is not None
    entry = journal["entries"][0]
    assert not entry["removed"] and not entry["removing"]
    backup = root / ".riposte" / "sort-history" / journal["id"] / entry["backup"]
    assert backup.read_bytes() == original
    assert hashlib.sha256(original).hexdigest() == entry["sha256"]

    # Undo may remove the generated output, but must keep the later source edit.
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == expected
    if change == "timestamp":
        assert source.stat().st_mtime_ns == stamp.st_mtime_ns + 10_000_000_000
    if change == "hardlink":
        assert (root / "external-link.tmp").read_bytes() == original
    assert not catalog(root)
