"""Core sorting remains recoverable when one file fails in a multi-file sort."""
from riposte.organizer import plan as _sort_preview
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from riposte import organizer
from riposte.policy import Policy
from riposte.sort_history import latest_sort
from riposte.store import catalog
from riposte.video import video_catalog
import riposte.sort_history as history

POLICY = Policy(date_mode="modified")


def media_pair(root, make_image, media):
    if media == "image":
        return [make_image(root / "a.png"), make_image(root / "b.png", color=(100, 50, 30))]
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real video fixture requires ffmpeg and ffprobe")
    paths = [root / "a.mp4", root / "b.mp4"]
    for path, color in zip(paths, ("blue", "red")):
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=64x48:r=2",
                        "-t", "1", str(path)], check=True, capture_output=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stamp = dt.datetime(2025, 3, 12, 12).timestamp()
        os.utime(path, (stamp, stamp))
    return paths


@pytest.mark.parametrize("media", ["image", "video"])
def test_failed_output_does_not_reuse_a_recovery_destination(root, make_image, monkeypatch, media):
    sources = media_pair(root, make_image, media)
    originals = [p.read_bytes() for p in sources]
    name = "atomic_clean_write" if media == "image" else "copy_exclusive"
    writer = getattr(organizer, name)
    failed = False

    def fail_first(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected destination write failure")
        return writer(*args, **kwargs)

    monkeypatch.setattr(organizer, name, fail_first)
    result = organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE"
    rows = catalog(root) if media == "image" else video_catalog(root)
    assert len(rows) == 1
    journal = latest_sort(root)
    destinations = [e["output"] for e in journal["entries"]]
    assert len(destinations) == len(set(destinations))
    assert organizer.undo_sort(root)["ready"]
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert [p.read_bytes() for p in sources] == originals
    assert not catalog(root) and not video_catalog(root)


@pytest.mark.parametrize("change", ["edit", "replace", "remove"])
def test_changed_source_after_backup_does_not_poison_later_files(root, make_image, monkeypatch, change):
    first, second = media_pair(root, make_image, "image")
    originals = [p.read_bytes() for p in (first, second)]
    edited = b"later source edit"
    writer = history.copy_exclusive
    changed = False

    def change_after_backup(workspace, source, relative, digest):
        nonlocal changed
        output = writer(workspace, source, relative, digest)
        if not changed and source == first:
            changed = True
            if change == "edit":
                first.write_bytes(edited)
            elif change == "replace":
                replacement = root / "replacement.tmp"
                replacement.write_bytes(originals[0])
                os.replace(replacement, first)
            else:
                first.unlink()
        return output

    monkeypatch.setattr(history, "copy_exclusive", change_after_backup)
    result = organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["counts"].get("migrated") == 1
    assert "DESTINATION_EXISTS" not in result["blockers"]
    journal = latest_sort(root)
    assert len(journal["entries"]) == 2
    for index, entry in enumerate(journal["entries"]):
        backup = root / ".riposte/sort-history" / journal["id"] / entry["backup"]
        assert backup.read_bytes() == originals[index]
    assert organizer.undo_sort(root)["ready"]
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert first.read_bytes() == (edited if change == "edit" else originals[0])
    assert second.read_bytes() == originals[1]
    assert not catalog(root)


def test_noncanonical_numeric_filename_does_not_block_sort(root, make_image):
    make_image(root / "a.png")
    make_image(root / "2025/March/img/SML/SML\u00b2.png", color=(100, 50, 30))
    assert organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["checkpoint"] == "COMPLETE"
    assert len(catalog(root)) == 2
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert (root / "2025/March/img/SML/SML\u00b2.png").exists()


def test_destination_numbering_scans_each_folder_once(root, make_image, monkeypatch):
    for index in range(12):
        make_image(root / f"image-{index:02}.png", color=(index, 50, 100))
    target = root / "2025/March/img/SML"
    target.mkdir(parents=True)
    iterations = 0
    iterdir = Path.iterdir

    def count_scans(path):
        nonlocal iterations
        if path == target:
            iterations += 1
        return iterdir(path)

    monkeypatch.setattr(Path, "iterdir", count_scans)
    assert organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["checkpoint"] == "COMPLETE"
    assert len(catalog(root)) == 12
    assert iterations == 3  # Preview and two integrity rechecks; no per-file rescans.


def test_late_destination_collision_is_preserved(root, make_image, monkeypatch):
    sources = media_pair(root, make_image, "image")
    originals = [p.read_bytes() for p in sources]
    late = root / "2025/March/img/SML/SML02.png"
    record = organizer.record_image

    def add_late_file(*args, **kwargs):
        row = record(*args, **kwargs)
        if not late.exists():
            late.write_bytes(b"external addition")
        return row

    monkeypatch.setattr(organizer, "record_image", add_late_file)
    result = organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["counts"]["migrated"] == 1
    assert result["blockers"]["DESTINATION_EXISTS"] == 1
    assert sources[1].read_bytes() == originals[1]
    assert [Path(r["relative"]).name for r in catalog(root)] == ["SML01.png"]
    assert late.read_bytes() == b"external addition"
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert [p.read_bytes() for p in sources] == originals
    assert late.read_bytes() == b"external addition"
