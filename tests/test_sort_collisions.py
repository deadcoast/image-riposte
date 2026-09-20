"""External destination winners remain intact through sorting and recovery."""
from riposte.organizer import plan as _sort_preview
import os
from pathlib import Path

import pytest

from riposte import organizer, store
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.sanitize import decode_clean, encode_clean
from riposte.video import video_catalog
from test_sort_partial_failures import media_pair

POLICY = Policy(date_mode="modified")
STAMP = 1_600_000_123_000_000_000


def intercept_commit(monkeypatch, destination, create):
    """Inject just before the filesystem commit, for both old and repaired code."""
    for name in ("replace", "link"):
        original = getattr(os, name)

        def commit(source, target, *args, _original=original, **kwargs):
            if Path(target) == destination and not destination.exists():
                create(Path(source).read_bytes())
            return _original(source, target, *args, **kwargs)

        monkeypatch.setattr(os, name, commit)


@pytest.mark.parametrize("winner", ["different", "identical", "directory"])
def test_clean_commit_never_replaces_a_late_winner(root, make_image, monkeypatch, winner):
    source = make_image(root / "original.png")
    clean = decode_clean(source, POLICY)
    data = encode_clean(clean.pixels, clean.day)
    destination = root / "out.png"
    external = data if winner == "identical" else b"external file"

    def create(_data):
        if winner == "directory":
            destination.mkdir()
            (destination / "keep.txt").write_bytes(external)
        else:
            destination.write_bytes(external)
        os.utime(destination, ns=(STAMP, STAMP))

    intercept_commit(monkeypatch, destination, create)
    with pytest.raises(RiposteError, match="DESTINATION_EXISTS"):
        store.atomic_clean_write(root, "out.png", data)
    assert (destination / "keep.txt" if winner == "directory" else destination).read_bytes() == external
    assert destination.stat().st_mtime_ns == STAMP
    assert not list(root.glob(".clean-*.tmp"))


@pytest.mark.parametrize("media", ["image", "video"])
@pytest.mark.parametrize("when", ["before_write", "final_commit"])
@pytest.mark.parametrize("identical", [False, True])
def test_rejected_output_is_not_owned_by_undo(root, make_image, monkeypatch, media, when, identical):
    sources = media_pair(root, make_image, media)
    originals = [p.read_bytes() for p in sources]
    destination = root / f"2025/March/{'img' if media == 'image' else 'vid'}/SML/SML01{sources[0].suffix}"
    winner = []

    def create(intended):
        destination.parent.mkdir(parents=True, exist_ok=True)
        winner.append(intended if identical else b"external destination")
        destination.write_bytes(winner[0])
        os.utime(destination, ns=(STAMP, STAMP))

    if when == "final_commit":
        intercept_commit(monkeypatch, destination, create)
    else:
        name = "atomic_clean_write" if media == "image" else "copy_exclusive"
        writer = getattr(organizer, name)

        def add_before_write(*args, **kwargs):
            if not winner:
                create(args[2] if media == "image" else Path(args[1]).read_bytes())
            return writer(*args, **kwargs)

        monkeypatch.setattr(organizer, name, add_before_write)

    result = organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    assert winner, "collision injection did not execute"
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["blockers"].get("DESTINATION_EXISTS") == 1
    assert sources[0].read_bytes() == originals[0]
    assert destination.read_bytes() == winner[0]
    assert destination.stat().st_mtime_ns == STAMP
    assert result["counts"].get("migrated" if media == "image" else "videos_sorted") == 1
    preview = organizer.undo_sort(root)
    assert preview["ready"]
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert [p.read_bytes() for p in sources] == originals
    assert destination.read_bytes() == winner[0]
    assert destination.stat().st_mtime_ns == STAMP
    assert not store.catalog(root) and not video_catalog(root)
    assert preview["outputs_to_remove"] == 1


def test_explicit_clean_replacement_still_works(root, make_image):
    source = make_image(root / "original.png")
    clean = decode_clean(source, POLICY)
    data = encode_clean(clean.pixels, clean.day)
    destination = root / "out.png"
    destination.write_bytes(b"explicitly replaced")
    assert store.atomic_clean_write(root, "out.png", data, replace=True) == destination
    assert destination.read_bytes() == data
    assert not list(root.glob(".clean-*.tmp"))


def test_exclusive_commit_failure_does_not_fall_back_to_replacement(root, make_image, monkeypatch):
    source = make_image(root / "original.png")
    clean = decode_clean(source, POLICY)
    data = encode_clean(clean.pixels, clean.day)

    def unsupported(*args, **kwargs):
        raise OSError("exclusive commit unavailable")

    monkeypatch.setattr(os, "link", unsupported)
    with pytest.raises(OSError, match="exclusive commit unavailable"):
        store.atomic_clean_write(root, "out.png", data)
    assert not (root / "out.png").exists()
    assert not list(root.glob(".clean-*.tmp"))
